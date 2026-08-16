from __future__ import annotations

from yt_transcriber_bot.application.workflows.execution import (
    ExecutionLifecycleService,
    PrimaryDeliveryOutcome,
)
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class Repo:
    def __init__(self) -> None:
        self.saved: list[JobStatus] = []

    def save(self, job: Job) -> None:
        self.saved.append(job.status)


def test_completed_observer_runs_only_after_completed_persistence() -> None:
    job = Job.new(VideoId("dQw4w9WgXcQ"), user_id=7)
    for status in (
        JobStatus.ACQUIRING,
        JobStatus.CONVERTING,
        JobStatus.TRANSCRIBING,
        JobStatus.DIARIZING,
        JobStatus.RENDERING,
        JobStatus.DELIVERING,
    ):
        job.transition_to(status)
    repo = Repo()
    observed: list[JobStatus] = []
    service = ExecutionLifecycleService(
        repo,  # type: ignore[arg-type]
        completed_observer=lambda item: observed.append(item.status),
    )
    service.finish_primary_delivery(job, PrimaryDeliveryOutcome(delivered=True))
    assert repo.saved[-1] is JobStatus.COMPLETED
    assert observed == [JobStatus.COMPLETED]
