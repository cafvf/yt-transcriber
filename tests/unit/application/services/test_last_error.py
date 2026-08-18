from __future__ import annotations

from pathlib import Path

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.operational_error import (
    JobLogReader,
    OperationalErrorRecord,
    OperationalErrorStore,
)
from yt_transcriber_bot.application.services.last_error import LastErrorService
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class Repo:
    def __init__(self, jobs: list[Job]) -> None:
        self.jobs = jobs

    def list_recent_for_user(self, user_id: int, limit: int) -> list[Job]:
        return [job for job in self.jobs if job.requested_by_user_id == user_id][:limit]


class Store(OperationalErrorStore):
    def __init__(self) -> None:
        self.records: list[OperationalErrorRecord] = []

    def append(self, record: OperationalErrorRecord) -> None:
        self.records.append(record)

    def latest_for_user(self, user_id: int, *, limit: int) -> OperationalErrorRecord | None:
        matches = [record for record in self.records if record.user_id == user_id][-limit:]
        return max(matches, key=lambda record: record.occurred_at) if matches else None


class Logs(JobLogReader):
    def tail(self, path: Path, *, max_lines: int, max_chars: int) -> str:
        _ = (path, max_lines, max_chars)
        return "safe tail"


def _settings() -> AppSettings:
    return AppSettings(_env_file=None, telegram_allowed_user_id=7)


def test_operational_error_roundtrip_is_sanitized_and_selected() -> None:
    store = Store()
    settings = _settings()
    service = LastErrorService(
        repository=Repo([]),  # type: ignore[arg-type]
        settings=settings,
        error_store=store,
        log_reader=Logs(),
    )
    service.record_operation_error(
        user_id=7,
        operation="summary",
        message="timeout",
        context={"path": "/private/staging/file"},
        error=TimeoutError("timeout"),
    )
    report = service.latest_for_user(7)
    assert report.operational_error is not None
    assert "summary" in report.message
    assert "timeout" in report.message


def test_failed_job_can_be_rendered_without_reading_whole_log() -> None:
    job = Job.new(VideoId("dQw4w9WgXcQ"), user_id=7)
    job.transition_to(JobStatus.FAILED, error="boom")
    job.log_path = "/private/job.log"
    service = LastErrorService(
        repository=Repo([job]),  # type: ignore[arg-type]
        settings=_settings(),
        error_store=Store(),
        log_reader=Logs(),
        artifact_available=lambda path: path == Path(job.log_path or ""),
    )
    assert "safe tail" in service.latest_for_user(7).message


def _delivery_failed_job() -> Job:
    job = Job.new(VideoId("dQw4w9WgXcQ"), user_id=7)
    for status in (
        JobStatus.ACQUIRING,
        JobStatus.CONVERTING,
        JobStatus.TRANSCRIBING,
        JobStatus.DIARIZING,
        JobStatus.RENDERING,
        JobStatus.DELIVERING,
        JobStatus.DELIVERY_FAILED,
    ):
        job.transition_to(status)
    return job


def test_delivery_failed_reports_actual_recoverability_without_private_path() -> None:
    job = _delivery_failed_job()
    job.md_path = "/private/transcripts/final.md"
    service = LastErrorService(
        repository=Repo([job]),  # type: ignore[arg-type]
        settings=_settings(),
        error_store=Store(),
        log_reader=Logs(),
        artifact_available=lambda path: path == Path(job.md_path or ""),
    )

    message = service.latest_for_user(7).message

    assert "Artefatos locais recuperáveis: Markdown" in message
    assert "procedimento privado do operador" in message
    assert "/private/transcripts/final.md" not in message


def test_delivery_failed_reports_missing_artifact_as_unavailable() -> None:
    job = _delivery_failed_job()
    job.md_path = "/private/transcripts/missing.md"
    service = LastErrorService(
        repository=Repo([job]),  # type: ignore[arg-type]
        settings=_settings(),
        error_store=Store(),
        log_reader=Logs(),
        artifact_available=lambda _path: False,
    )

    assert "Artefatos locais recuperáveis: indisponíveis" in service.latest_for_user(7).message
