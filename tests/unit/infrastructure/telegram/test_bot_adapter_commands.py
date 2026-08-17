"""Transport-focused Telegram command tests after PLAN-004 thin-adapter convergence."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.cache import CacheCleanupResult
from yt_transcriber_bot.application.services.healthcheck import HealthCheckItem, HealthCheckReport
from yt_transcriber_bot.application.services.last_error import LastErrorReport
from yt_transcriber_bot.application.services.rename_speakers import RenameResult
from yt_transcriber_bot.application.workflows.derivatives import PreparedRenameTarget
from yt_transcriber_bot.application.workflows.history import CompletedHistoryWorkflow
from yt_transcriber_bot.application.workflows.text_search import TextSearchResult
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.telegram.bot_adapter import (
    TelegramBotAdapter,
    _parse_rename_mapping,
)


class FakeBotClient:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str, object | None]] = []
        self.docs: list[Path] = []
        self.videos: list[tuple[Path, str | None]] = []

    async def send_message(
        self, chat_id: int, text: str, reply_markup: object | None = None
    ) -> int:
        self.sent.append((chat_id, text, reply_markup))
        return len(self.sent)

    async def edit_message(self, _chat_id: int, _message_id: int, _text: str) -> None:
        return None

    async def send_document(
        self, _chat_id: int, file_path: Path, caption: str | None = None
    ) -> None:
        self.docs.append(file_path)

    async def send_audio(self, _chat_id: int, _file_path: Path, caption: str | None = None) -> None:
        return None

    async def send_video(self, _chat_id: int, file_path: Path, caption: str | None = None) -> None:
        self.videos.append((file_path, caption))


class Repo:
    def __init__(self) -> None:
        self.jobs: list[Job] = []

    def save(self, job: Job) -> None:
        self.jobs = [existing for existing in self.jobs if existing.job_id != job.job_id]
        self.jobs.append(job)

    def get_by_id(self, job_id: str) -> Job | None:
        return next((job for job in self.jobs if job.job_id == job_id), None)

    def get_latest_by_video_id(self, video_id: VideoId) -> Job | None:
        return next((job for job in reversed(self.jobs) if job.video_id == video_id), None)

    def get_latest_completed_for_user(self, user_id: int) -> Job | None:
        return next(
            (
                job
                for job in reversed(self.jobs)
                if job.requested_by_user_id == user_id and job.status is JobStatus.COMPLETED
            ),
            None,
        )

    def list_recent_for_user(self, user_id: int, limit: int) -> list[Job]:
        jobs = [job for job in self.jobs if job.requested_by_user_id == user_id]
        return sorted(jobs, key=lambda job: job.updated_at, reverse=True)[:limit]

    def list_completed_oldest_first(self) -> list[Job]:
        return sorted(
            (job for job in self.jobs if job.status is JobStatus.COMPLETED),
            key=lambda job: job.updated_at,
        )

    def list_by_statuses_oldest_first(self, statuses: set[JobStatus]) -> list[Job]:
        return [job for job in self.jobs if job.status in statuses]

    def delete(self, job_id: str) -> None:
        self.jobs = [job for job in self.jobs if job.job_id != job_id]


class SearchWorkflow:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str]] = []
        self.results: list[TextSearchResult] = []

    def search(self, *, user_id: int, query: str, limit: int = 10) -> list[TextSearchResult]:
        self.calls.append((user_id, query))
        return self.results[:limit]


class DerivativeWorkflow:
    def __init__(self, tmp_path: Path) -> None:
        self.tmp_path = tmp_path
        self.job: Job | None = None
        self.rename_calls: list[dict[str, str]] = []

    def prepare_rename(self, *, user_id: int, index: int) -> PreparedRenameTarget:
        if self.job is None:
            raise LookupError(f"Não encontrei a transcrição #{index}.")
        return PreparedRenameTarget(
            self.job, self.job.canonical_transcript_ref or "canonical", ("SPEAKER_00", "SPEAKER_01")
        )

    def rename(self, *, job_id: str, aliases: dict[str, str]) -> RenameResult:
        self.rename_calls.append(dict(aliases))
        path = self.tmp_path / "renamed.md"
        path.write_text("# renamed", encoding="utf-8")
        return RenameResult(path, len(aliases))

    def export_text(self, *, user_id: int, index: int):
        path = self.tmp_path / "text.txt"
        path.write_text("text", encoding="utf-8")
        return SimpleNamespace(path=path)

    def export_transcript(self, *, user_id: int, index: int, format: str):
        path = self.tmp_path / f"export.{format}"
        path.write_text("export", encoding="utf-8")
        return SimpleNamespace(path=path, format=format)

    def export_video(self, *, user_id: int, index: int):
        path = self.tmp_path / "video.mp4"
        path.write_bytes(b"mp4")
        return SimpleNamespace(path=path, size_bytes=3)


class SummaryWorkflowFake:
    def __init__(self, tmp_path: Path) -> None:
        self.path = tmp_path / "summary.md"
        self.error: BaseException | None = None

    def summarize(self, **_kwargs: object):
        if self.error is not None:
            raise self.error
        self.path.write_text("# summary", encoding="utf-8")
        return SimpleNamespace(path=self.path, chunks=1, model="fake")


class OperationalWorkflowFake:
    def __init__(self) -> None:
        self.errors: list[dict[str, object]] = []

    def healthcheck(self) -> HealthCheckReport:
        return HealthCheckReport((HealthCheckItem("LM Studio", "ok", "modelo disponível."),))

    def last_error(self, _user_id: int) -> LastErrorReport:
        return LastErrorReport(job=None, message="✅ Nenhum erro recente registrado.")

    def record_error(self, **kwargs: object) -> object:
        self.errors.append(kwargs)
        return object()

    def clear_cache(self) -> CacheCleanupResult:
        return CacheCleanupResult(removed_files=2, removed_directories=1)

    def apply_retention(self):
        return SimpleNamespace(expired_jobs=(), removed_files=())


@pytest.fixture
def settings(tmp_path: Path) -> AppSettings:
    return AppSettings(
        telegram_bot_token="x",
        telegram_allowed_user_id=42,
        hf_token="x",
        data_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
        logs_dir=tmp_path / "logs",
    )


@pytest.fixture
def repo() -> Repo:
    return Repo()


@pytest.fixture
def client() -> FakeBotClient:
    return FakeBotClient()


@pytest.fixture
async def adapter(settings: AppSettings, repo: Repo, client: FakeBotClient, tmp_path: Path):
    search = SearchWorkflow()
    derivatives = DerivativeWorkflow(tmp_path)
    summary = SummaryWorkflowFake(tmp_path)
    operations = OperationalWorkflowFake()
    instance = TelegramBotAdapter(
        settings=settings,
        client=client,  # type: ignore[arg-type]
        use_case=MagicMock(),
        repository=repo,  # type: ignore[arg-type]
        history_workflow=CompletedHistoryWorkflow(repo, markdown_available=Path.is_file),  # type: ignore[arg-type]
        text_search_workflow=search,  # type: ignore[arg-type]
        derivative_workflow=derivatives,  # type: ignore[arg-type]
        summary_workflow=summary,  # type: ignore[arg-type]
        operational_workflow=operations,  # type: ignore[arg-type]
    )
    await instance.start()
    yield instance, search, derivatives, summary, operations
    await instance.stop()


def _completed(user_id: int, md_path: Path) -> Job:
    job = Job.new(VideoId("dQw4w9WgXcQ"), user_id)
    for status in (
        JobStatus.ACQUIRING,
        JobStatus.CONVERTING,
        JobStatus.TRANSCRIBING,
        JobStatus.DIARIZING,
        JobStatus.RENDERING,
        JobStatus.DELIVERING,
        JobStatus.COMPLETED,
    ):
        job.transition_to(status)
    job.md_path = str(md_path)
    job.canonical_transcript_ref = md_path.stem
    object.__setattr__(job, "updated_at", datetime(2026, 8, 16, tzinfo=UTC))
    return job


@pytest.mark.asyncio
async def test_list_and_last_are_transport_presentation_over_application_history(
    adapter, repo: Repo, client: FakeBotClient, tmp_path: Path
) -> None:
    instance, *_ = adapter
    md = tmp_path / "hello.md"
    md.write_text("# hello", encoding="utf-8")
    repo.save(_completed(42, md))
    await instance.handle_command_list(chat_id=1, user_id=42)
    await instance.handle_command_last(chat_id=1, user_id=42)
    assert any("hello — dQw4w9WgXcQ" in text for _, text, _ in client.sent)
    assert md in client.docs


@pytest.mark.asyncio
async def test_search_delegates_query_and_formats_result(adapter, client: FakeBotClient) -> None:
    instance, search, *_ = adapter
    search.results = [
        TextSearchResult(
            1,
            "job",
            "Título",
            "dQw4w9WgXcQ",
            "YouTube",
            "2026-08-16 20:00",
            "cookie=secret privacidade",
        )
    ]
    await instance.handle_command_search(chat_id=1, user_id=42, text="/search privacidade")
    assert search.calls == [(42, "privacidade")]
    assert "cookie=[REDACTED]" in client.sent[-1][1]


@pytest.mark.asyncio
async def test_rename_ui_state_delegates_portable_mutation(
    adapter, repo: Repo, client: FakeBotClient, tmp_path: Path
) -> None:
    instance, _, derivatives, *_ = adapter
    md = tmp_path / "hello.md"
    md.write_text("# hello", encoding="utf-8")
    derivatives.job = _completed(42, md)
    repo.save(derivatives.job)
    await instance.handle_command_rename(chat_id=1, user_id=42, text="/rename 1")
    await instance.handle_message(chat_id=1, user_id=42, text="SPEAKER_00=Ana")
    assert derivatives.rename_calls == [{"SPEAKER_00": "Ana"}]
    assert any("Falantes detectados" in text for _, text, _ in client.sent)


@pytest.mark.asyncio
async def test_summary_and_derivative_exports_delegate_to_application_workflows(
    adapter, client: FakeBotClient
) -> None:
    instance, *_ = adapter
    await instance.handle_command_summary(chat_id=1, user_id=42, text="/summary 1")
    await instance.handle_command_text(chat_id=1, user_id=42, text="/text 1")
    await instance.handle_command_export(chat_id=1, user_id=42, text="/export srt 1")
    await instance.handle_command_video_subs(chat_id=1, user_id=42, text="/video_subs 1")
    assert any(path.name == "summary.md" for path in client.docs)
    assert any(path.name == "text.txt" for path in client.docs)
    assert any(path.name == "export.srt" for path in client.docs)
    assert any(path.name == "video.mp4" for path, _ in client.videos)


@pytest.mark.asyncio
async def test_operational_commands_delegate_without_filesystem_fallback(
    adapter, client: FakeBotClient
) -> None:
    instance, *_ = adapter
    await instance.handle_command_healthcheck(chat_id=1, user_id=42)
    await instance.handle_command_lasterror(chat_id=1, user_id=42)
    await instance.handle_command_clearcache(chat_id=1, user_id=42)
    visible = chr(10).join(text for _, text, _ in client.sent)
    assert "LM Studio" in visible
    assert "Nenhum erro recente" in visible
    assert "2 arquivo(s) removido(s)" in visible


def test_parse_rename_mapping_keeps_telegram_ui_parser_small() -> None:
    assert _parse_rename_mapping("SPEAKER_00=Ana, SPEAKER_01=Bruno") == {
        "SPEAKER_00": "Ana",
        "SPEAKER_01": "Bruno",
    }
