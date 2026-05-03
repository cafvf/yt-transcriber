"""Entidade ``VideoMetadata`` — metadados extraídos do YouTube."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


@dataclass(frozen=True, slots=True)
class VideoMetadata:
    """Metadados de um vídeo do YouTube."""

    video_id: VideoId
    title: str
    channel: str
    duration: Duration
    upload_date: date | None
    original_language: Language | None
    has_alternate_audio_tracks: bool = False
    alternate_languages: tuple[Language, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.title or not self.title.strip():
            raise ValueError("VideoMetadata.title não pode ser vazio")
        if not self.channel or not self.channel.strip():
            raise ValueError("VideoMetadata.channel não pode ser vazio")

    def canonical_url(self) -> str:
        return self.video_id.canonical_url()
