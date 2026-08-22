"""Contratos do artefato de texto simples derivado de snapshots."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from yt_transcriber_bot.domain.entities.media_metadata import MediaMetadata
from yt_transcriber_bot.domain.entities.transcript import Transcript, TranscriptSegment
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.exporting.plain_text_exporter import (
    PlainTextTranscriptExportService,
)
from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
    TranscriptSnapshot,
    TranscriptSnapshotRepository,
)
from yt_transcriber_bot.infrastructure.rendering.markdown_renderer import RenderContext


def _snapshot(*, segments: tuple[TranscriptSegment, ...] | None = None) -> TranscriptSnapshot:
    return TranscriptSnapshot(
        metadata=MediaMetadata(
            video_id=VideoId("dQw4w9WgXcQ"),
            title="Vídeo de teste",
            channel="Canal de teste",
            duration=Duration.from_seconds(65.5),
            upload_date=date(2026, 5, 1),
            original_language=Language("pt"),
        ),
        transcript=Transcript(
            segments=segments
            or (
                TranscriptSegment(0.0, 1.25, "Olá mundo", "SPEAKER_00"),
                TranscriptSegment(1.25, 65.5, "Segundo trecho", "SPEAKER_01"),
            ),
            language=Language("pt"),
            language_confidence=0.95,
            source="whisperx",
        ),
        context=RenderContext(
            rendered_at=datetime(2026, 5, 3, 12, 0, tzinfo=UTC),
            whisper_model="inesc-id/WhisperLv3-X-PT-All",
            diarization_model="pyannote/speaker-diarization-community-1",
            transcription_source="whisperx",
        ),
    )


def test_export_writes_sanitized_plain_text_with_minimal_metadata_and_aliases(
    tmp_path: Path,
) -> None:
    snapshots = TranscriptSnapshotRepository(tmp_path / "snapshots")
    snapshots.save(
        "video",
        _snapshot(
            segments=(
                TranscriptSegment(0.0, 1.25, "Ol&aacute;&nbsp;mundo", "SPEAKER_00"),
                TranscriptSegment(1.25, 65.5, "VocÃª chegou", "SPEAKER_01"),
            )
        ),
    )
    service = PlainTextTranscriptExportService(snapshots)
    result = service.export(
        slug="video",
        output_base_path=tmp_path / "exports" / "video.md",
        speaker_aliases={"SPEAKER_00": "Maria"},
    )
    assert "URL: https://www.youtube.com/watch?v=dQw4w9WgXcQ" in result.path.read_text(
        encoding="utf-8"
    )


def test_plain_text_telegram_source_omits_synthetic_youtube_identity(tmp_path: Path) -> None:
    snapshots = TranscriptSnapshotRepository(tmp_path / "snapshots")
    snap = _snapshot()
    snapshots.save(
        "audio",
        replace(snap, metadata=replace(snap.metadata, source_label="Telegram (mídia privada)")),
    )
    result = PlainTextTranscriptExportService(snapshots).export(
        slug="audio", output_base_path=tmp_path / "audio", speaker_aliases={}
    )
    rendered = result.path.read_text(encoding="utf-8")
    assert "Origem: Telegram (mídia privada)" in rendered
    assert "Vídeo:" not in rendered
    assert "youtube.com" not in rendered


def test_export_filters_blank_segments_and_keeps_only_transcript_text(tmp_path: Path) -> None:
    snapshots = TranscriptSnapshotRepository(tmp_path / "snapshots")
    snapshots.save(
        "video",
        _snapshot(
            segments=(
                TranscriptSegment(1.0, 2.0, "   ", "UNKNOWN"),
                TranscriptSegment(2.0, 3.0, "Texto **sem Markdown**", "SPEAKER_00"),
            )
        ),
    )
    service = PlainTextTranscriptExportService(snapshots)

    result = service.export(slug="video", output_base_path=tmp_path / "video.md")

    text = result.path.read_text(encoding="utf-8")
    assert "UNKNOWN" not in text
    assert "SPEAKER_00: Texto sem Markdown" in text
    assert "**" not in text


def test_export_missing_snapshot_raises_file_not_found(tmp_path: Path) -> None:
    service = PlainTextTranscriptExportService(TranscriptSnapshotRepository(tmp_path / "snapshots"))

    with pytest.raises(FileNotFoundError, match="Snapshot inexistente: missing"):
        service.export(slug="missing", output_base_path=tmp_path / "missing.md")
