"""Testes do TranscriptSnapshotRepository."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from yt_transcriber_bot.domain.entities.transcript import (
    Transcript,
    TranscriptSegment,
)
from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
    TranscriptSnapshot,
    TranscriptSnapshotRepository,
)
from yt_transcriber_bot.infrastructure.rendering.markdown_renderer import (
    RenderContext,
)


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
    )
    context = RenderContext(
        rendered_at=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        whisper_model="small",
        diarization_model="pyannote/speaker-diarization-3.1",
        transcription_source="whisperx",
    )
    return TranscriptSnapshot(metadata=metadata, transcript=transcript, context=context)


def test_round_trip(tmp_path: Path) -> None:
    repo = TranscriptSnapshotRepository(tmp_path)
    snap = _make_snapshot()
    p = repo.save("hello-world", snap)
    assert p.is_file()
    loaded = repo.load("hello-world")
    assert loaded is not None
    # Round-trip preserva campos críticos
    assert loaded.metadata.title == snap.metadata.title
    assert loaded.metadata.video_id == snap.metadata.video_id
    assert loaded.metadata.original_language == snap.metadata.original_language
    assert loaded.metadata.upload_date == snap.metadata.upload_date
    assert loaded.transcript.language == snap.transcript.language
    assert loaded.transcript.language_confidence == pytest.approx(0.97)
    assert len(loaded.transcript.segments) == 2
    assert loaded.transcript.segments[0].text == "Hello"
    assert loaded.context.whisper_model == "small"


def test_youtube_snapshot_round_trip_preserves_video_identity(tmp_path: Path) -> None:
    repo = TranscriptSnapshotRepository(tmp_path)
    snap = _make_snapshot()

    path = repo.save("youtube", snap)

    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["metadata"]["video_id"] == "dQw4w9WgXcQ"
    assert persisted["metadata"]["source_label"] == "YouTube"
    assert repo.load("youtube") == snap


def test_telegram_snapshot_does_not_persist_synthetic_youtube_identity(
    tmp_path: Path,
) -> None:
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
    metadata = persisted["metadata"]
    assert "video_id" not in metadata
    assert "source_reference" not in metadata
    assert "youtube" not in path.read_text(encoding="utf-8").lower()
    loaded = repo.load("telegram-audio")
    assert loaded is not None
    assert loaded.metadata.video_id is None
    assert loaded.metadata.source_label == "Telegram (mídia privada)"


def test_loads_legacy_snapshot_with_video_id(tmp_path: Path) -> None:
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


def test_load_missing_returns_none(tmp_path: Path) -> None:
    repo = TranscriptSnapshotRepository(tmp_path)
    assert repo.load("ghost") is None


def test_unsupported_schema_version(tmp_path: Path) -> None:
    repo = TranscriptSnapshotRepository(tmp_path)
    repo.path_for("x").parent.mkdir(parents=True, exist_ok=True)
    repo.path_for("x").write_text('{"schema_version": 999}')
    with pytest.raises(ValueError, match="schema_version"):
        repo.load("x")


def test_handles_optional_fields(tmp_path: Path) -> None:
    """upload_date e original_language podem ser None."""
    metadata = VideoMetadata(
        video_id=VideoId("dQw4w9WgXcQ"),
        title="No Date",
        channel="Ch",
        duration=Duration.from_seconds(60.0),
        upload_date=None,
        original_language=None,
    )
    transcript = Transcript(
        segments=(TranscriptSegment(0.0, 1.0, "x", "SPEAKER_00"),),
        language=Language("en"),
        language_confidence=0.5,
    )
    context = RenderContext(
        rendered_at=datetime(2026, 1, 1, tzinfo=UTC),
        whisper_model="base",
        diarization_model="m",
        transcription_source="whisperx",
    )
    repo = TranscriptSnapshotRepository(tmp_path)
    repo.save("no-date", TranscriptSnapshot(metadata, transcript, context))
    loaded = repo.load("no-date")
    assert loaded is not None
    assert loaded.metadata.upload_date is None
    assert loaded.metadata.original_language is None
