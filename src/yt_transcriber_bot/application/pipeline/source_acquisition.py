"""Seleção da aquisição de mídia antes do sufixo comum do pipeline."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.pipeline.runner import PipelineStep
from yt_transcriber_bot.application.pipeline.steps import (
    DownloadAudioStep,
    FetchMetadataStep,
    TryYouTubeSubtitlesStep,
    UseTelegramAudioStep,
)
from yt_transcriber_bot.application.ports.youtube_downloader import YouTubeDownloader
from yt_transcriber_bot.domain.value_objects.media_source import MediaSourceType


class SourceAcquisitionStrategy(Protocol):
    """Monta o prefixo do pipeline específico da origem de mídia."""

    def steps(self) -> tuple[PipelineStep, ...]: ...


class YouTubeSourceAcquisition:
    """Prefixo de aquisição do fluxo YouTube já existente."""

    def __init__(self, downloader: YouTubeDownloader, settings: AppSettings) -> None:
        self._downloader = downloader
        self._settings = settings

    def steps(self) -> tuple[PipelineStep, ...]:
        return (
            FetchMetadataStep(self._downloader, self._settings),
            TryYouTubeSubtitlesStep(self._downloader, self._settings),
            DownloadAudioStep(self._downloader, self._settings.downloads_dir()),
        )


class TelegramAudioSourceAcquisition:
    def steps(self) -> tuple[PipelineStep, ...]:
        return (UseTelegramAudioStep(),)


class SourceAcquisitionResolver:
    """Resolve uma estratégia uma vez a partir do tipo de origem persistido."""

    def __init__(self, downloader: YouTubeDownloader, settings: AppSettings) -> None:
        self._strategies: dict[MediaSourceType, Callable[[], SourceAcquisitionStrategy]] = {
            MediaSourceType.YOUTUBE: lambda: YouTubeSourceAcquisition(downloader, settings),
            MediaSourceType.TELEGRAM_AUDIO: TelegramAudioSourceAcquisition,
        }

    def resolve(self, source_type: MediaSourceType) -> SourceAcquisitionStrategy:
        try:
            return self._strategies[source_type]()
        except KeyError as exc:
            raise ValueError(f"Origem de mídia não suportada: {source_type.value}") from exc
