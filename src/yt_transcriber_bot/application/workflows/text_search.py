from __future__ import annotations

from dataclasses import dataclass

from yt_transcriber_bot.application.ports.text_search import TextSearchQuery
from yt_transcriber_bot.application.services.search_indexing import SearchIndexingService
from yt_transcriber_bot.application.workflows.history import CompletedHistoryWorkflow


@dataclass(frozen=True, slots=True)
class TextSearchResult:
    history_index: int
    job_id: str
    title: str
    video_id: str | None
    source_label: str
    completed_at: str
    snippet: str


class TextSearchWorkflow:
    max_results = 10
    rebuild_limit = 200

    def __init__(
        self,
        *,
        history: CompletedHistoryWorkflow,
        query: TextSearchQuery,
        indexer: SearchIndexingService,
    ) -> None:
        self._history = history
        self._query = query
        self._indexer = indexer

    def search(
        self, *, user_id: int, query: str, limit: int = max_results
    ) -> list[TextSearchResult]:
        normalized = " ".join(query.split())
        if not normalized:
            return []
        history = self._history.list_completed(user_id, limit=self.rebuild_limit)
        for job in history:
            self._indexer.refresh(job)
        indexes = {job.job_id: index for index, job in enumerate(history, start=1)}
        hits = self._query.search_completed_for_user(
            user_id=user_id,
            query=normalized,
            limit=max(1, min(limit, self.max_results)),
        )
        return [
            TextSearchResult(
                history_index=indexes[hit.job_id],
                job_id=hit.job_id,
                title=hit.title,
                video_id=hit.video_id,
                source_label=hit.source_label,
                completed_at=hit.completed_at.strftime("%Y-%m-%d %H:%M"),
                snippet=hit.snippet,
            )
            for hit in hits
            if hit.job_id in indexes
        ]
