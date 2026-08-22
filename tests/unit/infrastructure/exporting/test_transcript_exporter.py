from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from yt_transcriber_bot.domain.entities.media_metadata import MediaMetadata
from yt_transcriber_bot.domain.entities.transcript import Transcript, TranscriptSegment
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.exporting.transcript_exporter import (
    TranscriptExportService,
)
from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
    TranscriptSnapshot,
    TranscriptSnapshotRepository,
)
from yt_transcriber_bot.infrastructure.rendering.markdown_renderer import RenderContext


def _snapshot() -> TranscriptSnapshot:
    return TranscriptSnapshot(
        metadata=MediaMetadata(
            video_id=VideoId("dQw4w9WgXcQ"),
            title="Vídeo de teste",
            channel="Canal",
            duration=Duration.from_seconds(65.5),
            upload_date=date(2026, 5, 1),
            original_language=Language("pt"),
        ),
        transcript=Transcript(
            segments=(
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


@pytest.fixture
def service(tmp_path: Path) -> TranscriptExportService:
    repo = TranscriptSnapshotRepository(tmp_path / "segments")
    repo.save("video", _snapshot())
    return TranscriptExportService(repo)


def test_export_json_contains_metadata_segments_and_aliases(
    service: TranscriptExportService, tmp_path: Path
) -> None:
    result = service.export(
        slug="video",
        output_base_path=tmp_path / "exports" / "video.md",
        format="json",
        speaker_aliases={"SPEAKER_00": "Maria"},
    )
    assert result.path.name == "video.json"
    data = json.loads(result.path.read_text())
    assert data["schema_version"] == 1
    assert data["metadata"]["title"] == "Vídeo de teste"
    assert data["transcript"]["speaker_aliases"] == {"SPEAKER_00": "Maria"}
    assert data["transcript"]["segments"][0]["speaker"] == "Maria"
    assert data["transcript"]["segments"][1]["speaker"] == "SPEAKER_01"


def test_export_json_telegram_source_omits_synthetic_youtube_identity(tmp_path: Path) -> None:
    repo = TranscriptSnapshotRepository(tmp_path / "segments")
    snap = _snapshot()
    repo.save(
        "audio",
        replace(snap, metadata=replace(snap.metadata, source_label="Telegram (mídia privada)")),
    )
    result = TranscriptExportService(repo).export(
        slug="audio", output_base_path=tmp_path / "audio", format="json", speaker_aliases={}
    )
    metadata = json.loads(result.path.read_text())["metadata"]
    assert metadata["source"] == "Telegram (mídia privada)"
    assert "video_id" not in metadata
    assert "url" not in metadata


def test_export_srt_uses_comma_milliseconds_and_sequence_numbers(
    service: TranscriptExportService, tmp_path: Path
) -> None:
    result = service.export(
        slug="video",
        output_base_path=tmp_path / "video.md",
        format="srt",
        speaker_aliases={"SPEAKER_00": "Maria"},
    )
    text = result.path.read_text()
    assert text.startswith("1\n00:00:00,000 --> 00:00:01,250\nMaria: Olá mundo")
    assert "2\n00:00:01,250 --> 00:01:05,500\nSPEAKER_01: Segundo trecho" in text


def test_export_vtt_starts_with_webvtt_and_uses_dot_milliseconds(
    service: TranscriptExportService, tmp_path: Path
) -> None:
    result = service.export(
        slug="video",
        output_base_path=tmp_path / "video.md",
        format="vtt",
        speaker_aliases={},
    )
    text = result.path.read_text()
    assert text.startswith("WEBVTT\n\n")
    assert "00:00:00.000 --> 00:00:01.250\nSPEAKER_00: Olá mundo" in text


def test_export_invalid_format_raises_value_error(
    service: TranscriptExportService, tmp_path: Path
) -> None:
    with pytest.raises(ValueError, match="Formato de exportação inválido"):
        service.export(slug="video", output_base_path=tmp_path / "video.md", format="pdf")


def test_export_missing_snapshot_raises_file_not_found(tmp_path: Path) -> None:
    service = TranscriptExportService(TranscriptSnapshotRepository(tmp_path / "segments"))
    with pytest.raises(FileNotFoundError):
        service.export(slug="missing", output_base_path=tmp_path / "missing.md", format="json")


def test_export_normalizes_entities(tmp_path: Path) -> None:
    repo = TranscriptSnapshotRepository(tmp_path / "segments")
    repo.save(
        "video",
        TranscriptSnapshot(
            metadata=_snapshot().metadata,
            transcript=Transcript(
                segments=(TranscriptSegment(0.0, 1.25, "Ol&aacute;&nbsp;mundo", "SPEAKER_00"),),
                language=Language("pt"),
                language_confidence=0.95,
                source="youtube_manual",
            ),
            context=_snapshot().context,
        ),
    )
    service = TranscriptExportService(repo)

    srt = service.export(slug="video", output_base_path=tmp_path / "video.md", format="srt")
    srt_text = srt.path.read_text()
    assert "Olá mundo" in srt_text
    assert "&nbsp;" not in srt_text

    payload = service.export(slug="video", output_base_path=tmp_path / "video.md", format="json")
    data = json.loads(payload.path.read_text())
    assert len(data["transcript"]["segments"]) == 1
    assert data["transcript"]["segments"][0]["speaker"] == "SPEAKER_00"
    assert data["transcript"]["segments"][0]["text"] == "Olá mundo"


def test_export_repairs_mojibake_in_derived_artifacts(tmp_path: Path) -> None:
    repo = TranscriptSnapshotRepository(tmp_path / "segments")
    snapshot = _snapshot()
    repo.save(
        "video",
        TranscriptSnapshot(
            metadata=snapshot.metadata,
            transcript=Transcript(
                segments=(
                    TranscriptSegment(
                        0.0,
                        1.25,
                        "VocÃª nÃ£o tem aÃ§Ã£o",
                        "SPEAKER_00",
                    ),
                ),
                language=Language("pt"),
                language_confidence=0.95,
                source="whisperx",
            ),
            context=snapshot.context,
        ),
    )
    service = TranscriptExportService(repo)

    srt = service.export(slug="video", output_base_path=tmp_path / "video.md", format="srt")
    assert "SPEAKER_00: Você não tem ação" in srt.path.read_text(encoding="utf-8")

    payload = service.export(slug="video", output_base_path=tmp_path / "video.md", format="json")
    data = json.loads(payload.path.read_text(encoding="utf-8"))
    assert data["transcript"]["segments"][0]["text"] == "Você não tem ação"
