from __future__ import annotations

import threading
from datetime import date
from pathlib import Path

import pytest

from yt_transcriber_bot.application.cancellation import OperationCanceledError
from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.pipeline.context import PipelineContext
from yt_transcriber_bot.application.pipeline.steps import (
    RenderMarkdownStep,
    TryYouTubeSubtitlesStep,
)
from yt_transcriber_bot.application.ports.canonical_markdown import CanonicalMarkdownWriter
from yt_transcriber_bot.application.ports.canonical_transcript import (
    CanonicalTranscriptRecord,
    CanonicalTranscriptStore,
)
from yt_transcriber_bot.application.ports.transcript_renderer import (
    TranscriptRenderer,
    TranscriptRenderRequest,
)
from yt_transcriber_bot.application.ports.youtube_downloader import (
    DownloadedAudio,
    FetchedSubtitle,
    SubtitleTrack,
    YouTubeDownloader,
)
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.entities.media_metadata import MediaMetadata
from yt_transcriber_bot.domain.entities.transcript import Transcript, TranscriptSegment
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class CancelingSubtitleDownloader(YouTubeDownloader):
    def fetch_metadata(self, video_id: VideoId) -> MediaMetadata:
        raise AssertionError(video_id)

    def list_subtitles(self, video_id: VideoId) -> tuple[SubtitleTrack, ...]:
        _ = video_id
        return (
            SubtitleTrack(
                language=Language("pt"),
                is_auto_generated=False,
                is_translated=False,
                url="https://example.invalid/pt.vtt",
                ext="vtt",
            ),
        )

    def fetch_subtitle(
        self,
        video_id: VideoId,
        track: SubtitleTrack,
        *,
        cancel_event: threading.Event | None = None,
    ) -> FetchedSubtitle:
        _ = (video_id, track, cancel_event)
        raise OperationCanceledError("cancelled during subtitle fetch")

    def download_audio(
        self,
        video_id: VideoId,
        dest_dir: Path,
        *,
        cancel_event: threading.Event | None = None,
    ) -> DownloadedAudio:
        raise AssertionError((video_id, dest_dir, cancel_event))


class StaticRenderer(TranscriptRenderer):
    def render_transcript(self, request: TranscriptRenderRequest) -> str:
        _ = request
        return "# rendered\n"


class FailingWriter(CanonicalMarkdownWriter):
    def write(self, path: Path, content: str) -> None:
        raise AssertionError((path, content))

    def write_new(self, preferred_path: Path, content: str, *, collision_key: str) -> Path:
        _ = (preferred_path, content, collision_key)
        raise RuntimeError("primary markdown failure")


class RollbackFailingStore(CanonicalTranscriptStore):
    def __init__(self) -> None:
        self.persisted: list[str] = []
        self.deleted: list[str] = []

    def persist(self, reference: str, record: CanonicalTranscriptRecord) -> None:
        _ = record
        self.persisted.append(reference)

    def delete(self, reference: str) -> None:
        self.deleted.append(reference)
        raise RuntimeError("secondary rollback failure")

    def load(self, reference: str) -> CanonicalTranscriptRecord | None:
        _ = reference
        return None

    def load_metadata(self, reference: str) -> MediaMetadata | None:
        _ = reference
        return None

    def load_metadata_many(self, references: tuple[str, ...]) -> dict[str, MediaMetadata]:
        _ = references
        return {}


def _settings(tmp_path: Path) -> AppSettings:
    return AppSettings(
        _env_file=None,
        telegram_allowed_user_id=7,
        base_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
        db_path=tmp_path / "data" / "jobs.db",
    )


def _metadata(video_id: VideoId) -> MediaMetadata:
    return MediaMetadata(
        video_id=video_id,
        title="Teste",
        channel="Canal",
        duration=Duration.from_seconds(60),
        upload_date=date(2026, 8, 22),
        original_language=Language("pt"),
    )


def test_subtitle_cancellation_is_not_swallowed_as_fallback(tmp_path: Path) -> None:
    video_id = VideoId("dQw4w9WgXcQ")
    job = Job.new(video_id, 7)
    ctx = PipelineContext(job=job, requested_language=Language("pt"))
    ctx.metadata = _metadata(video_id)
    step = TryYouTubeSubtitlesStep(CancelingSubtitleDownloader(), _settings(tmp_path))

    with pytest.raises(OperationCanceledError):
        step.execute(ctx)

    assert ctx.youtube_subtitle_used is False


def test_markdown_failure_preserves_primary_exception_when_rollback_also_fails(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    video_id = VideoId("dQw4w9WgXcQ")
    job = Job.new(video_id, 7)
    for status in (
        JobStatus.ACQUIRING,
        JobStatus.CONVERTING,
        JobStatus.TRANSCRIBING,
        JobStatus.DIARIZING,
    ):
        job.transition_to(status)
    ctx = PipelineContext(job=job)
    ctx.metadata = _metadata(video_id)
    ctx.transcript = Transcript(
        segments=(TranscriptSegment(0.0, 1.0, "Olá", "SPEAKER_00"),),
        language=Language("pt"),
    )
    store = RollbackFailingStore()
    step = RenderMarkdownStep(
        StaticRenderer(),
        FailingWriter(),
        settings.transcripts_dir(),
        settings,
        snapshot_repository=store,
        processing_fingerprint="fingerprint",
    )

    with pytest.raises(RuntimeError, match="primary markdown failure"):
        step.execute(ctx)

    assert store.persisted == [job.job_id]
    assert store.deleted == [job.job_id]
    assert ctx.final_md_path is None
    assert job.canonical_transcript_ref is None
