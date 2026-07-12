"""Identidade durável e independente de transporte de uma mídia de entrada."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class MediaSourceType(StrEnum):
    """Tipos de origem previstos pelo domínio.

    A enumeração descreve identidade, não aquisição. YouTube e mídia privada
    Telegram já usam estratégias de aquisição separadas no pipeline comum.
    """

    YOUTUBE = "youtube"
    TELEGRAM_AUDIO = "telegram_audio"


@dataclass(frozen=True, slots=True)
class MediaSource:
    """Referência canônica de uma mídia, sem payload de transporte ou chat."""

    source_type: MediaSourceType
    canonical_reference: str

    def __post_init__(self) -> None:
        if not self.canonical_reference.strip():
            raise ValueError("canonical_reference não pode ser vazio")

    @classmethod
    def youtube(cls, video_id: VideoId) -> MediaSource:
        """Cria a identidade canônica para o fluxo YouTube existente."""
        return cls(
            source_type=MediaSourceType.YOUTUBE,
            canonical_reference=video_id.canonical_url(),
        )

    @classmethod
    def telegram_audio(cls, file_id: str) -> MediaSource:
        return cls(
            source_type=MediaSourceType.TELEGRAM_AUDIO, canonical_reference=f"telegram:{file_id}"
        )
