from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.operational_errors import OperationalErrorCode
from yt_transcriber_bot.application.ports.cache import CacheCleanupResult
from yt_transcriber_bot.application.ports.canonical_transcript import (
    CanonicalTranscriptRecord,
    TranscriptRenderContext,
)
from yt_transcriber_bot.application.ports.derived_artifacts import (
    DerivedArtifactAssociation,
    StoredSummaryArtifact,
)
from yt_transcriber_bot.application.ports.operational_error import (
    JobLogReader,
    OperationalErrorRecord,
    OperationalErrorStore,
)
from yt_transcriber_bot.application.ports.text_search import SearchDocument, TextSearchIndex
from yt_transcriber_bot.application.services.last_error import LastErrorService
from yt_transcriber_bot.application.services.search_indexing import SearchIndexingService
from yt_transcriber_bot.application.workflows.derivatives import TranscriptDerivativeWorkflow
from yt_transcriber_bot.application.workflows.history import CompletedHistoryWorkflow
from yt_transcriber_bot.application.workflows.operations import OperationalWorkflow
from yt_transcriber_bot.configuration.external_services import TextGenerationEndpointPolicy
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.entities.media_metadata import MediaMetadata
from yt_transcriber_bot.domain.entities.transcript import Transcript, TranscriptSegment
from yt_transcriber_bot.domain.value_objects.artifact import ArtifactClass
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.media_source import MediaSource
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.persistence.filesystem.reconstructible_cache import (
    FilesystemReconstructibleCache,
)


class _Repo:
    def __init__(self, jobs: list[Job]) -> None:
        self.jobs = jobs
        self.saved: list[Job] = []

    def list_recent_for_user(self, user_id: int, limit: int) -> list[Job]:
        jobs = [job for job in self.jobs if job.requested_by_user_id == user_id]
        return sorted(jobs, key=lambda job: job.updated_at, reverse=True)[:limit]

    def get_by_id(self, job_id: str) -> Job | None:
        return next((job for job in self.jobs if job.job_id == job_id), None)

    def save(self, job: Job) -> None:
        self.saved.append(job)


class _Errors(OperationalErrorStore):
    def __init__(self, records: list[OperationalErrorRecord] | None = None) -> None:
        self.records = list(records or [])

    def append(self, record: OperationalErrorRecord) -> None:
        self.records.append(record)

    def latest_for_user(self, user_id: int, *, limit: int) -> OperationalErrorRecord | None:
        matches = [row for row in self.records if row.user_id == user_id][-limit:]
        return max(matches, key=lambda row: row.occurred_at) if matches else None


class _Logs(JobLogReader):
    def tail(self, path: Path, *, max_lines: int, max_chars: int) -> str:
        _ = (path, max_lines, max_chars)
        return "safe tail"


def _complete(job: Job) -> Job:
    for status in (
        JobStatus.ACQUIRING,
        JobStatus.CONVERTING,
        JobStatus.TRANSCRIBING,
        JobStatus.DIARIZING,
        JobStatus.RENDERING,
        JobStatus.DELIVERING,
        JobStatus.COMPLETED,
    ):
        job.transition_to(status)
    return job


def _delivery_failed(job: Job) -> Job:
    for status in (
        JobStatus.ACQUIRING,
        JobStatus.CONVERTING,
        JobStatus.TRANSCRIBING,
        JobStatus.DIARIZING,
        JobStatus.RENDERING,
        JobStatus.DELIVERING,
    ):
        job.transition_to(status)
    job.transition_to(JobStatus.DELIVERY_FAILED, error="telegram unavailable")
    return job


def test_p05_008_history_positions_are_current_and_unreadable_evidence_is_explicit(
    tmp_path: Path,
) -> None:
    old = _complete(Job.new(VideoId("aaaaaaaaaaa"), 7))
    new = _complete(Job.new(VideoId("bbbbbbbbbbb"), 7))
    old.updated_at = datetime(2026, 8, 17, 10, tzinfo=UTC)
    new.updated_at = datetime(2026, 8, 17, 11, tzinfo=UTC)
    old.md_path = str(tmp_path / "old.md")
    new.md_path = str(tmp_path / "new.md")
    workflow = CompletedHistoryWorkflow(_Repo([old, new]), markdown_available=lambda _p: False)  # type: ignore[arg-type]
    assert workflow.select(7, index=1) is new
    new.updated_at = datetime(2026, 8, 17, 9, tzinfo=UTC)
    assert workflow.select(7, index=1) is old
    assert workflow.resolve_markdown(old).markdown_state.value == "missing_file"


def test_p05_009_index_document_uses_canonical_text_aliases_and_summary_not_staging() -> None:
    job = _complete(Job.new(VideoId("dQw4w9WgXcQ"), 7))
    job.canonical_transcript_ref = "canonical"
    job.speaker_renames = {"SPEAKER_00": "Alice"}
    metadata = MediaMetadata(
        video_id=job.video_id,
        title="Título",
        channel="Canal",
        duration=Duration.from_seconds(60),
        upload_date=date(2026, 8, 17),
        original_language=Language("pt"),
    )
    record = CanonicalTranscriptRecord(
        metadata=metadata,
        transcript=Transcript(
            segments=(TranscriptSegment(0.0, 2.0, "conteúdo canônico", "SPEAKER_00"),),
            language=Language("pt"),
            language_confidence=0.9,
        ),
        context=TranscriptRenderContext(
            rendered_at=datetime(2026, 8, 17, tzinfo=UTC),
            whisper_model="small",
            diarization_model="model",
            transcription_source="whisperx",
        ),
    )

    class Canonical:
        def load(self, reference: str) -> CanonicalTranscriptRecord | None:
            return record if reference == "canonical" else None

    association = DerivedArtifactAssociation.from_job(job, ArtifactClass.DERIVED_SUMMARY)
    summary = StoredSummaryArtifact(association, Path("summary.md"), "síntese aprovada")

    class Summaries:
        def load(
            self, *, job_id: str, canonical_transcript_ref: str
        ) -> StoredSummaryArtifact | None:
            _ = (job_id, canonical_transcript_ref)
            return summary

    class Index(TextSearchIndex):
        def __init__(self) -> None:
            self.document: SearchDocument | None = None

        def replace(self, document: SearchDocument) -> None:
            self.document = document

        def remove(self, job_id: str) -> None:
            _ = job_id

    index = Index()
    SearchIndexingService(
        repository=_Repo([job]),  # type: ignore[arg-type]
        canonical_transcripts=Canonical(),  # type: ignore[arg-type]
        index=index,
        summaries=Summaries(),  # type: ignore[arg-type]
    ).refresh(job)
    assert index.document is not None
    assert "Alice: conteúdo canônico" in index.document.content
    assert "síntese aprovada" in index.document.content
    assert "/private/staging" not in index.document.content


def test_p05_011_nonlocal_summary_requires_explicit_operator_configuration() -> None:
    policy = TextGenerationEndpointPolicy(
        base_url="https://example.invalid/v1",
        model="model",
        explicitly_configured=False,
    )
    with pytest.raises(ValueError, match="explicit SUMMARY_BASE_URL"):
        policy.require_transcript_disclosure_allowed()


def test_p05_013_non_youtube_video_derivative_rejected_without_mutating_completed_job() -> None:
    job = _complete(
        Job.new(video_id=None, user_id=7, media_source=MediaSource.telegram_audio("file"))
    )
    job.canonical_transcript_ref = "canonical"

    class History:
        def select(self, user_id: int, *, index: int) -> Job | None:
            return job if (user_id, index) == (7, 1) else None

    class Gateway:
        def export_video(self, **kwargs: object) -> object:
            raise AssertionError(f"gateway must not be called: {kwargs}")

    before = job.status
    workflow = TranscriptDerivativeWorkflow(
        repository=_Repo([job]),  # type: ignore[arg-type]
        history=History(),  # type: ignore[arg-type]
        rename_service=object(),  # type: ignore[arg-type]
        gateway=Gateway(),  # type: ignore[arg-type]
        indexer=object(),  # type: ignore[arg-type]
        transcripts_dir=Path("transcripts"),
    )
    with pytest.raises(ValueError, match="apenas para transcrições do YouTube"):
        workflow.export_video(user_id=7, index=1)
    assert job.status is before is JobStatus.COMPLETED


def test_p05_015_delivery_failed_reports_only_artifacts_confirmed_available(tmp_path: Path) -> None:
    job = _delivery_failed(Job.new(VideoId("dQw4w9WgXcQ"), 7))
    md = tmp_path / "kept.md"
    audio = tmp_path / "gone.opus"
    md.write_text("kept", encoding="utf-8")
    job.md_path = str(md)
    job.audio_path = str(audio)
    service = LastErrorService(
        repository=_Repo([job]),  # type: ignore[arg-type]
        settings=AppSettings(_env_file=None, telegram_allowed_user_id=7),
        error_store=_Errors(),
        log_reader=_Logs(),
        artifact_available=lambda path: path.is_file(),
    )
    before = job.status
    message = service.latest_for_user(7).message
    assert "Markdown parcial: disponível" in message
    assert "Áudio parcial: disponível" not in message
    assert job.status is before is JobStatus.DELIVERY_FAILED


def test_p05_015_operational_error_wins_timestamp_tie() -> None:
    job = _delivery_failed(Job.new(VideoId("dQw4w9WgXcQ"), 7))
    when = datetime(2026, 8, 17, 12, tzinfo=UTC)
    job.updated_at = when
    operational = OperationalErrorRecord(
        user_id=7,
        operation="summary",
        code=OperationalErrorCode.TEXT_GENERATION_TIMEOUT,
        safe_message="timeout",
        occurred_at=when,
    )
    report = LastErrorService(
        repository=_Repo([job]),  # type: ignore[arg-type]
        settings=AppSettings(_env_file=None, telegram_allowed_user_id=7),
        error_store=_Errors([operational]),
        log_reader=_Logs(),
    ).latest_for_user(7)
    assert report.operational_error is operational


def test_p05_016_cache_refuses_protected_or_ambiguous_roots(tmp_path: Path) -> None:
    protected = tmp_path / "data" / "transcripts"
    protected.mkdir(parents=True)
    with pytest.raises(ValueError, match="protected application data"):
        FilesystemReconstructibleCache((tmp_path / "data",), protected_paths=(protected,))
    models = tmp_path / "models"
    with pytest.raises(ValueError, match="ambiguous"):
        FilesystemReconstructibleCache((models, models / "nested"))


def test_p05_016_partial_cache_failure_is_recorded_without_raw_path() -> None:
    class Health:
        def run(self) -> object:
            return object()

    class Last:
        def __init__(self) -> None:
            self.kwargs: dict[str, object] | None = None

        def latest_for_user(self, user_id: int) -> object:
            return user_id

        def record_operation_error(self, **kwargs: object) -> None:
            self.kwargs = dict(kwargs)

    class Cache:
        def clear(self) -> CacheCleanupResult:
            return CacheCleanupResult(1, 0, 2)

    class Retention:
        def apply(self) -> object:
            return object()

    last = Last()
    workflow = OperationalWorkflow(
        healthcheck=Health(),  # type: ignore[arg-type]
        last_error=last,  # type: ignore[arg-type]
        cache=Cache(),  # type: ignore[arg-type]
        retention=Retention(),  # type: ignore[arg-type]
    )
    result = workflow.clear_cache(user_id=7)
    assert result.failures == 2
    assert last.kwargs is not None
    assert last.kwargs["operation"] == "clearcache"
    assert last.kwargs["stage"] == "cache_cleanup"
    assert "/" not in str(last.kwargs["message"])
