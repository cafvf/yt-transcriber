"""Startup recovery semantics for durable queue/restart behavior."""

from __future__ import annotations

from dataclasses import dataclass

from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.domain.entities.job import Job, JobStatus

_INTERRUPTED_ACTIVE_STATES = frozenset(
    {
        JobStatus.DOWNLOADING,
        JobStatus.CONVERTING,
        JobStatus.TRANSCRIBING,
        JobStatus.DIARIZING,
        JobStatus.RENDERING,
    }
)


@dataclass(frozen=True)
class StartupRecoveryResult:
    pending_to_requeue: tuple[Job, ...]
    interrupted_failed: tuple[Job, ...]
    interrupted_delivery_failed: tuple[Job, ...]


class StartupRecoveryService:
    """Repairs interrupted jobs and selects safe pending jobs to requeue."""

    def __init__(self, repository: JobRepository) -> None:
        self._repository = repository

    def recover(self) -> StartupRecoveryResult:
        pending_to_requeue: list[Job] = []
        interrupted_failed: list[Job] = []
        interrupted_delivery_failed: list[Job] = []

        for job in self._repository.list_by_statuses_oldest_first({JobStatus.PENDING}):
            if self._has_restart_payload(job):
                pending_to_requeue.append(job)
                continue
            job.transition_to(
                JobStatus.FAILED,
                error=(
                    "Job pendente legado sem payload suficiente para retomar após "
                    "reinício do processo."
                ),
            )
            self._repository.save(job)
            interrupted_failed.append(job)

        for job in self._repository.list_by_statuses_oldest_first(set(_INTERRUPTED_ACTIVE_STATES)):
            job.transition_to(
                JobStatus.FAILED,
                error=(
                    "Job interrompido por reinício do processo antes da conclusão; "
                    "reenvie o vídeo ou use /redo."
                ),
            )
            self._repository.save(job)
            interrupted_failed.append(job)

        for job in self._repository.list_by_statuses_oldest_first({JobStatus.DELIVERING}):
            job.transition_to(
                JobStatus.DELIVERY_FAILED,
                error=(
                    "Entrega interrompida por reinício do processo; consulte "
                    "/lasterror para recuperar os artefatos locais."
                ),
            )
            self._repository.save(job)
            interrupted_delivery_failed.append(job)

        return StartupRecoveryResult(
            pending_to_requeue=tuple(pending_to_requeue),
            interrupted_failed=tuple(interrupted_failed),
            interrupted_delivery_failed=tuple(interrupted_delivery_failed),
        )

    @staticmethod
    def _has_restart_payload(job: Job) -> bool:
        return bool(
            job.source_url
            and job.source_url.strip()
            and job.requested_chat_id is not None
            and job.artifact_policy
            and job.artifact_policy.strip()
        )
