from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from yt_transcriber_bot.application.ports.derived_artifacts import (
    DerivedArtifactAssociation,
    SummaryArtifactStore,
)
from yt_transcriber_bot.application.services.search_indexing import SearchIndexingService
from yt_transcriber_bot.application.services.transcript_summary import (
    SummaryProgress,
    TranscriptSummaryService,
)
from yt_transcriber_bot.application.workflows.history import CompletedHistoryWorkflow
from yt_transcriber_bot.domain.value_objects.artifact import ArtifactClass


@dataclass(frozen=True, slots=True)
class SummaryWorkflowResult:
    association: DerivedArtifactAssociation
    path: Path
    chunks: int
    model: str


class SummaryWorkflow:
    def __init__(
        self,
        *,
        history: CompletedHistoryWorkflow,
        summary_policy: TranscriptSummaryService,
        store: SummaryArtifactStore,
        indexer: SearchIndexingService,
    ) -> None:
        self._history = history
        self._summary_policy = summary_policy
        self._store = store
        self._indexer = indexer

    def summarize(
        self,
        *,
        user_id: int,
        index: int,
        on_progress: Callable[[SummaryProgress], None] | None = None,
    ) -> SummaryWorkflowResult:
        if index <= 0:
            raise ValueError("Use um número positivo.")
        job = self._history.select(user_id, index=index)
        if job is None:
            raise LookupError(f"Não encontrei a transcrição #{index}.")
        association = DerivedArtifactAssociation.from_job(job, ArtifactClass.DERIVED_SUMMARY)
        generated = self._summary_policy.summarize(
            slug=association.canonical_transcript_ref,
            output_base_path=Path(association.canonical_transcript_ref),
            speaker_aliases=job.speaker_renames,
            on_progress=on_progress,
        )
        stored = self._store.save(association, generated.content)
        self._indexer.refresh(job)
        return SummaryWorkflowResult(association, stored.path, generated.chunks, generated.model)
