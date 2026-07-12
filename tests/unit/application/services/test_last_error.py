"""Testes do serviço de /lasterror."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.services.last_error import LastErrorService
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class FakeRepo:
    def __init__(self, jobs: list[Job]) -> None:
        self.jobs = jobs

    def list_recent_for_user(self, user_id: int, limit: int) -> list[Job]:
        return [job for job in self.jobs if job.requested_by_user_id == user_id][-limit:]


def _settings(tmp_path: Path) -> AppSettings:
    return AppSettings(
        telegram_bot_token="dummy-telegram-token-for-tests",
        telegram_allowed_user_id=42,
        hf_token="alpha-bravo-charlie",
        base_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
        lasterror_log_tail_lines=2,
    )


def _failed_job(user_id: int, when: datetime, *, error: str) -> Job:
    job = Job.new(VideoId("dQw4w9WgXcQ"), user_id)
    object.__setattr__(job, "requested_at", when)
    job.transition_to(JobStatus.FAILED, error=error)
    object.__setattr__(job, "updated_at", when)
    return job


def _delivery_failed_job(user_id: int, when: datetime, *, error: str) -> Job:
    job = Job.new(VideoId("dQw4w9WgXcQ"), user_id)
    object.__setattr__(job, "requested_at", when)
    job.transition_to(JobStatus.DELIVERING)
    job.transition_to(JobStatus.DELIVERY_FAILED, error=error)
    object.__setattr__(job, "updated_at", when)
    return job


def test_lasterror_reports_no_recent_failure(tmp_path: Path) -> None:
    service = LastErrorService(repository=FakeRepo([]), settings=_settings(tmp_path))  # type: ignore[arg-type]

    report = service.latest_for_user(42)

    assert report.job is None
    assert "Nenhum erro" in report.message


def test_lasterror_selects_latest_failed_job_and_sanitizes_secrets(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    older = _failed_job(42, datetime(2026, 5, 1, 10, tzinfo=UTC), error="erro antigo")
    newer = _failed_job(
        42,
        datetime(2026, 5, 1, 11, tzinfo=UTC),
        error="falhou com token dummy-telegram-token-for-tests",
    )
    log = tmp_path / "bot.log"
    log.write_text("linha1\nlinha2\nAUTH=alpha-bravo-charlie\n", encoding="utf-8")
    newer.log_path = str(log)
    service = LastErrorService(repository=FakeRepo([older, newer]), settings=settings)  # type: ignore[arg-type]

    report = service.latest_for_user(42)

    assert report.job is newer
    assert "falhou com token" in report.message
    assert "dummy-telegram-token-for-tests" not in report.message
    assert "alpha-bravo-charlie" not in report.message
    assert "[REDACTED]" in report.message
    assert "linha2" in report.message
    assert "linha1" not in report.message


def test_lasterror_reports_delivery_failed_job_with_artifact_paths(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    job = _delivery_failed_job(
        42,
        datetime(2026, 5, 1, 12, tzinfo=UTC),
        error="Falha ao entregar artefatos pelo Telegram",
    )
    job.md_path = str(tmp_path / "transcripts" / "video.md")
    job.audio_path = str(tmp_path / "processed" / "video.mp3")
    service = LastErrorService(repository=FakeRepo([job]), settings=settings)  # type: ignore[arg-type]

    report = service.latest_for_user(42)

    assert report.job is job
    assert report.operational_error is None
    assert "Tipo: job de transcrição" in report.message
    assert "Status: delivery_failed" in report.message
    assert f"Markdown parcial: {job.md_path}" in report.message
    assert f"Áudio parcial: {job.audio_path}" in report.message


def test_lasterror_reports_operational_error_from_summary(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    service = LastErrorService(repository=FakeRepo([]), settings=settings)  # type: ignore[arg-type]

    service.record_operation_error(
        user_id=42,
        operation="summary",
        message=(
            "Falha ao chamar a LLM de resumo: Não consegui consultar /v1/models. "
            "Authorization: Bearer dummy-bearer-token-for-tests"
        ),
        context={"video_id": "dQw4w9WgXcQ", "history_index": 1},
        stage="llm",
    )

    report = service.latest_for_user(42)

    assert report.job is None
    assert report.operational_error is not None
    assert "operação derivada" in report.message
    assert "Operação: summary" in report.message
    assert "Etapa: llm" in report.message
    assert "Falha ao chamar a LLM" in report.message
    assert "dQw4w9WgXcQ" in report.message
    assert "dummy-telegram-token-for-tests" not in report.message
    assert "[REDACTED]" in report.message


def test_lasterror_records_error_type_stage_traceback_and_hints(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    service = LastErrorService(repository=FakeRepo([]), settings=settings)  # type: ignore[arg-type]

    try:
        raise TimeoutError("LM Studio timeout while calling /v1/models")
    except TimeoutError as exc:
        service.record_operation_error(
            user_id=42,
            operation="summary",
            message="Falha ao chamar a LLM de resumo: LM Studio timeout",
            context={"video_id": "dQw4w9WgXcQ"},
            error=exc,
            stage="llm",
        )

    report = service.latest_for_user(42)

    assert report.operational_error is not None
    assert "Classe do erro: TimeoutError" in report.message
    assert "Etapa: llm" in report.message
    assert "Traceback final sanitizado" in report.message
    assert "TimeoutError" in report.message
    assert "Próximas verificações" in report.message
    assert "SUMMARY_MAX_INPUT_TOKENS" in report.message


def test_lasterror_sanitizes_api_bodies_in_message_context_and_traceback(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    service = LastErrorService(repository=FakeRepo([]), settings=settings)  # type: ignore[arg-type]

    try:
        raise RuntimeError(
            'HTTP 400 body={"messages":[{"role":"user","content":"raw transcript"}],'
            '"input":"private input body","Authorization":"Bearer backend-token"}'
        )
    except RuntimeError as exc:
        service.record_operation_error(
            user_id=42,
            operation="summary",
            message=f"Backend recusou request_body={{'transcript':'private transcript text'}}: {exc}",
            context={
                "response_body": '{"content":"echoed prompt body"}',
                "headers": "Authorization: Bearer context-token",
            },
            error=exc,
            stage="llm",
        )

    raw_log = (settings.logs_dir() / "operational_errors.jsonl").read_text(encoding="utf-8")
    report = service.latest_for_user(42)
    combined = raw_log + "\n" + report.message

    assert "raw transcript" not in combined
    assert "private input body" not in combined
    assert "private transcript text" not in combined
    assert "echoed prompt body" not in combined
    assert "backend-token" not in combined
    assert "context-token" not in combined
    assert "[REDACTED]" in combined


def test_lasterror_prefers_newer_operational_error_over_older_failed_job(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    older = _failed_job(42, datetime(2026, 5, 1, 10, tzinfo=UTC), error="erro antigo")
    service = LastErrorService(repository=FakeRepo([older]), settings=settings)  # type: ignore[arg-type]

    service.record_operation_error(
        user_id=42,
        operation="summary",
        message="LM Studio connection refused",
        context={"video_id": "dQw4w9WgXcQ"},
    )

    report = service.latest_for_user(42)

    assert report.operational_error is not None
    assert report.job is None
    assert "Operação: summary" in report.message
    assert "connection refused" in report.message


def test_lasterror_ignores_operational_errors_from_other_users(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    service = LastErrorService(repository=FakeRepo([]), settings=settings)  # type: ignore[arg-type]

    service.record_operation_error(user_id=99, operation="summary", message="erro de outro usuário")

    report = service.latest_for_user(42)

    assert report.job is None
    assert report.operational_error is None
    assert "Nenhum erro" in report.message


def test_lasterror_reads_legacy_operational_error_records(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    path = settings.logs_dir() / "operational_errors.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '{"user_id": 42, "operation": "summary", "message": "erro legado", '
        '"occurred_at": "2026-05-04T10:00:00+00:00", "context": {"video_id": "x"}}\n',
        encoding="utf-8",
    )
    service = LastErrorService(repository=FakeRepo([]), settings=settings)  # type: ignore[arg-type]

    report = service.latest_for_user(42)

    assert report.operational_error is not None
    assert "erro legado" in report.message
    assert "Operação: summary" in report.message
