"""Testes do TranscriptSnapshotRepository v2 e compatibilidade v1."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from yt_transcriber_bot.domain.entities.transcript import Transcript, TranscriptSegment
from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language, LanguageSource
from yt_transcriber_bot.domain.value_objects.provenance import ProcessingProvenance
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
    SCHEMA_VERSION,
    TranscriptSnapshot,
    TranscriptSnapshotRepository,
)
from yt_transcriber_bot.infrastructure.rendering.markdown_renderer import RenderContext


def _make_snapshot() -> TranscriptSnapshot:
    metadata = VideoMetadata(
        video_id=VideoId("dQw4w9WgXcQ"),
        title="Hello World",
        channel="Test Channel",
        duration=Duration.from_seconds(120.0),
        upload_date=date(2024, 3, 15),
        original_language=Language("en"),
        has_alternate_audio_tracks=True,
        alternate_languages=(Language("pt"),),
    )
    transcript = Transcript(
        segments=(
            TranscriptSegment(0.0, 5.0, "Hello", "SPEAKER_00"),
            TranscriptSegment(5.0, 10.0, "World", "SPEAKER_01"),
        ),
        language=Language("en"),
        language_confidence=0.97,
        source="whisperx",
        observed_language=Language("en"),
        observed_language_confidence=0.97,
        language_source=LanguageSource.ASR,
    )
    context = RenderContext(
        rendered_at=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        whisper_model="small",
        diarization_model="pyannote/speaker-diarization-3.1",
        transcription_source="whisperx",
    )
    return TranscriptSnapshot(
        metadata=metadata,
        transcript=transcript,
        context=context,
        processing_fingerprint="fingerprint-v1",
        processing_provenance=ProcessingProvenance(
            processing_path="audio_asr",
            transcription_backend="whisperx",
            transcription_model="small",
            device="cpu",
            compute_type="int8",
            asr_fallback_used=False,
            diarization_backend="composite",
            diarization_model="pyannote/speaker-diarization-community-1",
            language_source="asr",
        ),
    )


def test_round_trip_v2_preserves_canonical_facts(tmp_path: Path) -> None:
    repo = TranscriptSnapshotRepository(tmp_path)
    snap = _make_snapshot()

    path = repo.save("hello-world", snap)
    persisted = json.loads(path.read_text(encoding="utf-8"))
    loaded = repo.load("hello-world")

    assert persisted["schema_version"] == SCHEMA_VERSION == 2
    assert loaded == snap
    assert loaded is not None
    assert loaded.processing_fingerprint == "fingerprint-v1"
    assert loaded.processing_provenance.transcription_model == "small"


def test_youtube_snapshot_round_trip_preserves_video_identity(tmp_path: Path) -> None:
    repo = TranscriptSnapshotRepository(tmp_path)
    snap = _make_snapshot()

    path = repo.save("youtube", snap)

    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["metadata"]["video_id"] == "dQw4w9WgXcQ"
    assert persisted["metadata"]["source_label"] == "YouTube"
    assert repo.load("youtube") == snap


def test_telegram_snapshot_does_not_persist_synthetic_youtube_identity(tmp_path: Path) -> None:
    repo = TranscriptSnapshotRepository(tmp_path)
    original = _make_snapshot()
    snap = TranscriptSnapshot(
        metadata=VideoMetadata(
            video_id=None,
            title="Mensagem de voz",
            channel="Telegram",
            duration=Duration.from_seconds(42),
            upload_date=None,
            original_language=None,
            source_label="Telegram (mídia privada)",
        ),
        transcript=original.transcript,
        context=original.context,
    )

    path = repo.save("telegram-audio", snap)
    persisted = json.loads(path.read_text(encoding="utf-8"))

    assert "video_id" not in persisted["metadata"]
    assert "source_reference" not in persisted["metadata"]
    loaded = repo.load("telegram-audio")
    assert loaded is not None
    assert loaded.metadata.video_id is None
    assert loaded.metadata.source_label == "Telegram (mídia privada)"


def test_loads_legacy_v1_snapshot_with_unknown_provenance(tmp_path: Path) -> None:
    repo = TranscriptSnapshotRepository(tmp_path)
    legacy = {
        "schema_version": 1,
        "metadata": {
            "video_id": "dQw4w9WgXcQ",
            "title": "Hello World",
            "channel": "Test Channel",
            "duration_seconds": 120.0,
            "upload_date": "2024-03-15",
            "original_language": "en",
            "has_alternate_audio_tracks": True,
            "alternate_languages": ["pt"],
        },
        "transcript": {
            "language": "en",
            "language_confidence": 0.97,
            "source": "whisperx",
            "segments": [],
        },
        "context": {
            "rendered_at": "2026-05-01T12:00:00+00:00",
            "whisper_model": "small",
            "diarization_model": "pyannote/speaker-diarization-3.1",
            "transcription_source": "whisperx",
        },
    }
    repo.path_for("legacy").parent.mkdir(parents=True, exist_ok=True)
    repo.path_for("legacy").write_text(json.dumps(legacy), encoding="utf-8")

    loaded = repo.load("legacy")

    assert loaded is not None
    assert loaded.metadata.video_id == VideoId("dQw4w9WgXcQ")
    assert loaded.metadata.source_label == "YouTube"
    assert loaded.processing_fingerprint == ""
    assert loaded.processing_provenance == ProcessingProvenance.unknown()
    assert loaded.transcript.language_source is LanguageSource.UNKNOWN


def test_unknown_duration_language_and_confidence_round_trip_as_unknown(tmp_path: Path) -> None:
    repo = TranscriptSnapshotRepository(tmp_path)
    original = _make_snapshot()
    snapshot = TranscriptSnapshot(
        metadata=VideoMetadata(
            video_id=VideoId("dQw4w9WgXcQ"),
            title="Unknown facts",
            channel="Channel",
            duration=None,
            upload_date=None,
            original_language=None,
        ),
        transcript=Transcript(
            segments=original.transcript.segments,
            language=None,
            language_confidence=None,
        ),
        context=original.context,
    )

    repo.save("unknown", snapshot)
    loaded = repo.load("unknown")

    assert loaded is not None
    assert loaded.metadata.duration is None
    assert loaded.metadata.original_language is None
    assert loaded.transcript.language is None
    assert loaded.transcript.language_confidence is None


def test_atomic_save_leaves_no_temp_file(tmp_path: Path) -> None:
    repo = TranscriptSnapshotRepository(tmp_path)
    path = repo.save("atomic", _make_snapshot())

    assert path.exists()
    assert not list(tmp_path.glob("*.tmp"))
    assert not list(tmp_path.glob(".*.tmp"))


def test_load_missing_returns_none(tmp_path: Path) -> None:
    assert TranscriptSnapshotRepository(tmp_path).load("ghost") is None


def test_unsupported_schema_version(tmp_path: Path) -> None:
    repo = TranscriptSnapshotRepository(tmp_path)
    repo.path_for("x").parent.mkdir(parents=True, exist_ok=True)
    repo.path_for("x").write_text('{"schema_version": 999}', encoding="utf-8")
    with pytest.raises(ValueError, match="schema_version"):
        repo.load("x")
