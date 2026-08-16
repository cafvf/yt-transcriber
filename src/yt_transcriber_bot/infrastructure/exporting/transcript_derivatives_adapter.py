from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from yt_transcriber_bot.application.ports.derived_artifacts import (
    GeneratedDerivativeFile,
    TranscriptDerivativeGateway,
)
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.exporting.plain_text_exporter import (
    PlainTextTranscriptExportService,
)
from yt_transcriber_bot.infrastructure.exporting.transcript_exporter import TranscriptExportService
from yt_transcriber_bot.infrastructure.exporting.video_subtitles_exporter import (
    VideoSoftSubtitleExportService,
)


class TranscriptDerivativesAdapter(TranscriptDerivativeGateway):
    def __init__(
        self,
        *,
        text: PlainTextTranscriptExportService,
        transcript: TranscriptExportService,
        video: VideoSoftSubtitleExportService,
    ) -> None:
        self._text = text
        self._transcript = transcript
        self._video = video

    def export_text(
        self,
        *,
        canonical_transcript_ref: str,
        output_base_path: Path,
        speaker_aliases: Mapping[str, str],
    ) -> GeneratedDerivativeFile:
        result = self._text.export(
            slug=canonical_transcript_ref,
            output_base_path=output_base_path,
            speaker_aliases=speaker_aliases,
        )
        return GeneratedDerivativeFile(result.path, "txt")

    def export_transcript(
        self,
        *,
        canonical_transcript_ref: str,
        output_base_path: Path,
        format: str,
        speaker_aliases: Mapping[str, str],
    ) -> GeneratedDerivativeFile:
        result = self._transcript.export(
            slug=canonical_transcript_ref,
            output_base_path=output_base_path,
            format=format,
            speaker_aliases=speaker_aliases,
        )
        return GeneratedDerivativeFile(result.path, result.format)

    def export_video(
        self,
        *,
        video_id: VideoId,
        canonical_transcript_ref: str,
        speaker_aliases: Mapping[str, str],
    ) -> GeneratedDerivativeFile:
        result = self._video.export(
            video_id=video_id,
            slug=canonical_transcript_ref,
            speaker_aliases=speaker_aliases,
        )
        return GeneratedDerivativeFile(result.path, "mp4", result.size_bytes)
