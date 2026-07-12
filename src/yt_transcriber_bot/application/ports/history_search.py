"""Porta e DTOs para busca textual no histórico concluído."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class HistorySearchHit:
    """Resultado textual independente do transporte e da persistência."""

    job_id: str
    title: str
    video_id: str | None
    source_label: str
    completed_at: datetime
    snippet: str


class HistorySearchRepository(ABC):
    """Consulta e atualiza o índice derivado do histórico de um usuário."""

    @abstractmethod
    def search_completed_for_user(
        self, *, user_id: int, query: str, limit: int
    ) -> list[HistorySearchHit]: ...

    @abstractmethod
    def refresh_search_index(self, job_id: str) -> None:
        """Atualiza o documento derivado de um job concluído, quando houver."""
