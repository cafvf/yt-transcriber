"""Testes do lifecycle application-owned de execução e entrega primária."""

from __future__ import annotations

import pytest

from yt_transcriber_bot.application.workflows.execution import (
    ExecutionLifecycleService,
    PrimaryDeliveryOutcome,
)
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class FakeRepo:
    def __init__(self) -> None:
        self.saved: list[JobStatus] = []

    def save(self, job: Job) -> None:
        self.saved.append(job.status)


class FailingSaveRepo(FakeRepo):
    def save(self, job: Job) -> None:
        raise OSError("database password=do-not-expose")


def _delivering_job() -> Job:
    job = Job.new(VideoId("dQw4w9WgXcQ"), 42)
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


def test_start_is_application_owned_and_persisted() -> None:
    repo = FakeRepo()
    job = Job.new(VideoId("dQw4w9WgXcQ"), 42)

    ExecutionLifecycleService(repo).start(job)  # type: ignore[arg-type]

    assert job.status is JobStatus.ACQUIRING
    assert repo.saved == [JobStatus.ACQUIRING]


def test_pending_cancellation_is_persisted() -> None:
    repo = FakeRepo()
    job = Job.new(VideoId("dQw4w9WgXcQ"), 42)

    ExecutionLifecycleService(repo).cancel_pending(  # type: ignore[arg-type]
        job,
        error="cancelado pelo usuário",
    )

    assert job.status is JobStatus.CANCELLED
    assert repo.saved == [JobStatus.CANCELLED]


def test_unexpected_execution_failure_is_persisted() -> None:
    repo = FakeRepo()
    job = Job.new(VideoId("dQw4w9WgXcQ"), 42)
    job.transition_to(JobStatus.ACQUIRING)

    ExecutionLifecycleService(repo).fail_unexpected(  # type: ignore[arg-type]
        job,
        error="RuntimeError",
    )

    assert job.status is JobStatus.FAILED
    assert repo.saved == [JobStatus.FAILED]


def test_terminal_persistence_failure_is_not_silently_suppressed() -> None:
    job = _delivering_job()
    service = ExecutionLifecycleService(FailingSaveRepo())  # type: ignore[arg-type]

    with pytest.raises(OSError, match="database password"):
        service.finish_primary_delivery(
            job,
            PrimaryDeliveryOutcome(delivered=True),
        )


def test_successful_primary_delivery_completes_job() -> None:
    repo = FakeRepo()
    job = _delivering_job()

    ExecutionLifecycleService(repo).finish_primary_delivery(  # type: ignore[arg-type]
        job,
        PrimaryDeliveryOutcome(delivered=True),
    )

    assert job.status is JobStatus.COMPLETED
    assert repo.saved == [JobStatus.COMPLETED]


def test_failed_primary_delivery_preserves_failure_state() -> None:
    repo = FakeRepo()
    job = _delivering_job()

    ExecutionLifecycleService(repo).finish_primary_delivery(  # type: ignore[arg-type]
        job,
        PrimaryDeliveryOutcome(delivered=False, error="delivery unavailable"),
    )

    assert job.status is JobStatus.DELIVERY_FAILED
    assert job.error_message == "delivery unavailable"
    assert repo.saved == [JobStatus.DELIVERY_FAILED]
