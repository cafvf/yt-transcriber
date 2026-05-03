"""Porta ``JobRepository`` — abstrai a persistência de Jobs."""

from __future__ import annotations

from abc import ABC, abstractmethod

from yt_transcriber_bot.domain.entities.job import Job
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class JobRepository(ABC):
    """Repository do agregado ``Job``."""

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
    def delete(self, job_id: str) -> None: ...
