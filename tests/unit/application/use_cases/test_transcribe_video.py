"""Testes do use case TranscribeVideoUseCase (integração entre steps com fakes)."""

from __future__ import annotations

import logging
import threading
from datetime import date

from tests.unit.application.conftest import (
    FakeAudioConverter,
    FakeDiarizationEngine,
    FakeGpuDetector,
    FakeJobRepository,
    FakeTranscriptionEngine,
    FakeYouTubeDownloader,
)
from yt_transcriber_bot.application.cancellation import OperationCanceledError
from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.pipeline.context import PipelineContext
from yt_transcriber_bot.application.ports.diarization_engine import (
    DiarizationError,
    DiarizationProvenance,
    DiarizationResult,
    DiarizedSpeakerSegment,
)
from yt_transcriber_bot.application.ports.gpu_detector import HardwareProfile
from yt_transcriber_bot.application.ports.transcription_engine import (
    OutOfMemoryError,
    TranscribedSegment,
    TranscriptionRequest,
    TranscriptionResult,
)
from yt_transcriber_bot.application.ports.youtube_downloader import (
    FetchedSubtitle,
    NoAudioStreamError,
    SubtitleTrack,
    VideoUnavailableError,
)
from yt_transcriber_bot.application.services.retention_policy import RetentionPolicy
from yt_transcriber_bot.application.use_cases.transcribe_video import (
    TranscribeVideoDependencies,
    TranscribeVideoResult,
    TranscribeVideoUseCase,
)
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.media_source import MediaSource
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.persistence.filesystem.owned_artifact_cleanup import (
    FilesystemOwnedArtifactCleanup,
)
from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
    TranscriptSnapshotRepository,
)
from yt_transcriber_bot.infrastructure.rendering.markdown_renderer import (
    MarkdownTranscriptRenderer,
)
from yt_transcriber_bot.infrastructure.text.normalization import (
    text_has_unresolved_corruption,
)


def _job() -> Job:
    return Job.new(
        video_id=VideoId(value="dQw4w9WgXcQ"),
        user_id=42,
    )


def _make_uc(
    settings: AppSettings,
    *,
    fake_repo: FakeJobRepository,
    fake_downloader: FakeYouTubeDownloader,
    fake_converter: FakeAudioConverter,
    fake_gpu_cpu: FakeGpuDetector,
    fake_transcription: FakeTranscriptionEngine,
    fake_diarization: FakeDiarizationEngine,
    snapshot_repository: TranscriptSnapshotRepository | None = None,
    diarization_model_name: str = "pyannote/speaker-diarization-community-1",
) -> TranscribeVideoUseCase:
    if snapshot_repository is None:
        snapshot_repository = TranscriptSnapshotRepository(settings.base_dir / "segments")

    deps = TranscribeVideoDependencies(
        downloader=fake_downloader,
        converter=fake_converter,
        gpu_detector=fake_gpu_cpu,
        transcription_engine=fake_transcription,
        diarization_engine=fake_diarization,
        renderer=MarkdownTranscriptRenderer(),
        settings=settings,
        repository=fake_repo,
        snapshot_repository=snapshot_repository,
        diarization_model_name=diarization_model_name,
    )
    return TranscribeVideoUseCase(deps=deps)


# ======================================================================
# Happy path
# ======================================================================


class TestHappyPath:
    def test_full_pipeline_completes(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        result = uc.execute(_job())
        assert result.job.status == JobStatus.DELIVERING
        assert result.md_path is not None
        assert result.md_path.exists()
        assert result.audio_path is not None
        assert result.audio_path.exists()
        # MD deve conter pelo menos o cabeçalho
        md = result.md_path.read_text(encoding="utf-8")
        assert md.startswith("# Transcrição —")

    def test_md_filename_uses_title_slug(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        fake_downloader.metadata = VideoMetadata(
            video_id=VideoId(value="dQw4w9WgXcQ"),
            title="Meu Vídeo Especial",
            channel="Canal X",
            duration=Duration.from_seconds(60),
            upload_date=date(2024, 1, 1),
            original_language=Language(code="pt"),
        )
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        result = uc.execute(_job())
        assert result.md_path is not None
        assert "meu-video-especial" in result.md_path.name

    def test_telegram_jobs_with_same_title_keep_distinct_audio_for_retention(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        source_one = settings.base_dir / "downloads" / "telegram-one.m4a"
        source_two = settings.base_dir / "downloads" / "telegram-two.m4a"
        source_one.parent.mkdir(parents=True, exist_ok=True)
        source_one.write_bytes(b"first")
        source_two.write_bytes(b"second")
        first = Job.new(
            None,
            42,
            media_source=MediaSource.telegram_audio("file-one"),
            source_title="Mesmo título",
            source_duration_seconds=1,
        )
        second = Job.new(
            None,
            42,
            media_source=MediaSource.telegram_audio("file-two"),
            source_title="Mesmo título",
            source_duration_seconds=1,
        )

        first_result = uc.execute(first, source_locator=str(source_one))
        second_result = uc.execute(second, source_locator=str(source_two))

        assert first_result.audio_path is not None
        assert second_result.audio_path is not None
        assert first_result.audio_path != second_result.audio_path
        assert first_result.audio_path.exists()
        assert second_result.audio_path.exists()
        first_audio_path = first_result.audio_path
        second_audio_path = second_result.audio_path

        first.transition_to(JobStatus.COMPLETED)
        second.transition_to(JobStatus.COMPLETED)
        RetentionPolicy(
            fake_repo,
            artifact_cleanup=FilesystemOwnedArtifactCleanup(
                (
                    settings.downloads_dir(),
                    settings.processed_dir(),
                    settings.logs_dir(),
                )
            ),
            max_volatile_jobs=1,
        ).apply()

        assert first.audio_path is None
        assert second.audio_path is not None
        assert not first_audio_path.exists()
        assert second_audio_path.exists()

    def test_progress_callback_called_per_step(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        events: list[tuple[str, str]] = []
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        uc.execute(_job(), progress_step=lambda s, m: events.append((s, m)))
        # Sem legendas YT: cada etapa publica início e conclusão, em ordem.
        assert [step for step, _ in events] == [
            "fetch_metadata",
            "fetch_metadata",
            "try_youtube_subtitles",
            "try_youtube_subtitles",
            "download_audio",
            "download_audio",
            "convert_audio",
            "convert_audio",
            "select_runtime",
            "select_runtime",
            "transcribe",
            "transcribe",
            "diarize",
            "diarize",
            "render_md",
            "render_md",
        ]

    def test_runner_for_has_the_same_youtube_step_order_as_execute(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        job = _job()
        execute_events: list[tuple[str, str]] = []
        uc.execute(job, progress_step=lambda step, message: execute_events.append((step, message)))

        runner_job = _job()
        runner_events: list[tuple[str, str]] = []
        context = PipelineContext(job=runner_job)
        returned_context = uc.runner_for(runner_job).run(
            context,
            progress=lambda step, message: runner_events.append((step, message)),
        )

        assert returned_context is context
        assert context.job is runner_job
        assert [step for step, _ in runner_events] == [step for step, _ in execute_events]

    def test_collision_appends_suffix(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        r1 = uc.execute(_job())
        r2 = uc.execute(_job())
        assert r1.md_path is not None
        assert r2.md_path is not None
        assert r1.md_path != r2.md_path
        assert r2.md_path.name.endswith("-2.md")

    def test_pipeline_persists_snapshot_for_rename(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        snapshots = TranscriptSnapshotRepository(settings.base_dir / "segments")
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
            snapshot_repository=snapshots,
            diarization_model_name="custom/diarization-v1",
        )
        result = uc.execute(_job())
        assert result.md_path is not None
        assert result.job.canonical_transcript_ref is not None
        snap = snapshots.load(result.job.canonical_transcript_ref)
        assert snap is not None
        assert snap.metadata.title == fake_downloader.metadata.title
        assert snap.transcript.speaker_labels()
        assert snap.context.diarization_model == "custom/diarization-v1"
        assert snap.processing_provenance.diarization_model == "custom/diarization-v1"

    def test_pipeline_persists_actual_diarization_backend_model_and_fallback(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        snapshots = TranscriptSnapshotRepository(settings.base_dir / "segments")
        fake_diarization.result = DiarizationResult(
            speaker_segments=(
                DiarizedSpeakerSegment(
                    start_seconds=0.0,
                    end_seconds=10.0,
                    speaker_label="SPEAKER_00",
                ),
            ),
            total_speakers=1,
            provenance=DiarizationProvenance(
                backend="pyannote",
                model="actual/diarization-model",
                fallback_used=True,
            ),
        )
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
            snapshot_repository=snapshots,
            diarization_model_name="compatibility/model-must-not-win",
        )

        result = uc.execute(_job())

        assert result.job.canonical_transcript_ref is not None
        snapshot = snapshots.load(result.job.canonical_transcript_ref)
        assert snapshot is not None
        assert snapshot.processing_provenance.diarization_backend == "pyannote"
        assert snapshot.processing_provenance.diarization_model == ("actual/diarization-model")
        assert snapshot.processing_provenance.diarization_fallback_used is True
        assert snapshot.context.diarization_model == "actual/diarization-model"
        assert any(
            "Fallback de diarização utilizado" in diagnostic for diagnostic in result.diagnostics
        )


# ======================================================================
# Rejeições semânticas
# ======================================================================


class TestRejections:
    def test_pipeline_rejection_sanitizes_persisted_and_returned_reason(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        raw_secret = "sk-secret12345"
        raw_payload = "private transcript text"
        fake_downloader.raise_on_audio = NoAudioStreamError(
            f'authorization: Bearer {raw_secret}; transcript: "{raw_payload}"'
        )
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        job = _job()

        result = uc.execute(job)

        stored = fake_repo.get_by_id(job.job_id)
        assert stored is not None
        assert stored.status is JobStatus.FAILED
        assert stored.error_message == result.failure_reason
        assert raw_secret not in (result.failure_reason or "")
        assert raw_payload not in (result.failure_reason or "")
        assert "[REDACTED]" in (result.failure_reason or "")

    def test_video_too_long_rejected(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        # max default é 180 min. Vídeo de 200 min deve ser rejeitado.
        fake_downloader.metadata = VideoMetadata(
            video_id=VideoId(value="dQw4w9WgXcQ"),
            title="Muito Longo",
            channel="X",
            duration=Duration.from_minutes(200),
            upload_date=date(2024, 1, 1),
            original_language=Language(code="pt"),
        )
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        result = uc.execute(_job())
        assert result.job.status == JobStatus.FAILED
        assert result.failure_reason is not None
        assert "limite" in result.failure_reason or "excede" in result.failure_reason

    def test_language_not_allowed(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        fake_downloader.metadata = VideoMetadata(
            video_id=VideoId(value="dQw4w9WgXcQ"),
            title="Espanhol",
            channel="X",
            duration=Duration.from_seconds(60),
            upload_date=date(2024, 1, 1),
            original_language=Language(code="es"),
        )
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        result = uc.execute(_job())
        assert result.job.status == JobStatus.FAILED
        assert "es" in (result.failure_reason or "")

    def test_und_language_passes(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        # Quando idioma original é desconhecido (None), deixa passar para o Whisper detectar
        fake_downloader.metadata = VideoMetadata(
            video_id=VideoId(value="dQw4w9WgXcQ"),
            title="Indeterminado",
            channel="X",
            duration=Duration.from_seconds(60),
            upload_date=None,
            original_language=None,
        )
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        result = uc.execute(_job())
        assert result.job.status == JobStatus.DELIVERING


# ======================================================================
# Atalho via legendas do YouTube
# ======================================================================


class TestYouTubeSubtitles:
    def test_uses_manual_subtitles_when_available(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        fake_downloader.subtitles = (
            SubtitleTrack(
                language=Language(code="pt"),
                is_auto_generated=False,
                is_translated=False,
                url="http://x/pt.vtt",
                ext="vtt",
            ),
        )
        fake_downloader.fetched_subtitle = FetchedSubtitle(
            language=Language(code="pt"),
            is_auto_generated=False,
            segments=(
                (0.0, 2.0, "Olá."),
                (2.0, 4.0, "Como vai?"),
            ),
        )
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        events: list[tuple[str, str]] = []
        result = uc.execute(
            _job(), progress_step=lambda step, message: events.append((step, message))
        )
        assert result.job.status == JobStatus.DELIVERING
        # Caminho por legendas deve pular download/conversão/transcrição/diarização.
        assert result.audio_path is None
        assert fake_converter.convert_calls == []
        assert fake_transcription.calls == []
        assert fake_diarization.calls == []
        assert [step for step, _ in events] == [
            "fetch_metadata",
            "fetch_metadata",
            "try_youtube_subtitles",
            "try_youtube_subtitles",
            "download_audio",
            "convert_audio",
            "select_runtime",
            "transcribe",
            "diarize",
            "render_md",
            "render_md",
        ]
        skipped_steps = {step for step, message in events if "Etapa pulada" in message}
        assert skipped_steps >= {
            "download_audio",
            "convert_audio",
            "select_runtime",
            "transcribe",
            "diarize",
        }
        # MD deve indicar a fonte como legenda manual do YT
        assert result.md_path is not None
        md = result.md_path.read_text(encoding="utf-8")
        assert "Legendas manuais do YouTube" in md
        assert "SPEAKER_00" in md

    def test_falls_back_to_whisperx_when_subtitle_text_stays_corrupted(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        fake_downloader.subtitles = (
            SubtitleTrack(
                language=Language(code="pt"),
                is_auto_generated=False,
                is_translated=False,
                url="http://x/pt.vtt",
                ext="vtt",
            ),
        )
        fake_downloader.fetched_subtitle = FetchedSubtitle(
            language=Language(code="pt"),
            is_auto_generated=False,
            segments=(
                (0.0, 2.0, "Ol� mundo."),
                (2.0, 4.0, "Jo�o chegou."),
            ),
        )
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        events: list[tuple[str, str]] = []
        result = uc.execute(
            _job(), progress_step=lambda step, message: events.append((step, message))
        )

        assert result.job.status == JobStatus.DELIVERING
        assert fake_transcription.calls != []
        assert fake_diarization.calls != []
        assert [step for step, _ in events] == [
            "fetch_metadata",
            "fetch_metadata",
            "try_youtube_subtitles",
            "try_youtube_subtitles",
            "download_audio",
            "download_audio",
            "convert_audio",
            "convert_audio",
            "select_runtime",
            "select_runtime",
            "transcribe",
            "transcribe",
            "diarize",
            "diarize",
            "render_md",
            "render_md",
        ]
        assert not any("Usando legendas do YouTube" in d for d in result.diagnostics)
        assert any("Legenda do YouTube rejeitada por integridade" in d for d in result.diagnostics)

    def test_repairs_subtitle_mojibake_before_markdown_and_snapshot_persistence(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        snapshots = TranscriptSnapshotRepository(settings.base_dir / "segments")
        fake_downloader.subtitles = (
            SubtitleTrack(
                language=Language(code="pt"),
                is_auto_generated=False,
                is_translated=False,
                url="http://x/pt.vtt",
                ext="vtt",
            ),
        )
        fake_downloader.fetched_subtitle = FetchedSubtitle(
            language=Language(code="pt"),
            is_auto_generated=False,
            segments=(
                (0.0, 2.0, "VocÃª nÃ£o tem aÃ§Ã£o."),
                (2.0, 4.0, "JoÃ£o chegou."),
            ),
        )
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
            snapshot_repository=snapshots,
        )

        result = uc.execute(_job())

        assert result.job.status == JobStatus.DELIVERING
        assert result.md_path is not None
        md = result.md_path.read_text(encoding="utf-8")
        assert "Você não tem ação." in md
        assert "João chegou." in md
        assert not text_has_unresolved_corruption(md)

        assert result.job.canonical_transcript_ref is not None
        snap = snapshots.load(result.job.canonical_transcript_ref)
        assert snap is not None
        assert snap.transcript.segments[0].text == "Você não tem ação."
        assert snap.transcript.segments[1].text == "João chegou."


class _BlockingTranscriptionEngine(FakeTranscriptionEngine):
    started: threading.Event

    def __init__(self, started: threading.Event) -> None:
        super().__init__()
        self.started = started

    def transcribe(
        self,
        request: TranscriptionRequest,
    ) -> TranscriptionResult:
        cancel_event = request.cancel_event
        self.started.set()
        while True:
            if cancel_event is not None and cancel_event.is_set():
                raise OperationCanceledError("cancelado durante transcrição")
            if cancel_event is not None:
                cancel_event.wait(0.01)


class TestCancellation:
    def test_active_transcription_cancellation_marks_job_cancelled(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        started = threading.Event()
        cancel_event = threading.Event()
        engine = _BlockingTranscriptionEngine(started=started)
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=engine,
            fake_diarization=fake_diarization,
        )
        outcome: dict[str, object] = {}

        def run_use_case() -> None:
            outcome["result"] = uc.execute(_job(), cancel_event=cancel_event)

        worker = threading.Thread(target=run_use_case)
        worker.start()
        assert started.wait(timeout=1.0)
        cancel_event.set()
        worker.join(timeout=2.0)
        assert not worker.is_alive()

        result = outcome["result"]
        assert isinstance(result, TranscribeVideoResult)
        assert result.canceled is True
        assert result.job.status == JobStatus.CANCELLED
        assert result.audio_path is not None

    def test_translated_subtitles_are_ignored(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        fake_downloader.subtitles = (
            SubtitleTrack(
                language=Language(code="pt"),
                is_auto_generated=False,
                is_translated=True,  # tradução, não legenda original
                url="http://x/pt.vtt",
                ext="vtt",
            ),
        )
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        uc.execute(_job())
        # Caiu no caminho do WhisperX
        assert len(fake_transcription.calls) == 1

    def test_subtitles_in_other_language_ignored(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        # Vídeo é PT, mas só tem legenda em EN: deve ignorar e ir pra Whisper.
        fake_downloader.subtitles = (
            SubtitleTrack(
                language=Language(code="en"),
                is_auto_generated=False,
                is_translated=False,
                url="http://x/en.vtt",
                ext="vtt",
            ),
        )
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        uc.execute(_job())
        assert len(fake_transcription.calls) == 1

    def test_disabled_setting_skips_subtitles(
        self,
        tmp_path: object,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        fake_downloader.subtitles = (
            SubtitleTrack(
                language=Language(code="pt"),
                is_auto_generated=False,
                is_translated=False,
                url="http://x/pt.vtt",
                ext="vtt",
            ),
        )
        fake_downloader.fetched_subtitle = FetchedSubtitle(
            language=Language(code="pt"),
            is_auto_generated=False,
            segments=((0.0, 2.0, "Olá."),),
        )
        # Settings com prefer_youtube_subtitles=False
        from pathlib import Path as _Path

        s = AppSettings(
            telegram_bot_token="x",
            telegram_allowed_user_id=42,
            hf_token="hf_x",
            whisper_model="small",
            device="cpu",
            compute_type="int8",
            prefer_youtube_subtitles=False,
            base_dir=_Path(str(tmp_path)) / "data",
            models_dir=_Path(str(tmp_path)) / "models",
            db_path=_Path(str(tmp_path)) / "data" / "jobs.db",
        )
        uc = _make_uc(
            s,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        uc.execute(_job())
        assert len(fake_transcription.calls) == 1

    def test_zero_duration_subtitle_segment_does_not_surface_unknown_speaker(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        fake_downloader.subtitles = (
            SubtitleTrack(
                language=Language(code="pt"),
                is_auto_generated=True,
                is_translated=False,
                url="http://x/pt-auto.vtt",
                ext="vtt",
            ),
        )
        fake_downloader.fetched_subtitle = FetchedSubtitle(
            language=Language(code="pt"),
            is_auto_generated=True,
            segments=(
                (0.0, 0.0, "Fantasma"),
                (0.0, 3.0, "Olá mundo"),
            ),
        )
        fake_diarization.result = DiarizationResult(
            speaker_segments=(
                DiarizedSpeakerSegment(
                    start_seconds=0.0,
                    end_seconds=3.0,
                    speaker_label="SPEAKER_00",
                ),
            ),
            total_speakers=1,
        )
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        result = uc.execute(_job())
        assert result.job.status == JobStatus.DELIVERING
        assert result.md_path is not None
        md = result.md_path.read_text(encoding="utf-8")
        assert "UNKNOWN" not in md
        assert "00:00:00 (0.0%)" not in md


# ======================================================================
# Recuperação de OOM (Strategy: cair para modelo menor + CPU)
# ======================================================================


class TestOomRetry:
    def test_oom_falls_back_to_smaller_model(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        fake_transcription.raise_on_call = OutOfMemoryError("CUDA OOM")
        # No segundo call (após retry) devolve resultado normal.
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        result = uc.execute(_job())
        assert result.job.status == JobStatus.DELIVERING
        assert len(fake_transcription.calls) == 2
        # Segundo call deve usar perfil menor e CPU.
        first_profile = fake_transcription.calls[0]["profile"]
        second_profile = fake_transcription.calls[1]["profile"]
        from yt_transcriber_bot.application.ports.transcription_engine import (
            ProcessingTarget,
            TranscriptionProcessingProfile,
        )

        assert isinstance(first_profile, TranscriptionProcessingProfile)
        assert isinstance(second_profile, TranscriptionProcessingProfile)
        assert second_profile.model_id != first_profile.model_id
        assert second_profile.target is ProcessingTarget.CPU


# ======================================================================
# Diarização e falhas
# ======================================================================


class TestDiarizationOutcomes:
    def test_diarization_failure_marks_job_failed(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        fake_diarization.raise_on_call = DiarizationError("hf token invalido")
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        result = uc.execute(_job())
        assert result.job.status == JobStatus.FAILED
        assert "hf token invalido" in (result.failure_reason or "")

    def test_segments_assigned_to_speakers(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        fake_transcription.result = TranscriptionResult(
            segments=(
                TranscribedSegment(start_seconds=0.0, end_seconds=2.0, text="Olá."),
                TranscribedSegment(start_seconds=2.5, end_seconds=4.5, text="Tudo bem."),
            ),
            detected_language=Language(code="pt"),
            language_confidence=0.9,
        )
        fake_diarization.result = DiarizationResult(
            speaker_segments=(
                DiarizedSpeakerSegment(
                    start_seconds=0.0,
                    end_seconds=2.4,
                    speaker_label="SPEAKER_00",
                ),
                DiarizedSpeakerSegment(
                    start_seconds=2.4,
                    end_seconds=5.0,
                    speaker_label="SPEAKER_01",
                ),
            ),
            total_speakers=2,
        )
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        result = uc.execute(_job())
        assert result.md_path is not None
        md = result.md_path.read_text(encoding="utf-8")
        assert "SPEAKER_00" in md
        assert "SPEAKER_01" in md


# ======================================================================
# Falhas de YouTube
# ======================================================================


class TestYouTubeFailures:
    def test_no_audio_stream_stops_before_conversion_and_asr(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        fake_downloader.raise_on_audio = NoAudioStreamError("somente vídeo")
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )

        events: list[tuple[str, str]] = []
        result = uc.execute(
            _job(), progress_step=lambda step, message: events.append((step, message))
        )

        assert result.job.status == JobStatus.FAILED
        assert "sem fluxo de áudio" in (result.failure_reason or "")
        assert [step for step, _ in events] == [
            "fetch_metadata",
            "fetch_metadata",
            "try_youtube_subtitles",
            "try_youtube_subtitles",
            "download_audio",
        ]
        assert fake_converter.convert_calls == []
        assert fake_transcription.calls == []
        assert fake_diarization.calls == []

    def test_video_unavailable_marks_failed(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        fake_downloader.raise_on_metadata = VideoUnavailableError("vídeo privado")
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        result = uc.execute(_job())
        assert result.job.status == JobStatus.FAILED
        assert "privado" in (result.failure_reason or "")


# ======================================================================
# Speaker renames
# ======================================================================


class TestRenames:
    def test_renames_applied_in_md(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        job = _job()
        job.apply_rename("SPEAKER_00", "Maria")
        result = uc.execute(job)
        assert result.md_path is not None
        md = result.md_path.read_text(encoding="utf-8")
        assert "Maria" in md


# ======================================================================
# Persistência via repo
# ======================================================================


class TestRepositoryPersistence:
    def test_rendered_job_persisted_as_delivering(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        job = _job()
        uc.execute(job)
        stored = fake_repo.get_by_id(job.job_id)
        assert stored is not None
        assert stored.status == JobStatus.DELIVERING
        assert stored.md_path is not None

    def test_failed_job_persisted(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        fake_downloader.raise_on_metadata = VideoUnavailableError("rip")
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        job = _job()
        uc.execute(job)
        stored = fake_repo.get_by_id(job.job_id)
        assert stored is not None
        assert stored.status == JobStatus.FAILED
        assert stored.error_message is not None

    def test_unexpected_failure_persists_and_returns_sanitized_reason(
        self,
        caplog,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        raw_secret = "sk-secret12345"
        raw_payload = "private transcript text"
        fake_converter.raise_on_convert = RuntimeError(
            f'ffmpeg failed authorization: Bearer {raw_secret} prompt: "{raw_payload}"'
        )
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        job = _job()

        caplog.set_level(
            logging.ERROR,
            logger="yt_transcriber_bot.application.use_cases.transcribe_video",
        )
        result = uc.execute(job)

        stored = fake_repo.get_by_id(job.job_id)
        assert stored is not None
        assert stored.status == JobStatus.FAILED
        assert stored.error_message == result.failure_reason
        assert stored.error_message is not None
        assert "RuntimeError" in stored.error_message
        assert "[REDACTED]" in stored.error_message
        assert raw_secret not in stored.error_message
        assert raw_payload not in stored.error_message
        assert result.failure_reason is not None
        assert raw_secret not in result.failure_reason
        assert raw_payload not in result.failure_reason
        assert "Pipeline falhou" in caplog.text
        assert "RuntimeError" in caplog.text
        assert "[REDACTED]" in caplog.text
        assert raw_secret not in caplog.text
        assert raw_payload not in caplog.text


# ======================================================================
# Smoke: GPU compatível usa CUDA
# ======================================================================


class TestRuntimeSelection:
    def test_auto_gpu_used_when_compatible(
        self,
        tmp_path: object,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        # GPU CC 7.5 (Turing - compatível) com 8GB de VRAM, modelo small
        gpu = FakeGpuDetector(
            profile=HardwareProfile(
                has_cuda=True,
                cuda_compute_capability=(7, 5),
                vram_total_gb=8.0,
                gpu_name="Quadro T2000",
            )
        )
        from pathlib import Path as _Path

        s = AppSettings(
            telegram_bot_token="x",
            telegram_allowed_user_id=42,
            hf_token="hf_x",
            whisper_model="small",
            device="auto",
            compute_type="auto",
            base_dir=_Path(str(tmp_path)) / "data",
            models_dir=_Path(str(tmp_path)) / "models",
            db_path=_Path(str(tmp_path)) / "data" / "jobs.db",
        )
        uc = _make_uc(
            s,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=gpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        result = uc.execute(_job())
        assert result.job.status == JobStatus.DELIVERING
        # Engine deve receber perfil de execução GPU.
        from yt_transcriber_bot.application.ports.transcription_engine import (
            ProcessingTarget,
            TranscriptionProcessingProfile,
        )

        profile = fake_transcription.calls[0]["profile"]
        assert isinstance(profile, TranscriptionProcessingProfile)
        assert profile.target is ProcessingTarget.GPU


class TestAutoSubtitleQualityGate:
    def test_rejects_repetitive_auto_subtitles_and_falls_back_to_whisperx(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        fake_downloader.subtitles = (
            SubtitleTrack(
                language=Language(code="pt"),
                is_auto_generated=True,
                is_translated=False,
                url="http://x/pt-auto.vtt",
                ext="vtt",
            ),
        )
        repeated = (
            "Spec Driven Development ajuda a organizar o contexto "
            "Spec Driven Development ajuda a organizar o contexto "
            "Spec Driven Development ajuda a organizar o contexto "
        )
        fake_downloader.fetched_subtitle = FetchedSubtitle(
            language=Language(code="pt"),
            is_auto_generated=True,
            segments=((0.0, 20.0, repeated),),
        )
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        result = uc.execute(_job())
        assert result.job.status == JobStatus.DELIVERING
        assert len(fake_transcription.calls) == 1
        assert any("Legenda automática rejeitada" in d for d in result.diagnostics)

    def test_accepts_clean_auto_subtitles_and_skips_whisperx(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        fake_downloader.subtitles = (
            SubtitleTrack(
                language=Language(code="pt"),
                is_auto_generated=True,
                is_translated=False,
                url="http://x/pt-auto.vtt",
                ext="vtt",
            ),
        )
        fake_downloader.fetched_subtitle = FetchedSubtitle(
            language=Language(code="pt"),
            is_auto_generated=True,
            segments=(
                (0.0, 4.0, "Hoje vamos falar sobre especificação de software."),
                (4.0, 8.0, "O objetivo é preservar contexto durante a implementação."),
                (8.0, 12.0, "Depois criamos tarefas menores e verificáveis."),
                (12.0, 16.0, "Essa estrutura reduz retrabalho e melhora revisão."),
            ),
        )
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        result = uc.execute(_job())
        assert result.job.status == JobStatus.DELIVERING
        assert fake_transcription.calls == []
        assert any("Qualidade da legenda automática" in d for d in result.diagnostics)


class TestFixedProgressMilestones:
    def test_transcription_and_diarization_emit_fixed_milestones(
        self,
        settings: AppSettings,
        fake_repo: FakeJobRepository,
        fake_downloader: FakeYouTubeDownloader,
        fake_converter: FakeAudioConverter,
        fake_gpu_cpu: FakeGpuDetector,
        fake_transcription: FakeTranscriptionEngine,
        fake_diarization: FakeDiarizationEngine,
    ) -> None:
        transcribe_events: list[float] = []
        diarize_events: list[float] = []
        uc = _make_uc(
            settings,
            fake_repo=fake_repo,
            fake_downloader=fake_downloader,
            fake_converter=fake_converter,
            fake_gpu_cpu=fake_gpu_cpu,
            fake_transcription=fake_transcription,
            fake_diarization=fake_diarization,
        )
        uc.execute(
            _job(),
            progress_transcribe=lambda p, _m: transcribe_events.append(p),
            progress_diarize=lambda p, _m: diarize_events.append(p),
        )
        # O fake de transcrição não emite progresso interno; o teste garante
        # pelo menos os marcos emitidos pelo step de diarização.
        assert {0.10, 0.75, 0.90}.issubset({round(x, 2) for x in diarize_events})
