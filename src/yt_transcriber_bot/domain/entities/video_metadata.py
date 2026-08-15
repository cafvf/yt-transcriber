"""Metadados source-neutral de uma mídia processada."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


@dataclass(frozen=True, slots=True)
class MediaMetadata:
    """Metadados conhecidos; fatos ausentes permanecem ``None``.

    O nome histórico ``VideoMetadata`` é mantido como alias abaixo para evitar
    uma migração puramente nominal em consumidores internos nesta fase.
    """

    video_id: VideoId | None
    title: str
    channel: str
    duration: Duration | None
    upload_date: date | None
    original_language: Language | None
    has_alternate_audio_tracks: bool = False
    alternate_languages: tuple[Language, ...] = field(default_factory=tuple)
    source_label: str = "YouTube"
    source_reference: str | None = None

    def __post_init__(self) -> None:
        if not self.title or not self.title.strip():
            raise ValueError("MediaMetadata.title não pode ser vazio")
        if not self.channel or not self.channel.strip():
            raise ValueError("MediaMetadata.channel não pode ser vazio")
        if self.source_label == "YouTube" and self.video_id is None:
            raise ValueError("MediaMetadata.video_id é obrigatório para YouTube")

    def canonical_url(self) -> str:
        if self.source_reference:
            return self.source_reference
        if self.video_id is None:
            raise ValueError("Mídia sem URL canônica")
        return self.video_id.canonical_url()


# Compatibilidade de import durante a migração interna.
VideoMetadata = MediaMetadata
