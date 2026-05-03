"""Testes do RenameSpeakersService."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from yt_transcriber_bot.application.services.rename_speakers import (
    RenameSpeakersService,
)
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
    MarkdownTranscriptRenderer,
    RenderContext,
)


@pytest.fixture
def snapshot() -> TranscriptSnapshot:
    return TranscriptSnapshot(
        metadata=VideoMetadata(
            video_id=VideoId("dQw4w9WgXcQ"),
            title="Teste Rename",
            channel="Ch",
            duration=Duration.from_seconds(60.0),
            upload_date=date(2024, 1, 1),
            original_language=Language("pt"),
        ),
        transcript=Transcript(
            segments=(
                TranscriptSegment(0.0, 3.0, "Olá", "SPEAKER_00"),
                TranscriptSegment(3.0, 6.0, "Tudo bem?", "SPEAKER_01"),
                TranscriptSegment(6.0, 9.0, "Sim, obrigado.", "SPEAKER_00"),
            ),
            language=Language("pt"),
            language_confidence=0.99,
        ),
        context=RenderContext(
            rendered_at=datetime(2026, 5, 1, tzinfo=UTC),
            whisper_model="small",
            diarization_model="pyannote/speaker-diarization-3.1",
            transcription_source="whisperx",
        ),
    )


@pytest.fixture
def service(tmp_path: Path) -> RenameSpeakersService:
    repo = TranscriptSnapshotRepository(tmp_path / "segments")
    return RenameSpeakersService(repo, MarkdownTranscriptRenderer())


def test_list_speakers(
    service: RenameSpeakersService, snapshot: TranscriptSnapshot, tmp_path: Path
) -> None:
    service._snapshots.save("teste-rename", snapshot)  # type: ignore[attr-defined]
    speakers = service.list_speakers("teste-rename")
    assert speakers == ("SPEAKER_00", "SPEAKER_01")


def test_list_speakers_missing(service: RenameSpeakersService) -> None:
    with pytest.raises(FileNotFoundError, match="Snapshot inexistente"):
        service.list_speakers("ghost")


def test_rename_writes_md_with_aliases(
    service: RenameSpeakersService, snapshot: TranscriptSnapshot, tmp_path: Path
) -> None:
    service._snapshots.save("teste-rename", snapshot)  # type: ignore[attr-defined]
    md = tmp_path / "out.md"
    result = service.rename("teste-rename", {"SPEAKER_00": "João", "SPEAKER_01": "Maria"}, md)
    assert result.speakers_renamed == 2
    assert result.md_path == md
    content = md.read_text()
    assert "João" in content
    assert "Maria" in content
    assert "SPEAKER_00" not in content


def test_rename_partial(
    service: RenameSpeakersService, snapshot: TranscriptSnapshot, tmp_path: Path
) -> None:
    service._snapshots.save("teste-rename", snapshot)  # type: ignore[attr-defined]
    md = tmp_path / "out.md"
    result = service.rename("teste-rename", {"SPEAKER_00": "João"}, md)
    assert result.speakers_renamed == 1
    content = md.read_text()
    assert "João" in content
    assert "SPEAKER_01" in content


def test_rename_ignores_empty_names(
    service: RenameSpeakersService, snapshot: TranscriptSnapshot, tmp_path: Path
) -> None:
    service._snapshots.save("teste-rename", snapshot)  # type: ignore[attr-defined]
    md = tmp_path / "out.md"
    result = service.rename("teste-rename", {"SPEAKER_00": "  ", "SPEAKER_01": "Maria"}, md)
    assert result.speakers_renamed == 1
    content = md.read_text()
    assert "Maria" in content
    assert "SPEAKER_00" in content  # não foi renomeado


def test_rename_ignores_unknown_labels(
    service: RenameSpeakersService, snapshot: TranscriptSnapshot, tmp_path: Path
) -> None:
    service._snapshots.save("teste-rename", snapshot)  # type: ignore[attr-defined]
    md = tmp_path / "out.md"
    result = service.rename("teste-rename", {"SPEAKER_99": "Ghost", "SPEAKER_00": "João"}, md)
    assert result.speakers_renamed == 1


def test_rename_missing_snapshot(service: RenameSpeakersService, tmp_path: Path) -> None:
    md = tmp_path / "out.md"
    with pytest.raises(FileNotFoundError):
        service.rename("ghost", {"SPEAKER_00": "X"}, md)


def test_rename_same_name_merges_speakers_in_markdown(
    service: RenameSpeakersService, snapshot: TranscriptSnapshot, tmp_path: Path
) -> None:
    service._snapshots.save("teste-rename", snapshot)  # type: ignore[attr-defined]
    md = tmp_path / "out.md"

    result = service.rename(
        "teste-rename",
        {"SPEAKER_00": "Christiano", "SPEAKER_01": "Christiano"},
        md,
    )

    assert result.speakers_renamed == 2
    content = md.read_text()
    assert "**Falantes identificados**: 2" in content
    assert "**Falantes após renomeação/mesclagem**: 1" in content
    assert "- **Christiano**: 00:00:09 (100.0%)" in content
    assert content.count("] Christiano") == 1
    assert "SPEAKER_00" not in content
    assert "SPEAKER_01" not in content
