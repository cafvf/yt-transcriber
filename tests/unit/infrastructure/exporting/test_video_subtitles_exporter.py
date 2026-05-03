from __future__ import annotations

import subprocess
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from yt_transcriber_bot.domain.entities.transcript import Transcript, TranscriptSegment
from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.exporting.transcript_exporter import TranscriptExportService
from yt_transcriber_bot.infrastructure.exporting.video_subtitles_exporter import (
    VideoSoftSubtitleExportService,
    VideoSubtitleTooLargeError,
    VideoSubtitleTooLongError,
    VideoSubtitleExportLimits,
)
from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
    TranscriptSnapshot,
    TranscriptSnapshotRepository,
)
from yt_transcriber_bot.infrastructure.rendering.markdown_renderer import RenderContext


class FakeYDL:
    def __init__(self, params: dict[str, Any], *, payload_size: int = 1024) -> None:
        self.params = params
        self.payload_size = payload_size

    def __enter__(self) -> "FakeYDL":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def extract_info(self, url: str, download: bool = True) -> dict[str, Any]:
        outtmpl = self.params["outtmpl"]
        path = Path(outtmpl.replace("%(ext)s", "mp4"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"0" * self.payload_size)
        return {"requested_downloads": [{"filepath": str(path)}]}


def _snapshot(duration_s: float = 120.0) -> TranscriptSnapshot:
    return TranscriptSnapshot(
        metadata=VideoMetadata(
            video_id=VideoId("dQw4w9WgXcQ"),
            title="Vídeo de teste",
            channel="Canal",
            duration=Duration.from_seconds(duration_s),
            upload_date=date(2026, 5, 1),
            original_language=Language("pt"),
        ),
        transcript=Transcript(
            segments=(TranscriptSegment(0.0, 2.0, "Olá mundo", "SPEAKER_00"),),
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


def _service(
    tmp_path: Path,
    *,
    duration_s: float = 120.0,
    video_payload_size: int = 1024,
    max_size_bytes: int = 200 * 1024 * 1024,
) -> tuple[VideoSoftSubtitleExportService, list[list[str]]]:
    snapshots = TranscriptSnapshotRepository(tmp_path / "segments")
    snapshots.save("video", _snapshot(duration_s=duration_s))
    exporter = TranscriptExportService(snapshots)
    commands: list[list[str]] = []

    def ydl_factory(params: dict[str, Any]) -> FakeYDL:
        return FakeYDL(params, payload_size=video_payload_size)

    def runner(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(cmd)
        Path(cmd[-1]).write_bytes(b"1" * 2048)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    service = VideoSoftSubtitleExportService(
        snapshots=snapshots,
        transcript_exporter=exporter,
        ydl_factory=ydl_factory,
        output_dir=tmp_path / "video_exports",
        limits=VideoSubtitleExportLimits(
            max_duration_seconds=30 * 60,
            max_size_bytes=max_size_bytes,
        ),
        command_runner=runner,
    )
    return service, commands


def test_export_creates_mp4_with_selectable_subtitle_ffmpeg_command(tmp_path: Path) -> None:
    service, commands = _service(tmp_path)
    result = service.export(video_id=VideoId("dQw4w9WgXcQ"), slug="video")
    assert result.path.name == "video-legendas-selecionaveis.mp4"
    assert result.path.is_file()
    assert result.subtitle_path.name == "video.srt"
    assert commands
    cmd = commands[0]
    assert "-c:v" in cmd and "copy" in cmd
    assert "-c:s" in cmd and "mov_text" in cmd
    assert "-map" in cmd


def test_export_rejects_videos_longer_than_30_minutes(tmp_path: Path) -> None:
    service, _ = _service(tmp_path, duration_s=31 * 60)
    with pytest.raises(VideoSubtitleTooLongError):
        service.export(video_id=VideoId("dQw4w9WgXcQ"), slug="video")


def test_export_rejects_downloaded_video_larger_than_limit(tmp_path: Path) -> None:
    service, _ = _service(tmp_path, video_payload_size=4096, max_size_bytes=2048)
    with pytest.raises(VideoSubtitleTooLargeError):
        service.export(video_id=VideoId("dQw4w9WgXcQ"), slug="video")
