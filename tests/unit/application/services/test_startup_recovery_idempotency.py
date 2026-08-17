from __future__ import annotations

from yt_transcriber_bot.application.services.startup_recovery import StartupRecoveryService
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class Repo:
    def __init__(self, job: Job) -> None:
        self.job = job
        self.saves = 0

    def list_by_statuses_oldest_first(self, statuses: set[JobStatus]) -> list[Job]:
        return [self.job] if self.job.status in statuses else []

    def get_request_context(self, _job_id: str):
        return None

    def save(self, _job: Job) -> None:
        self.saves += 1


def test_repeated_startup_recovery_does_not_remutate_terminal_reconciliation() -> None:
    job = Job.new(VideoId("dQw4w9WgXcQ"), 7)
    job.transition_to(JobStatus.ACQUIRING)
    repo = Repo(job)
    service = StartupRecoveryService(repo)  # type: ignore[arg-type]

    first = service.recover()
    first_updated_at = job.updated_at
    second = service.recover()

    assert [item.job_id for item in first.interrupted_failed] == [job.job_id]
    assert second.interrupted_failed == ()
    assert second.interrupted_delivery_failed == ()
    assert second.pending_to_requeue == ()
    assert job.status is JobStatus.FAILED
    assert job.updated_at == first_updated_at
    assert repo.saves == 1
