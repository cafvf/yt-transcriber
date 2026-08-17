"""Coordenação application-owned do ciclo de execução e entrega primária."""

from __future__ import annotations

from collections.abc import Callable
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

    def __init__(
        self,
        repository: JobRepository | None,
        *,
        completed_observer: Callable[[Job], None] | None = None,
    ) -> None:
        self._repository = repository
        self._completed_observer = completed_observer

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
            self._save(job)
            self._notify_completed(job)
            return
        job.transition_to(
            JobStatus.DELIVERY_FAILED,
            error=outcome.error or "Falha na entrega primária; artefatos preservados localmente.",
        )
        self._save(job)

    def _notify_completed(self, job: Job) -> None:
        if self._completed_observer is None:
            return
        try:
            self._completed_observer(job)
        except Exception:
            # Search/index refresh is derived best-effort work. Canonical completion
            # was already persisted and must not be retroactively invalidated.
            return

    def _save(self, job: Job) -> None:
        if self._repository is not None:
            self._repository.save(job)
