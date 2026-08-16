"""Serviço de aplicação para busca no histórico textual."""

from __future__ import annotations

from dataclasses import dataclass

from yt_transcriber_bot.application.ports.text_search import (
    HistorySearchHit,
    TextSearchQuery,
)


@dataclass(frozen=True, slots=True)
class HistorySearchResult:
    """Resultado pronto para o adapter associar aos índices de histórico."""

    job_id: str
    title: str
    video_id: str | None
    completed_at: str
    snippet: str
    source_label: str = "YouTube"


class HistorySearchService:
    """Mantém a política de limites fora do adapter Telegram."""

    max_results = 10

    def __init__(self, repository: TextSearchQuery) -> None:
        self._repository = repository

    def search(
        self, *, user_id: int, query: str, limit: int = max_results
    ) -> list[HistorySearchResult]:
        normalized = " ".join(query.split())
        if not normalized:
            return []
        bounded_limit = max(1, min(limit, self.max_results))
        hits = self._repository.search_completed_for_user(
            user_id=user_id, query=normalized, limit=bounded_limit
        )
        return [self._to_result(hit) for hit in hits]

    @staticmethod
    def _to_result(hit: HistorySearchHit) -> HistorySearchResult:
        return HistorySearchResult(
            job_id=hit.job_id,
            title=hit.title,
            video_id=hit.video_id,
            source_label=hit.source_label,
            completed_at=hit.completed_at.strftime("%Y-%m-%d %H:%M"),
            snippet=hit.snippet,
        )
