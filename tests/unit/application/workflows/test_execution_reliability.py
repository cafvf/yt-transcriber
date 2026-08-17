from __future__ import annotations

import pytest

from yt_transcriber_bot.application.workflows.execution import (
    ExecutionLifecycleService,
    PrimaryDeliveryOutcome,
)
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class Repo:
    def __init__(self, *, fail_completed_save: bool = False) -> None:
        self.fail_completed_save = fail_completed_save
        self.saved: list[JobStatus] = []

    def save(self, job: Job) -> None:
        if self.fail_completed_save and job.status is JobStatus.COMPLETED:
            raise OSError("canonical persistence unavailable")
        self.saved.append(job.status)


def _delivering() -> Job:
    job = Job.new(VideoId("dQw4w9WgXcQ"), 7)
    for status in (
        JobStatus.ACQUIRING,
        JobStatus.CONVERTING,
        JobStatus.TRANSCRIBING,
        JobStatus.DIARIZING,
        JobStatus.RENDERING,
        JobStatus.DELIVERING,
    ):
        job.transition_to(status)
    return job


def test_completed_observer_failure_does_not_invalidate_persisted_completion() -> None:
    repo = Repo()

    def fail_observer(_job: Job) -> None:
        raise RuntimeError("derived index failed")

    service = ExecutionLifecycleService(repo, completed_observer=fail_observer)  # type: ignore[arg-type]
    job = _delivering()

    service.finish_primary_delivery(job, PrimaryDeliveryOutcome(delivered=True))

    assert job.status is JobStatus.COMPLETED
    assert repo.saved[-1] is JobStatus.COMPLETED


def test_completed_observer_runs_only_after_canonical_persistence_succeeds() -> None:
    repo = Repo(fail_completed_save=True)
    observed: list[str] = []
    service = ExecutionLifecycleService(
        repo,  # type: ignore[arg-type]
        completed_observer=lambda job: observed.append(job.job_id),
    )
    job = _delivering()

    with pytest.raises(OSError, match="canonical persistence unavailable"):
        service.finish_primary_delivery(job, PrimaryDeliveryOutcome(delivered=True))

    assert observed == []


def test_invalid_lifecycle_transition_is_deterministic() -> None:
    job = Job.new(VideoId("dQw4w9WgXcQ"), 7)
    with pytest.raises(ValueError, match="transição inválida de pending para completed"):
        job.transition_to(JobStatus.COMPLETED)
    assert job.status is JobStatus.PENDING
