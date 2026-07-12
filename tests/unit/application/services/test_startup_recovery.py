"""Tests for startup recovery semantics."""

from __future__ import annotations

from dataclasses import dataclass, field

from yt_transcriber_bot.application.services.startup_recovery import StartupRecoveryService
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


@dataclass
class FakeJobRepository:
    jobs: dict[str, Job] = field(default_factory=dict)

    def save(self, job: Job) -> None:
        self.jobs[job.job_id] = job

    def get_by_id(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def get_latest_by_video_id(self, video_id: VideoId) -> Job | None:
        candidates = [job for job in self.jobs.values() if job.video_id == video_id]
        return max(candidates, key=lambda job: job.requested_at) if candidates else None

    def get_latest_completed_for_user(self, user_id: int) -> Job | None:
        candidates = [
            job
            for job in self.jobs.values()
            if job.requested_by_user_id == user_id and job.status is JobStatus.COMPLETED
        ]
        return max(candidates, key=lambda job: job.requested_at) if candidates else None

    def list_recent_for_user(self, user_id: int, limit: int) -> list[Job]:
        ordered = sorted(
            (job for job in self.jobs.values() if job.requested_by_user_id == user_id),
            key=lambda job: job.requested_at,
            reverse=True,
        )
        return ordered[:limit]

    def list_completed_oldest_first(self) -> list[Job]:
        return sorted(
            (job for job in self.jobs.values() if job.status is JobStatus.COMPLETED),
            key=lambda job: job.updated_at,
        )

    def list_by_statuses_oldest_first(self, statuses: set[JobStatus]) -> list[Job]:
        return sorted(
            (job for job in self.jobs.values() if job.status in statuses),
            key=lambda job: job.requested_at,
        )

    def delete(self, job_id: str) -> None:
        self.jobs.pop(job_id, None)


def _job(
    *,
    status: JobStatus = JobStatus.PENDING,
    source_url: str | None = "https://youtu.be/dQw4w9WgXcQ",
    requested_chat_id: int | None = 10,
    requested_language: str | None = "pt",
    artifact_policy: str = "audio+markdown",
) -> Job:
    job = Job.new(
        VideoId("dQw4w9WgXcQ"),
        user_id=42,
        config_signature="sig",
        source_url=source_url,
        requested_chat_id=requested_chat_id,
        requested_language=requested_language,
        artifact_policy=artifact_policy,
    )
    if status is not JobStatus.PENDING:
        job.transition_to(status)
    return job


def test_requeues_pending_jobs_with_recovery_payload() -> None:
    repo = FakeJobRepository()
    pending = _job()
    repo.save(pending)

    result = StartupRecoveryService(repo).recover()

    assert [job.job_id for job in result.pending_to_requeue] == [pending.job_id]
    stored = repo.get_by_id(pending.job_id)
    assert stored is not None
    assert stored.status is JobStatus.PENDING


def test_marks_pending_job_without_restart_payload_as_failed() -> None:
    repo = FakeJobRepository()
    pending = _job(source_url=None, requested_chat_id=None, requested_language=None)
    repo.save(pending)

    result = StartupRecoveryService(repo).recover()

    assert result.pending_to_requeue == ()
    stored = repo.get_by_id(pending.job_id)
    assert stored is not None
    assert stored.status is JobStatus.FAILED
    assert stored.error_message is not None
    assert "payload suficiente" in stored.error_message


def test_marks_pending_job_with_incomplete_artifact_policy_as_failed() -> None:
    repo = FakeJobRepository()
    pending = _job(artifact_policy="")
    repo.save(pending)

    result = StartupRecoveryService(repo).recover()

    assert result.pending_to_requeue == ()
    stored = repo.get_by_id(pending.job_id)
    assert stored is not None
    assert stored.status is JobStatus.FAILED
    assert stored.error_message is not None
    assert "payload suficiente" in stored.error_message


def test_marks_interrupted_active_jobs_failed() -> None:
    repo = FakeJobRepository()
    active = _job(status=JobStatus.TRANSCRIBING)
    repo.save(active)

    result = StartupRecoveryService(repo).recover()

    assert [job.job_id for job in result.interrupted_failed] == [active.job_id]
    stored = repo.get_by_id(active.job_id)
    assert stored is not None
    assert stored.status is JobStatus.FAILED
    assert stored.error_message is not None
    assert "reinício do processo" in stored.error_message


def test_marks_interrupted_delivering_jobs_as_delivery_failed() -> None:
    repo = FakeJobRepository()
    delivering = _job(status=JobStatus.DELIVERING)
    delivering.md_path = "/tmp/out.md"
    delivering.audio_path = "/tmp/out.ogg"
    repo.save(delivering)

    result = StartupRecoveryService(repo).recover()

    assert [job.job_id for job in result.interrupted_delivery_failed] == [delivering.job_id]
    stored = repo.get_by_id(delivering.job_id)
    assert stored is not None
    assert stored.status is JobStatus.DELIVERY_FAILED
    assert stored.error_message is not None
    assert "Entrega" in stored.error_message
