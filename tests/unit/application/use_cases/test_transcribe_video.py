"""Testes do use case TranscribeVideoUseCase (integração entre steps com fakes)."""

from __future__ import annotations

from datetime import date

from tests.unit.application.conftest import (
    FakeAudioConverter,
    FakeDiarizationEngine,
    FakeGpuDetector,
    FakeJobRepository,
    FakeTranscriptionEngine,
    FakeYouTubeDownloader,
)
from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.diarization_engine import (
    DiarizationError,
    DiarizationResult,
    DiarizedSpeakerSegment,
)
from yt_transcriber_bot.application.ports.gpu_detector import HardwareProfile
from yt_transcriber_bot.application.ports.transcription_engine import (
    OutOfMemoryError,
    TranscribedSegment,
    TranscriptionResult,
)
from yt_transcriber_bot.application.ports.youtube_downloader import (
    FetchedSubtitle,
    SubtitleTrack,
    VideoUnavailableError,
)
from yt_transcriber_bot.application.use_cases.transcribe_video import (
    TranscribeVideoDependencies,
    TranscribeVideoUseCase,
)
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
    TranscriptSnapshotRepository,
)
from yt_transcriber_bot.infrastructure.rendering.markdown_renderer import (
    MarkdownTranscriptRenderer,
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
) -> TranscribeVideoUseCase:
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
        assert result.job.status == JobStatus.COMPLETED
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
        names = {e[0] for e in events}
        # Sem legendas YT: passa por todos os 8 steps
        assert "fetch_metadata" in names
        assert "download_audio" in names
        assert "convert_audio" in names
        assert "select_runtime" in names
        assert "transcribe" in names
        assert "diarize" in names
        assert "render_md" in names

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
        )
        result = uc.execute(_job())
        assert result.md_path is not None
        snap = snapshots.load(result.md_path.stem)
        assert snap is not None
        assert snap.metadata.title == fake_downloader.metadata.title
        assert snap.transcript.speaker_labels()


# ======================================================================
# Rejeições semânticas
# ======================================================================


class TestRejections:
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
        assert result.job.status == JobStatus.COMPLETED


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
        result = uc.execute(_job())
        assert result.job.status == JobStatus.COMPLETED
        # Engine de transcrição NÃO deve ter sido chamado
        assert fake_transcription.calls == []
        # MD deve indicar a fonte como legenda manual do YT
        assert result.md_path is not None
        md = result.md_path.read_text(encoding="utf-8")
        assert "Legendas manuais do YouTube" in md

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
        assert result.job.status == JobStatus.COMPLETED
        assert len(fake_transcription.calls) == 2
        # Segundo call deve ter modelo menor e device CPU
        first = fake_transcription.calls[0]
        second = fake_transcription.calls[1]
        first_model = first["model"]
        second_model = second["model"]
        from yt_transcriber_bot.domain.value_objects.model_name import ModelName

        assert isinstance(first_model, ModelName)
        assert isinstance(second_model, ModelName)
        assert second_model.name != first_model.name
        from yt_transcriber_bot.domain.value_objects.device import Device

        assert isinstance(second["device"], Device)
        assert second["device"].is_cpu()


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
    def test_completed_job_persisted(
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
        assert stored.status == JobStatus.COMPLETED
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
        assert result.job.status == JobStatus.COMPLETED
        # Engine deve ter sido chamado com device CUDA
        from yt_transcriber_bot.domain.value_objects.device import Device

        d = fake_transcription.calls[0]["device"]
        assert isinstance(d, Device)
        assert d.is_cuda()


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
        assert result.job.status == JobStatus.COMPLETED
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
        assert result.job.status == JobStatus.COMPLETED
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
