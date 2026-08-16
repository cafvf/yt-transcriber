"""Testes de startup recovery com request context separado do Job."""

from __future__ import annotations

from pathlib import Path

from yt_transcriber_bot.application.job_request_context import JobRequestContext
from yt_transcriber_bot.application.services.startup_recovery import (
    RecoveredPendingJob,
    StartupRecoveryService,
)
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.media_source import MediaSource
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class FakeRepo:
    def __init__(
        self, jobs: list[Job], contexts: dict[str, JobRequestContext] | None = None
    ) -> None:
        self.jobs = jobs
        self.contexts = dict(contexts or {})

    def save(self, job: Job) -> None: ...
    def get_by_id(self, job_id: str) -> Job | None: ...
    def get_latest_by_video_id(self, video_id: VideoId) -> Job | None: ...
    def get_latest_completed_for_user(self, user_id: int) -> Job | None: ...
    def list_recent_for_user(self, user_id: int, limit: int) -> list[Job]: ...
    def list_completed_oldest_first(self) -> list[Job]: ...
    def delete(self, job_id: str) -> None: ...

    def list_by_statuses_oldest_first(self, statuses: set[JobStatus]) -> list[Job]:
        return [job for job in self.jobs if job.status in statuses]

    def save_request_context(self, context: JobRequestContext) -> None:
        self.contexts[context.job_id] = context

    def get_request_context(self, job_id: str) -> JobRequestContext | None:
        return self.contexts.get(job_id)


def _advance(job: Job, target: JobStatus) -> None:
    order = (
        JobStatus.ACQUIRING,
        JobStatus.CONVERTING,
        JobStatus.TRANSCRIBING,
        JobStatus.DIARIZING,
        JobStatus.RENDERING,
        JobStatus.DELIVERING,
    )
    for status in order:
        job.transition_to(status)
        if status is target:
            return


def test_pending_youtube_with_valid_request_context_is_requeued() -> None:
    job = Job.new(VideoId("dQw4w9WgXcQ"), 42, requested_language="pt")
    context = JobRequestContext(
        job_id=job.job_id,
        delivery_chat_id=10,
        source_locator="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    )
    repo = FakeRepo([job], {job.job_id: context})

    result = StartupRecoveryService(repo).recover()  # type: ignore[arg-type]

    assert result.pending_to_requeue == (RecoveredPendingJob(job, context),)
    assert job.status is JobStatus.PENDING


def test_pending_without_valid_request_context_becomes_failed() -> None:
    job = Job.new(VideoId("dQw4w9WgXcQ"), 42)
    repo = FakeRepo([job])

    result = StartupRecoveryService(repo).recover()  # type: ignore[arg-type]

    assert result.pending_to_requeue == ()
    assert result.interrupted_failed == (job,)
    assert job.status is JobStatus.FAILED


def test_pending_telegram_requires_existing_staged_media(tmp_path: Path) -> None:
    staged = tmp_path / "voice.ogg"
    staged.write_bytes(b"audio")
    job = Job.new(
        None,
        42,
        media_source=MediaSource.telegram_audio("private-file-id"),
        source_duration_seconds=12,
    )
    repo = FakeRepo(
        [job],
        {
            job.job_id: JobRequestContext(
                job.job_id,
                delivery_chat_id=10,
                source_locator=str(staged),
            )
        },
    )

    result = StartupRecoveryService(repo).recover()  # type: ignore[arg-type]

    assert result.pending_to_requeue == (RecoveredPendingJob(job, repo.contexts[job.job_id]),)


def test_interrupted_active_job_becomes_failed() -> None:
    job = Job.new(VideoId("dQw4w9WgXcQ"), 42)
    _advance(job, JobStatus.TRANSCRIBING)
    repo = FakeRepo([job])

    result = StartupRecoveryService(repo).recover()  # type: ignore[arg-type]

    assert result.interrupted_failed == (job,)
    assert job.status is JobStatus.FAILED


def test_interrupted_delivery_becomes_delivery_failed() -> None:
    job = Job.new(VideoId("dQw4w9WgXcQ"), 42)
    _advance(job, JobStatus.DELIVERING)
    repo = FakeRepo([job])

    result = StartupRecoveryService(repo).recover()  # type: ignore[arg-type]

    assert result.interrupted_delivery_failed == (job,)
    assert job.status is JobStatus.DELIVERY_FAILED
