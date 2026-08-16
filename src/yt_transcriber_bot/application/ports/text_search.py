from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SearchDocument:
    job_id: str
    canonical_transcript_ref: str
    user_id: int
    title: str
    content: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class HistorySearchHit:
    job_id: str
    title: str
    video_id: str | None
    source_label: str
    completed_at: datetime
    snippet: str


class TextSearchIndex(ABC):
    @abstractmethod
    def replace(self, document: SearchDocument) -> None: ...

    @abstractmethod
    def remove(self, job_id: str) -> None: ...


class TextSearchQuery(ABC):
    @abstractmethod
    def search_completed_for_user(
        self, *, user_id: int, query: str, limit: int
    ) -> list[HistorySearchHit]: ...
