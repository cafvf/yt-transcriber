"""Coordenação application-owned do ciclo de execução e entrega primária."""

from __future__ import annotations

from dataclasses import dataclass

from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.domain.entities.job import Job, JobStatus


@dataclass(frozen=True, slots=True)
class PrimaryDeliveryOutcome:
    """Resultado do mecanismo externo de entrega primária."""

    delivered: bool
    error: str | None = None


class ExecutionLifecycleService:
    """Mantém mutações de lifecycle coerentes com o resultado da execução.

    O mecanismo de entrega permanece no adapter. Este serviço possui apenas a
    política de transição/persistência do Job resultante.
    """

    def __init__(self, repository: JobRepository | None) -> None:
        self._repository = repository

    def start(self, job: Job) -> None:
        job.transition_to(JobStatus.ACQUIRING)
        self._save(job)

    def cancel_pending(self, job: Job, *, error: str) -> None:
        job.transition_to(JobStatus.CANCELLED, error=error)
        self._save(job)

    def fail_unexpected(self, job: Job, *, error: str) -> None:
        job.transition_to(JobStatus.FAILED, error=error)
        self._save(job)

    def begin_primary_delivery(self, job: Job) -> None:
        job.transition_to(JobStatus.DELIVERING)
        self._save(job)

    def finish_primary_delivery(
        self,
        job: Job,
        outcome: PrimaryDeliveryOutcome,
    ) -> None:
        if outcome.delivered:
            job.transition_to(JobStatus.COMPLETED)
        else:
            job.transition_to(
                JobStatus.DELIVERY_FAILED,
                error=outcome.error
                or "Falha na entrega primária; artefatos preservados localmente.",
            )
        self._save(job)

    def _save(self, job: Job) -> None:
        if self._repository is not None:
            self._repository.save(job)
