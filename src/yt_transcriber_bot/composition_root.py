"""Composition root — instancia e conecta todas as dependências do bot.

Este módulo é o único lugar onde concretudes tocam abstratos. Mantém
todas as escolhas de implementação centralizadas, facilitando substituir
componentes em testes e em diferentes ambientes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.audio_converter import AudioConverter
from yt_transcriber_bot.application.ports.diarization_engine import DiarizationEngine
from yt_transcriber_bot.application.ports.gpu_detector import GpuDetector
from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.application.ports.transcription_engine import (
    TranscriptionEngine,
)
from yt_transcriber_bot.application.ports.youtube_downloader import YouTubeDownloader
from yt_transcriber_bot.application.services.rename_speakers import (
    RenameSpeakersService,
)
from yt_transcriber_bot.application.services.retention_policy import RetentionPolicy
from yt_transcriber_bot.application.use_cases.transcribe_video import (
    TranscribeVideoDependencies,
    TranscribeVideoUseCase,
)
from yt_transcriber_bot.infrastructure.audio.ffmpeg_converter import (
    FfmpegAudioConverter,
)
from yt_transcriber_bot.infrastructure.diarization.composite_engine import (
    CompositeDiarizationEngine,
)
from yt_transcriber_bot.infrastructure.exporting.transcript_exporter import (
    TranscriptExportService,
)
from yt_transcriber_bot.infrastructure.exporting.video_subtitles_exporter import (
    VideoSoftSubtitleExportService,
    VideoSubtitleExportLimits,
)
from yt_transcriber_bot.infrastructure.persistence.filesystem.local_file_storage import (
    LocalFileStorage,
)
from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
    TranscriptSnapshotRepository,
)
from yt_transcriber_bot.infrastructure.persistence.sqlalchemy.job_repository import (
    SqlAlchemyJobRepository,
)
from yt_transcriber_bot.infrastructure.rendering.markdown_renderer import (
    MarkdownTranscriptRenderer,
)
from yt_transcriber_bot.infrastructure.youtube.yt_dlp_downloader import (
    YtDlpDownloader,
)
from yt_transcriber_bot.infrastructure.youtube.yt_dlp_real_factory import (
    real_subtitle_fetcher,
    real_ydl_factory,
)

logger = logging.getLogger(__name__)


@dataclass
class Composition:
    settings: AppSettings
    repository: JobRepository
    file_storage: LocalFileStorage
    snapshots: TranscriptSnapshotRepository
    use_case: TranscribeVideoUseCase
    rename_service: RenameSpeakersService
    export_service: TranscriptExportService
    video_subtitle_export_service: VideoSoftSubtitleExportService
    retention_policy: RetentionPolicy


def _make_gpu_detector() -> GpuDetector:
    """Tenta criar o detector real (TorchGpuDetector); cai para um stub se torch
    não estiver instalado (modo de teste sem ML).
    """
    try:
        from yt_transcriber_bot.infrastructure.gpu.torch_gpu_detector import (
            TorchGpuDetector,
        )

        return TorchGpuDetector()
    except ImportError as exc:
        logger.warning("torch indisponível, usando detector stub (CPU only): %s", exc)
        return _StubGpuDetector()


class _StubGpuDetector(GpuDetector):
    """Detector que sempre devolve perfil de CPU."""

    def detect(self) -> object:  # pragma: no cover - usado só em ambientes sem torch
        from yt_transcriber_bot.application.ports.gpu_detector import HardwareProfile

        return HardwareProfile(
            cuda_available=False,
            cuda_device_count=0,
            gpu_name=None,
            vram_gb=0.0,
            compute_capability=None,
        )


def _make_transcription_engine() -> TranscriptionEngine:
    """Engine real do WhisperX. Falha cedo se as dependências de ML faltarem."""
    from yt_transcriber_bot.infrastructure.transcription.whisperx_engine import (
        WhisperXTranscriptionEngine,
    )
    from yt_transcriber_bot.infrastructure.transcription.whisperx_real_backend import (
        RealWhisperXBackend,
    )

    return WhisperXTranscriptionEngine(RealWhisperXBackend())


def _make_diarization_engine() -> DiarizationEngine:
    """Engine composto: WhisperX (primário) → pyannote (fallback)."""
    from yt_transcriber_bot.infrastructure.diarization.pyannote_diarization import (
        PyannoteDiarizationEngine,
    )
    from yt_transcriber_bot.infrastructure.diarization.pyannote_real_backend import (
        RealPyannoteBackend,
    )
    from yt_transcriber_bot.infrastructure.diarization.whisperx_diarization import (
        WhisperXDiarizationEngine,
    )
    from yt_transcriber_bot.infrastructure.diarization.whisperx_real_diar_backend import (
        RealWhisperXDiarBackend,
    )

    primary = WhisperXDiarizationEngine(RealWhisperXDiarBackend())
    fallback = PyannoteDiarizationEngine(RealPyannoteBackend())
    return CompositeDiarizationEngine([primary, fallback])


def build(settings: AppSettings) -> Composition:
    """Wiring completo da aplicação."""
    # Diretórios
    settings.base_dir.mkdir(parents=True, exist_ok=True)
    settings.downloads_dir().mkdir(parents=True, exist_ok=True)
    settings.processed_dir().mkdir(parents=True, exist_ok=True)
    settings.transcripts_dir().mkdir(parents=True, exist_ok=True)
    settings.logs_dir().mkdir(parents=True, exist_ok=True)
    settings.video_exports_dir().mkdir(parents=True, exist_ok=True)
    segments_dir = settings.base_dir / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    settings.models_dir.mkdir(parents=True, exist_ok=True)
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)

    # Persistência
    repository = SqlAlchemyJobRepository.from_url(f"sqlite:///{settings.db_path}")
    file_storage = LocalFileStorage()
    snapshots = TranscriptSnapshotRepository(segments_dir)

    # Adapters de I/O
    downloader: YouTubeDownloader = YtDlpDownloader(
        ydl_factory=real_ydl_factory,
        subtitle_fetcher=real_subtitle_fetcher,
        cookies_file=settings.youtube_cookies_file or None,
        cookies_browser=settings.youtube_cookies_browser or None,
    )
    converter: AudioConverter = FfmpegAudioConverter()

    # Engines de ML (importação preguiçosa)
    gpu_detector = _make_gpu_detector()
    transcription_engine = _make_transcription_engine()
    diarization_engine = _make_diarization_engine()

    # Renderer
    renderer = MarkdownTranscriptRenderer()

    # Use case
    use_case = TranscribeVideoUseCase(
        TranscribeVideoDependencies(
            downloader=downloader,
            converter=converter,
            gpu_detector=gpu_detector,
            transcription_engine=transcription_engine,
            diarization_engine=diarization_engine,
            renderer=renderer,
            settings=settings,
            repository=repository,
            snapshot_repository=snapshots,
        )
    )

    # Serviços auxiliares
    rename_service = RenameSpeakersService(snapshots, renderer)
    export_service = TranscriptExportService(snapshots)
    video_subtitle_export_service = VideoSoftSubtitleExportService(
        snapshots=snapshots,
        transcript_exporter=export_service,
        ydl_factory=real_ydl_factory,
        output_dir=settings.video_exports_dir(),
        cookies_file=settings.youtube_cookies_file or None,
        cookies_browser=settings.youtube_cookies_browser or None,
        limits=VideoSubtitleExportLimits(
            max_duration_seconds=settings.max_video_subtitles_duration_min * 60,
            max_size_bytes=settings.max_video_subtitles_size_mb * 1024 * 1024,
        ),
    )
    retention_policy = RetentionPolicy(
        repository=repository,
        max_volatile_jobs=settings.retention_count,
    )

    return Composition(
        settings=settings,
        repository=repository,
        file_storage=file_storage,
        snapshots=snapshots,
        use_case=use_case,
        rename_service=rename_service,
        export_service=export_service,
        video_subtitle_export_service=video_subtitle_export_service,
        retention_policy=retention_policy,
    )
