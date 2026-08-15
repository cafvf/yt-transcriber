"""Porta ``JobRepository`` — persistência do agregado e contexto de entrega."""

from __future__ import annotations

from abc import ABC, abstractmethod

from yt_transcriber_bot.application.job_request_context import JobRequestContext
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class JobRepository(ABC):
    """Repository do agregado ``Job``.

    ``JobRequestContext`` é deliberadamente separado do agregado. O sidecar
    padrão mantém fakes brownfield pequenos; adapters duráveis devem sobrescrever
    estes dois métodos (o SQLAlchemy adapter o faz).
    """

    @abstractmethod
    def save(self, job: Job) -> None: ...

    @abstractmethod
    def get_by_id(self, job_id: str) -> Job | None: ...

    @abstractmethod
    def get_latest_by_video_id(self, video_id: VideoId) -> Job | None: ...

    @abstractmethod
    def get_latest_completed_for_user(self, user_id: int) -> Job | None: ...

    @abstractmethod
    def list_recent_for_user(self, user_id: int, limit: int) -> list[Job]: ...

    @abstractmethod
    def list_completed_oldest_first(self) -> list[Job]: ...

    @abstractmethod
    def list_by_statuses_oldest_first(self, statuses: set[JobStatus]) -> list[Job]: ...

    @abstractmethod
    def delete(self, job_id: str) -> None: ...

    def save_request_context(self, context: JobRequestContext) -> None:
        sidecar = getattr(self, "_job_request_context_sidecar", None)
        if sidecar is None:
            sidecar = {}
            self._job_request_context_sidecar = sidecar
        sidecar[context.job_id] = context

    def get_request_context(self, job_id: str) -> JobRequestContext | None:
        sidecar = getattr(self, "_job_request_context_sidecar", {})
        return sidecar.get(job_id)
