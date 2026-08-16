"""Conformance gate for F2 domain/data truth and compatibility migration."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.job_request_context import JobRequestContext
from yt_transcriber_bot.application.services.config_signature import (
    compute_processing_fingerprint,
    processing_fingerprint_payload,
)
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.entities.transcript import Transcript, TranscriptSegment
from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata
from yt_transcriber_bot.domain.value_objects.artifact import ArtifactClass
from yt_transcriber_bot.domain.value_objects.language import LanguageSource
from yt_transcriber_bot.domain.value_objects.media_source import MediaSource
from yt_transcriber_bot.domain.value_objects.provenance import ProcessingProvenance
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
    SCHEMA_VERSION,
    TranscriptSnapshot,
    TranscriptSnapshotRepository,
)
from yt_transcriber_bot.infrastructure.persistence.sqlalchemy.models import JobModel
from yt_transcriber_bot.infrastructure.rendering.markdown_renderer import RenderContext


def test_job_state_machine_rejects_impossible_jump_and_reads_legacy_downloading() -> None:
    job = Job.new(VideoId("dQw4w9WgXcQ"), 42)
    with pytest.raises(ValueError, match="transição inválida"):
        job.transition_to(JobStatus.TRANSCRIBING)

    job.transition_to(JobStatus.ACQUIRING)
    before = job.updated_at
    job.transition_to(JobStatus.ACQUIRING)

    assert job.updated_at == before
    assert JobStatus.from_persisted("downloading") is JobStatus.ACQUIRING
    assert JobStatus.ACQUIRING.value == "acquiring"


def test_request_delivery_context_is_not_part_of_job_domain() -> None:
    job_fields = set(Job.__dataclass_fields__)
    assert "requested_chat_id" not in job_fields
    assert "source_url" not in job_fields
    assert "source_locator" not in job_fields

    context = JobRequestContext("job-1", delivery_chat_id=10, source_locator="opaque-locator")
    assert context.delivery_chat_id == 10
    assert context.source_locator == "opaque-locator"


def test_source_identity_is_canonical_and_source_neutral() -> None:
    video_id = VideoId("dQw4w9WgXcQ")
    youtube = MediaSource.youtube(video_id)
    telegram = MediaSource.telegram_audio("private-file-id")

    assert youtube.canonical_reference == video_id.canonical_url()
    assert telegram.canonical_reference != youtube.canonical_reference
    assert "youtube" not in telegram.canonical_reference.lower()


def test_unknown_language_duration_and_confidence_remain_unknown() -> None:
    metadata = VideoMetadata(
        video_id=VideoId("dQw4w9WgXcQ"),
        title="Unknown facts",
        channel="Channel",
        duration=None,
        upload_date=None,
        original_language=None,
    )
    transcript = Transcript(
        segments=(TranscriptSegment(0, 1, "text", "SPEAKER_00"),),
        language=None,
        language_confidence=None,
    )

    assert metadata.duration is None
    assert metadata.original_language is None
    assert transcript.language is None
    assert transcript.language_confidence is None
    assert transcript.language_source is LanguageSource.UNKNOWN


def test_zero_duration_transcript_segment_is_not_canonical() -> None:
    with pytest.raises(ValueError, match="end_seconds"):
        TranscriptSegment(1.0, 1.0, "ghost", "UNKNOWN")


def test_artifact_taxonomy_separates_canonical_derived_and_volatile() -> None:
    assert ArtifactClass.CANONICAL_STRUCTURED_TRANSCRIPT != ArtifactClass.DERIVED_EXPORT
    assert ArtifactClass.CANONICAL_MARKDOWN != ArtifactClass.VOLATILE_SOURCE_MEDIA
    assert ArtifactClass.OPERATIONAL_LOG != ArtifactClass.RECONSTRUCTIBLE_CACHE


def test_fingerprint_excludes_credentials_paths_and_runtime_bookkeeping(tmp_path: Path) -> None:
    settings = AppSettings(
        telegram_bot_token="token-a",
        telegram_allowed_user_id=42,
        hf_token="hf_a",
        base_dir=tmp_path / "data-a",
        models_dir=tmp_path / "models-a",
    )
    changed = AppSettings(
        telegram_bot_token="token-b",
        telegram_allowed_user_id=42,
        hf_token="hf_b",
        summary_api_key="secret",
        base_dir=tmp_path / "data-b",
        models_dir=tmp_path / "models-b",
        retention_count=17,
    )

    assert compute_processing_fingerprint(settings) == compute_processing_fingerprint(changed)
    assert compute_processing_fingerprint(
        settings, requested_language="pt"
    ) != compute_processing_fingerprint(settings)
    assert compute_processing_fingerprint(
        settings, source_type="youtube"
    ) != compute_processing_fingerprint(settings, source_type="telegram_audio")
    payload = processing_fingerprint_payload(settings)
    for forbidden in (
        "telegram_bot_token",
        "hf_token",
        "summary_api_key",
        "base_dir",
        "models_dir",
        "retention_count",
    ):
        assert forbidden not in payload


def test_sql_schema_keeps_legacy_context_columns_but_adds_explicit_canonical_link() -> None:
    columns = {column.name for column in JobModel.__table__.columns}
    assert "requested_chat_id" in columns
    assert "source_url" in columns
    assert "canonical_transcript_ref" in columns


def test_snapshot_v2_writes_truthful_unknowns_and_v1_remains_readable(tmp_path: Path) -> None:
    repo = TranscriptSnapshotRepository(tmp_path)
    context = RenderContext(
        rendered_at=datetime(2026, 8, 15, tzinfo=UTC),
        whisper_model="small",
        diarization_model="model",
        transcription_source="whisperx",
    )
    snapshot = TranscriptSnapshot(
        metadata=VideoMetadata(
            video_id=VideoId("dQw4w9WgXcQ"),
            title="Unknown",
            channel="Channel",
            duration=None,
            upload_date=None,
            original_language=None,
        ),
        transcript=Transcript(
            segments=(TranscriptSegment(0, 1, "text", "SPEAKER_00"),),
            language=None,
            language_confidence=None,
        ),
        context=context,
        processing_fingerprint="fp",
        processing_provenance=ProcessingProvenance.unknown(),
    )

    path = repo.save("v2", snapshot)
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["schema_version"] == SCHEMA_VERSION == 2
    assert persisted["metadata"]["duration_seconds"] is None
    assert persisted["transcript"]["language"] is None
    assert persisted["transcript"]["language_confidence"] is None

    persisted["schema_version"] = 1
    persisted.pop("processing", None)
    for key in (
        "language_source",
        "requested_language",
        "observed_language",
        "observed_language_confidence",
    ):
        persisted["transcript"].pop(key, None)
    repo.path_for("v1").write_text(json.dumps(persisted), encoding="utf-8")
    legacy = repo.load("v1")
    assert legacy is not None
    assert legacy.processing_provenance == ProcessingProvenance.unknown()
    assert legacy.transcript.language_source is LanguageSource.UNKNOWN


def test_f2_source_guards_against_known_fact_fabrication() -> None:
    youtube = Path("src/yt_transcriber_bot/infrastructure/youtube/yt_dlp_downloader.py").read_text(
        encoding="utf-8"
    )
    whisper = Path(
        "src/yt_transcriber_bot/infrastructure/transcription/whisperx_engine.py"
    ).read_text(encoding="utf-8")
    steps = Path("src/yt_transcriber_bot/application/pipeline/steps.py").read_text(encoding="utf-8")

    assert "Fallback: en" not in youtube
    assert "return Language.en()" not in youtube
    assert "allowed[0]" not in whisper
    assert 'or "pt"' not in steps
    assert "Falha ao persistir snapshot da transcrição" not in steps


def test_structured_consumers_do_not_reconstruct_missing_canonical_reference_from_markdown() -> (
    None
):
    history_source = Path("src/yt_transcriber_bot/infrastructure/telegram/history.py").read_text(
        encoding="utf-8"
    )
    adapter_source = Path(
        "src/yt_transcriber_bot/infrastructure/telegram/bot_adapter.py"
    ).read_text(encoding="utf-8")

    assert "return job.canonical_transcript_ref or" not in history_source
    assert "return job.canonical_transcript_ref or" not in adapter_source
