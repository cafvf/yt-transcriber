"""Porta ``YouTubeDownloader`` — abstrai download de áudio e legendas do YouTube."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import VideoId

# ----- Erros do adaptador -----


class YouTubeError(Exception):
    """Erro genérico no acesso ao YouTube."""


class VideoUnavailableError(YouTubeError):
    """Vídeo não pode ser acessado (privado, removido, geo-bloqueado)."""


class MembersOnlyError(YouTubeError):
    """Vídeo restrito a membros; cookies necessários ou inválidos."""


class AgeRestrictedError(YouTubeError):
    """Vídeo com restrição de idade; cookies necessários."""


class NoAudioStreamError(YouTubeError):
    """Vídeo não possui faixa de áudio adequada."""


# ----- DTOs -----


@dataclass(frozen=True)
class DownloadedAudio:
    """Resultado do download de áudio."""

    audio_path: Path
    container: str  # ex.: "m4a", "webm", "opus"
    used_alternate_track: bool  # True se o vídeo tinha auto-dub e a original foi escolhida
    metadata: VideoMetadata


@dataclass(frozen=True)
class SubtitleTrack:
    """Pista de legenda disponível em um vídeo."""

    language: Language
    is_auto_generated: bool
    is_translated: bool
    url: str | None  # URL para o arquivo VTT/SRT (nem sempre presente em getMetadata)
    ext: str  # vtt|srt


@dataclass(frozen=True)
class FetchedSubtitle:
    """Conteúdo de legenda baixado e parseado em segmentos."""

    language: Language
    is_auto_generated: bool
    segments: tuple[tuple[float, float, str], ...]  # (start_s, end_s, text)


# ----- Porta -----


class YouTubeDownloader(ABC):
    """Operações sobre vídeos do YouTube."""

    @abstractmethod
    def fetch_metadata(self, video_id: VideoId) -> VideoMetadata: ...

    @abstractmethod
    def list_subtitles(self, video_id: VideoId) -> tuple[SubtitleTrack, ...]: ...

    @abstractmethod
    def fetch_subtitle(self, video_id: VideoId, track: SubtitleTrack) -> FetchedSubtitle: ...

    @abstractmethod
    def download_audio(self, video_id: VideoId, dest_dir: Path) -> DownloadedAudio: ...
