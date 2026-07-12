"""Caracterização do prefixo de aquisição YouTube do pipeline."""

from __future__ import annotations

from tests.unit.application.conftest import FakeYouTubeDownloader
from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.pipeline.source_acquisition import (
    SourceAcquisitionResolver,
)
from yt_transcriber_bot.application.pipeline.steps import (
    DownloadAudioStep,
    FetchMetadataStep,
    TryYouTubeSubtitlesStep,
)
from yt_transcriber_bot.domain.value_objects.media_source import MediaSourceType


def test_youtube_source_keeps_existing_acquisition_step_order(tmp_path) -> None:
    settings = AppSettings(data_dir=str(tmp_path))

    strategy = SourceAcquisitionResolver(FakeYouTubeDownloader(), settings).resolve(
        MediaSourceType.YOUTUBE
    )

    assert tuple(type(step) for step in strategy.steps()) == (
        FetchMetadataStep,
        TryYouTubeSubtitlesStep,
        DownloadAudioStep,
    )


def test_telegram_audio_source_uses_local_audio_prefix(tmp_path) -> None:
    settings = AppSettings(data_dir=str(tmp_path))
    resolver = SourceAcquisitionResolver(FakeYouTubeDownloader(), settings)

    strategy = resolver.resolve(MediaSourceType.TELEGRAM_AUDIO)
    assert tuple(type(step).__name__ for step in strategy.steps()) == ("UseTelegramAudioStep",)
