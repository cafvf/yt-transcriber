"""Entidade ``VideoMetadata`` — metadados de uma mídia transcrita."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


@dataclass(frozen=True, slots=True)
class VideoMetadata:
    """Metadados da mídia; YouTube requer uma identidade de vídeo."""

    video_id: VideoId | None
    title: str
    channel: str
    duration: Duration
    upload_date: date | None
    original_language: Language | None
    has_alternate_audio_tracks: bool = False
    alternate_languages: tuple[Language, ...] = field(default_factory=tuple)
    source_label: str = "YouTube"
    source_reference: str | None = None

    def __post_init__(self) -> None:
        if not self.title or not self.title.strip():
            raise ValueError("VideoMetadata.title não pode ser vazio")
        if not self.channel or not self.channel.strip():
            raise ValueError("VideoMetadata.channel não pode ser vazio")
        if self.source_label == "YouTube" and self.video_id is None:
            raise ValueError("VideoMetadata.video_id é obrigatório para YouTube")

    def canonical_url(self) -> str:
        if self.source_reference:
            return self.source_reference
        if self.video_id is None:
            raise ValueError("Mídia sem URL canônica")
        return self.video_id.canonical_url()
