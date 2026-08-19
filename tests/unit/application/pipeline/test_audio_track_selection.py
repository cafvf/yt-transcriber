"""Gate A1: propagação da seleção de faixa no pipeline."""

from __future__ import annotations

from tests.unit.application.conftest import FakeYouTubeDownloader
from yt_transcriber_bot.application.pipeline.context import PipelineContext
from yt_transcriber_bot.application.pipeline.steps import DownloadAudioStep
from yt_transcriber_bot.domain.entities.job import Job
from yt_transcriber_bot.domain.value_objects.audio_track import AudioTrackSelection
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


def _youtube_job() -> Job:
    return Job.new(VideoId("dQw4w9WgXcQ"), user_id=42)


def test_pipeline_context_starts_with_unknown_audio_track_selection() -> None:
    ctx = PipelineContext(job=_youtube_job())

    assert ctx.audio_track_selection is AudioTrackSelection.UNKNOWN


def test_download_audio_step_preserves_original_selection(tmp_path) -> None:
    downloader = FakeYouTubeDownloader(audio_track_selection=AudioTrackSelection.ORIGINAL)
    ctx = PipelineContext(job=_youtube_job())

    DownloadAudioStep(downloader, tmp_path).execute(ctx)

    assert ctx.raw_audio_path is not None
    assert ctx.raw_audio_path.is_file()
    assert ctx.audio_track_selection is AudioTrackSelection.ORIGINAL


def test_download_audio_step_preserves_default_selection(tmp_path) -> None:
    downloader = FakeYouTubeDownloader(audio_track_selection=AudioTrackSelection.DEFAULT)
    ctx = PipelineContext(job=_youtube_job())

    DownloadAudioStep(downloader, tmp_path).execute(ctx)

    assert ctx.audio_track_selection is AudioTrackSelection.DEFAULT
