from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.application.services.manual_artifact_recovery import (
    ArtifactRecoveryState,
    ManualArtifactRecoveryService,
)
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class Repo(JobRepository):
    def __init__(self, job: Job | None) -> None:
        self.job = job

    def save(self, job: Job) -> None:
        raise AssertionError("recovery inspection must not save")

    def get_by_id(self, job_id: str) -> Job | None:
        if self.job is not None and self.job.job_id == job_id:
            return self.job
        return None

    def get_latest_by_video_id(self, video_id: VideoId) -> Job | None:
        _ = video_id
        return None

    def get_latest_completed_for_user(self, user_id: int) -> Job | None:
        _ = user_id
        return None

    def list_recent_for_user(self, user_id: int, limit: int) -> list[Job]:
        _ = (user_id, limit)
        return []

    def list_completed_oldest_first(self) -> list[Job]:
        return []

    def list_by_statuses_oldest_first(self, statuses: set[JobStatus]) -> list[Job]:
        _ = statuses
        return []

    def delete(self, job_id: str) -> None:
        raise AssertionError("recovery inspection must not delete")


def _delivery_failed() -> Job:
    now = datetime.now(UTC)
    return Job(
        job_id="job-recovery",
        video_id=VideoId("dQw4w9WgXcQ"),
        status=JobStatus.DELIVERY_FAILED,
        requested_by_user_id=7,
        requested_at=now,
        updated_at=now,
        md_path="data/transcripts/job-recovery.md",
        audio_path=None,
    )


def test_delivery_failed_classifies_existing_and_absent_artifacts() -> None:
    job = _delivery_failed()
    service = ManualArtifactRecoveryService(
        Repo(job),
        artifact_available=lambda path: path == Path(job.md_path or ""),
    )

    report = service.inspect(job.job_id)

    assert report is not None
    assert report.eligible is True
    assert report.recoverable[0].kind == "markdown"
    assert report.artifacts[0].state is ArtifactRecoveryState.AVAILABLE
    assert report.artifacts[1].state is ArtifactRecoveryState.REFERENCE_ABSENT
    assert job.status is JobStatus.DELIVERY_FAILED


def test_referenced_but_missing_artifact_is_not_recoverable() -> None:
    job = _delivery_failed()
    job.audio_path = "data/processed/missing.mp3"
    service = ManualArtifactRecoveryService(Repo(job), artifact_available=lambda _path: False)

    report = service.inspect(job.job_id)

    assert report is not None
    assert not report.recoverable
    assert report.artifacts[0].state is ArtifactRecoveryState.REFERENCED_MISSING
    assert report.artifacts[1].state is ArtifactRecoveryState.REFERENCED_MISSING


def test_non_delivery_failed_job_is_ineligible_without_mutation() -> None:
    job = _delivery_failed()
    job.status = JobStatus.COMPLETED
    service = ManualArtifactRecoveryService(Repo(job), artifact_available=lambda _path: True)

    report = service.inspect(job.job_id)

    assert report is not None
    assert report.eligible is False
    assert job.status is JobStatus.COMPLETED
