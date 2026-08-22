from __future__ import annotations

from yt_transcriber_bot.application.ports.canonical_transcript import CanonicalTranscriptStore
from yt_transcriber_bot.application.ports.derived_artifacts import SummaryArtifactStore
from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.application.ports.text_search import SearchDocument, TextSearchIndex
from yt_transcriber_bot.application.services.text_integrity import normalize_artifact_text
from yt_transcriber_bot.domain.entities.job import Job, JobStatus

_MAX_DOCUMENT_CHARS = 200_000


class SearchIndexingService:
    def __init__(
        self,
        *,
        repository: JobRepository,
        canonical_transcripts: CanonicalTranscriptStore,
        index: TextSearchIndex,
        summaries: SummaryArtifactStore,
    ) -> None:
        self._repository = repository
        self._canonical_transcripts = canonical_transcripts
        self._index = index
        self._summaries = summaries

    def refresh(self, job_or_id: Job | str) -> None:
        job = job_or_id if isinstance(job_or_id, Job) else self._repository.get_by_id(job_or_id)
        job_id = job.job_id if job is not None else str(job_or_id)
        if job is None or job.status is not JobStatus.COMPLETED or not job.canonical_transcript_ref:
            self._index.remove(job_id)
            return
        reference = job.canonical_transcript_ref
        record = self._canonical_transcripts.load(reference)
        if record is None:
            self._index.remove(job.job_id)
            return

        aliases = job.speaker_renames
        transcript = "\n".join(
            f"{aliases.get(segment.speaker_label, segment.speaker_label)}: "
            f"{normalize_artifact_text(segment.text)}"
            for segment in record.transcript.segments
            if segment.text.strip() and segment.end_seconds > segment.start_seconds
        )
        summary = self._summaries.load(job_id=job.job_id, canonical_transcript_ref=reference)
        metadata = " ".join(
            value
            for value in (
                normalize_artifact_text(record.metadata.title),
                normalize_artifact_text(record.metadata.channel),
                record.metadata.source_label,
                job.video_id.value if job.video_id is not None else "",
                job.requested_language.code if job.requested_language is not None else None or "",
                " ".join(aliases.values()),
            )
            if value
        )
        content = normalize_artifact_text(
            "\n".join(
                part for part in (metadata, transcript, summary.content if summary else "") if part
            )
        )[:_MAX_DOCUMENT_CHARS]
        self._index.replace(
            SearchDocument(
                job_id=job.job_id,
                canonical_transcript_ref=reference,
                user_id=job.requested_by_user_id,
                title=normalize_artifact_text(record.metadata.title)[:300]
                or record.metadata.source_label,
                content=content,
                updated_at=job.updated_at,
            )
        )
