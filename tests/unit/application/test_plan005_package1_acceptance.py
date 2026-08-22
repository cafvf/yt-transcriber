from __future__ import annotations

import asyncio
import json
import threading
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from tests.unit.application.conftest import (
    FakeAudioConverter,
    FakeDiarizationEngine,
    FakeGpuDetector,
    FakeJobRepository,
    FakeTranscriptionEngine,
    FakeYouTubeDownloader,
)
from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.job_request_context import JobRequestContext
from yt_transcriber_bot.application.ports.incoming_media import IncomingMedia, IncomingMediaKind
from yt_transcriber_bot.application.services.volatile_source_cleanup import (
    VolatileSourceCleanupService,
)
from yt_transcriber_bot.application.use_cases.transcribe_video import (
    TranscribeVideoDependencies,
    TranscribeVideoUseCase,
)
from yt_transcriber_bot.application.workflows.admission import (
    QueueAdmissionState,
    YoutubeAdmission,
    admit_youtube_submission,
)
from yt_transcriber_bot.application.workflows.execution import ExecutionLifecycleService
from yt_transcriber_bot.application.workflows.history import CompletedHistoryWorkflow
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.entities.media_metadata import MediaMetadata
from yt_transcriber_bot.domain.value_objects.media_source import MediaSource
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.logging.execution_audit import ExecutionAuditLogger
from yt_transcriber_bot.infrastructure.persistence.filesystem.canonical_markdown_writer import (
    FilesystemCanonicalMarkdownWriter,
)
from yt_transcriber_bot.infrastructure.persistence.filesystem.owned_artifact_cleanup import (
    FilesystemOwnedArtifactCleanup,
)
from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
    TranscriptSnapshotRepository,
)
from yt_transcriber_bot.infrastructure.rendering.markdown_renderer import (
    MarkdownTranscriptRenderer,
)
from yt_transcriber_bot.infrastructure.telegram.bot_adapter import JobPayload, TelegramBotAdapter
from yt_transcriber_bot.infrastructure.telegram.retry import TelegramSendError
from yt_transcriber_bot.infrastructure.youtube.yt_dlp_downloader import YtDlpDownloader


class _Client:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_message(
        self, _chat_id: int, text: str, reply_markup: object | None = None
    ) -> int:
        _ = reply_markup
        self.sent.append(text)
        return len(self.sent)

    async def edit_message(self, *_args: object) -> None:
        return None

    async def send_document(self, *_args: object, **_kwargs: object) -> None:
        return None

    async def send_audio(self, *_args: object, **_kwargs: object) -> None:
        return None

    async def send_video(self, *_args: object, **_kwargs: object) -> None:
        return None


class _NoopUseCase:
    def execute(self, *_args: object, **_kwargs: object) -> object:
        raise AssertionError("worker execution is outside this acceptance test")


class _MediaDownloader:
    async def download(self, _media: IncomingMedia, dest_dir: Path) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / "incoming.wav"
        path.write_bytes(b"audio")
        return path


class _BlockingDurationInspector:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()

    def duration_seconds(self, _path: Path) -> int:
        self.started.set()
        self.release.wait(timeout=2.0)
        return 60


class _RecordingOperationalWorkflow:
    def __init__(self) -> None:
        self.errors: list[dict[str, object]] = []

    def record_error(self, **kwargs: object) -> None:
        self.errors.append(dict(kwargs))


def _make_use_case(
    settings: AppSettings,
    fake_repo: FakeJobRepository,
    fake_downloader: FakeYouTubeDownloader,
    fake_converter: FakeAudioConverter,
    fake_gpu_cpu: FakeGpuDetector,
    fake_transcription: FakeTranscriptionEngine,
    fake_diarization: FakeDiarizationEngine,
) -> TranscribeVideoUseCase:
    return TranscribeVideoUseCase(
        TranscribeVideoDependencies(
            downloader=fake_downloader,
            converter=fake_converter,
            gpu_detector=fake_gpu_cpu,
            transcription_engine=fake_transcription,
            diarization_engine=fake_diarization,
            renderer=MarkdownTranscriptRenderer(),
            markdown_writer=FilesystemCanonicalMarkdownWriter(),
            settings=settings,
            repository=fake_repo,
            snapshot_repository=TranscriptSnapshotRepository(settings.base_dir / "segments"),
        )
    )


def _completed_job(*, md_path: Path, user_id: int = 42) -> Job:
    job = Job.new(VideoId("dQw4w9WgXcQ"), user_id)
    for status in (
        JobStatus.ACQUIRING,
        JobStatus.CONVERTING,
        JobStatus.TRANSCRIBING,
        JobStatus.DIARIZING,
        JobStatus.RENDERING,
        JobStatus.DELIVERING,
        JobStatus.COMPLETED,
    ):
        job.transition_to(status)
    job.md_path = str(md_path)
    return job


def test_p05_001_and_p05_005_unknown_youtube_duration_stops_before_expensive_work(
    settings: AppSettings,
    fake_repo: FakeJobRepository,
    fake_downloader: FakeYouTubeDownloader,
    fake_converter: FakeAudioConverter,
    fake_gpu_cpu: FakeGpuDetector,
    fake_transcription: FakeTranscriptionEngine,
    fake_diarization: FakeDiarizationEngine,
) -> None:
    video_id = VideoId("dQw4w9WgXcQ")
    fake_downloader.metadata = MediaMetadata(
        video_id=video_id,
        title="Duração desconhecida",
        channel="Canal",
        duration=None,
        upload_date=date(2026, 8, 17),
        original_language=None,
    )
    use_case = _make_use_case(
        settings,
        fake_repo,
        fake_downloader,
        fake_converter,
        fake_gpu_cpu,
        fake_transcription,
        fake_diarization,
    )

    result = use_case.execute(Job.new(video_id, 42))

    assert result.job.status is JobStatus.FAILED
    assert "duração" in (result.failure_reason or "").lower()
    assert fake_converter.convert_calls == []
    assert fake_transcription.calls == []
    assert fake_diarization.calls == []


def test_p05_001_ytdlp_common_network_wait_has_finite_socket_timeout() -> None:
    downloader = YtDlpDownloader(
        ydl_factory=lambda _params: None,  # type: ignore[arg-type]
        subtitle_fetcher=lambda _url, _ext: "",
        socket_timeout_s=12.5,
    )

    params = downloader._common_params()

    assert params["socket_timeout"] == pytest.approx(12.5)
    with pytest.raises(ValueError, match="socket_timeout_s"):
        YtDlpDownloader(
            ydl_factory=lambda _params: None,  # type: ignore[arg-type]
            subtitle_fetcher=lambda _url, _ext: "",
            socket_timeout_s=0,
        )


def test_p05_002_audit_keeps_operational_shape_and_omits_private_payload(
    settings: AppSettings, tmp_path: Path
) -> None:
    audit = ExecutionAuditLogger(tmp_path / "execution_audit.jsonl", settings=settings)

    audit.record(
        "job_execution",
        operation="transcribe",
        job_id="opaque-job-123",
        stage="transcribe",
        outcome="failed",
        transcript="private transcript body",
        token="do-not-store-this",
    )

    row = json.loads(audit.path.read_text(encoding="utf-8").splitlines()[-1])
    assert row["event"] == "job_execution"
    assert row["operation"] == "transcribe"
    assert row["job_id"] == "opaque-job-123"
    assert row["stage"] == "transcribe"
    assert row["outcome"] == "failed"
    assert row["transcript"] == "[OMITTED]"
    assert row["token"] == "[REDACTED]"
    assert "private transcript body" not in audit.path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_p05_003_slow_duration_probe_does_not_block_independent_event_loop_tick(
    settings: AppSettings,
    fake_repo: FakeJobRepository,
) -> None:
    inspector = _BlockingDurationInspector()
    adapter = TelegramBotAdapter(
        settings=settings,
        client=_Client(),
        use_case=_NoopUseCase(),  # type: ignore[arg-type]
        repository=fake_repo,
        media_downloader=_MediaDownloader(),  # type: ignore[arg-type]
        duration_inspector=inspector,  # type: ignore[arg-type]
    )
    media = IncomingMedia(
        file_id="file-doc",
        file_name="meeting.wav",
        mime_type="audio/wav",
        size_bytes=1024,
        duration_seconds=None,
        kind=IncomingMediaKind.DOCUMENT,
    )
    safety_release = threading.Timer(1.5, inspector.release.set)
    safety_release.start()
    task = asyncio.create_task(adapter.handle_incoming_media(chat_id=10, user_id=42, media=media))
    try:
        while not inspector.started.is_set():
            await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert not inspector.release.is_set()
    finally:
        inspector.release.set()
        await asyncio.wait_for(task, timeout=1.0)
        safety_release.cancel()


def test_p05_004_terminal_history_does_not_block_fresh_submission(
    fake_repo: FakeJobRepository,
    tmp_path: Path,
) -> None:
    markdown = tmp_path / "history.md"
    markdown.write_text("# history\n", encoding="utf-8")
    historical = _completed_job(md_path=markdown)
    fake_repo.save(historical)

    result = admit_youtube_submission(
        repository=fake_repo,
        queue_state=QueueAdmissionState(items=(), capacity=5),
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        user_id=42,
        delivery_chat_id=10,
        requested_language=None,
        reprocess=False,
        processing_fingerprint="package1",
    )

    assert isinstance(result, YoutubeAdmission)
    assert result.job.job_id != historical.job_id
    assert historical.status is JobStatus.COMPLETED


@pytest.mark.asyncio
async def test_p05_006_nonprimary_delivery_failure_is_recorded_without_mutating_completed_job(
    settings: AppSettings,
    fake_repo: FakeJobRepository,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    markdown = tmp_path / "completed.md"
    markdown.write_text("# completed\n", encoding="utf-8")
    job = _completed_job(md_path=markdown)
    fake_repo.save(job)
    operational = _RecordingOperationalWorkflow()

    async def fail_send(_operation: object, **_kwargs: object) -> Any:
        raise TelegramSendError("transport unavailable")

    monkeypatch.setattr(
        "yt_transcriber_bot.infrastructure.telegram.bot_adapter.send_with_retry",
        fail_send,
    )
    adapter = TelegramBotAdapter(
        settings=settings,
        client=_Client(),
        use_case=_NoopUseCase(),  # type: ignore[arg-type]
        repository=fake_repo,
        history_workflow=CompletedHistoryWorkflow(
            fake_repo,
            markdown_available=Path.is_file,
        ),
        operational_workflow=operational,  # type: ignore[arg-type]
    )

    await adapter.handle_command_last(chat_id=10, user_id=42, text="/last 1")

    assert job.status is JobStatus.COMPLETED
    assert len(operational.errors) == 1
    record = operational.errors[0]
    assert record["operation"] == "history_delivery"
    assert record["stage"] == "delivery"
    assert "transcrição histórica" in str(record["message"])


@pytest.mark.asyncio
async def test_p05_007_pending_telegram_cancellation_cleans_staging_and_locator(
    settings: AppSettings,
    fake_repo: FakeJobRepository,
) -> None:
    job = Job.new(
        None,
        42,
        media_source=MediaSource.telegram_audio("file-private"),
        source_title="Meeting",
        source_duration_seconds=60,
    )
    fake_repo.save(job)
    staging_dir = settings.downloads_dir() / job.job_id
    staging_dir.mkdir(parents=True, exist_ok=True)
    source = staging_dir / "source.ogg"
    source.write_bytes(b"private")
    fake_repo.save_request_context(
        JobRequestContext(
            job_id=job.job_id,
            delivery_chat_id=10,
            source_locator=str(source),
        )
    )
    cleanup = VolatileSourceCleanupService(
        fake_repo,
        FilesystemOwnedArtifactCleanup((settings.downloads_dir(),)),
    )
    adapter = TelegramBotAdapter(
        settings=settings,
        client=_Client(),
        use_case=_NoopUseCase(),  # type: ignore[arg-type]
        repository=fake_repo,
        execution_lifecycle=ExecutionLifecycleService(fake_repo),
        source_cleanup_service=cleanup,
    )
    payload = JobPayload(
        job_id=job.job_id,
        chat_id=10,
        user_id=42,
        url=str(source),
        video_id=None,
        progress_message_id=1,
        media_source=job.media_source,
        source_title=job.source_title,
        source_duration_seconds=job.source_duration_seconds,
    )
    await adapter._queue.enqueue(payload, item_id=job.job_id)

    await adapter.handle_command_clearqueue(chat_id=10, user_id=42)

    assert job.status is JobStatus.CANCELLED
    assert not source.exists()
    context = fake_repo.get_request_context(job.job_id)
    assert context is not None
    assert context.source_locator is None
    current, pending = adapter._queue.snapshot()
    assert current is None
    assert pending == ()
