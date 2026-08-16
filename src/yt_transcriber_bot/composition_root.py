# Single composition owner for concrete provider selection and construction.

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.audio_converter import AudioConverter
from yt_transcriber_bot.application.ports.canonical_transcript import CanonicalTranscriptStore
from yt_transcriber_bot.application.ports.diarization_engine import DiarizationEngine
from yt_transcriber_bot.application.ports.gpu_detector import GpuDetector, HardwareProfile
from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.application.ports.transcription_engine import TranscriptionEngine
from yt_transcriber_bot.application.ports.youtube_downloader import YouTubeDownloader
from yt_transcriber_bot.application.services.healthcheck import HealthCheckService
from yt_transcriber_bot.application.services.history_search import HistorySearchService
from yt_transcriber_bot.application.services.last_error import LastErrorService
from yt_transcriber_bot.application.services.rename_speakers import RenameSpeakersService
from yt_transcriber_bot.application.services.retention_policy import RetentionPolicy
from yt_transcriber_bot.application.services.sanitization import sanitize_text
from yt_transcriber_bot.application.use_cases.transcribe_video import (
    TranscribeVideoDependencies,
    TranscribeVideoUseCase,
)
from yt_transcriber_bot.configuration.credentials import ProviderCredentials
from yt_transcriber_bot.configuration.external_services import (
    TextGenerationEndpointPolicy,
)
from yt_transcriber_bot.infrastructure.audio.ffmpeg_converter import FfmpegAudioConverter
from yt_transcriber_bot.infrastructure.diarization.composite_engine import (
    CompositeDiarizationEngine,
)
from yt_transcriber_bot.infrastructure.exporting.plain_text_exporter import (
    PlainTextTranscriptExportService,
)
from yt_transcriber_bot.infrastructure.exporting.transcript_exporter import (
    TranscriptExportService,
)
from yt_transcriber_bot.infrastructure.exporting.video_subtitles_exporter import (
    VideoSoftSubtitleExportService,
    VideoSubtitleExportLimits,
)
from yt_transcriber_bot.infrastructure.logging.execution_audit import ExecutionAuditLogger
from yt_transcriber_bot.infrastructure.operational.health_probes import (
    find_executable,
    local_disk_usage,
    module_available,
    probe_openai_compatible_models,
)
from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
    TranscriptSnapshotRepository,
)
from yt_transcriber_bot.infrastructure.persistence.sqlalchemy.job_repository import (
    SqlAlchemyJobRepository,
)
from yt_transcriber_bot.infrastructure.persistence.sqlite_health import SqliteHealthProbe
from yt_transcriber_bot.infrastructure.rendering.markdown_renderer import (
    MarkdownTranscriptRenderer,
)
from yt_transcriber_bot.infrastructure.summarization.openai_compatible_client import (
    OpenAICompatibleChatClient,
)
from yt_transcriber_bot.infrastructure.summarization.transcript_summarizer import (
    TranscriptSummaryService,
    make_text_tokenizer,
)
from yt_transcriber_bot.infrastructure.telegram.audience import (
    DeniedAudienceFilter,
    TelegramAudiencePolicy,
)
from yt_transcriber_bot.infrastructure.telegram.bot_adapter import TelegramBotAdapter
from yt_transcriber_bot.infrastructure.telegram.ffprobe_duration_inspector import (
    FfprobeAudioDurationInspector,
)
from yt_transcriber_bot.infrastructure.telegram.ptb_bot_client import PTBBotClient
from yt_transcriber_bot.infrastructure.youtube.yt_dlp_downloader import YtDlpDownloader
from yt_transcriber_bot.infrastructure.youtube.yt_dlp_real_factory import (
    real_subtitle_fetcher,
    real_ydl_factory,
)

logger = logging.getLogger(__name__)

_DIARIZATION_MODEL_NAME = "pyannote/speaker-diarization-community-1"


def _bound_error_sanitizer(settings: AppSettings) -> Callable[[str], str]:
    def sanitize(detail: str) -> str:
        return sanitize_text(detail, settings)

    return sanitize


@dataclass
class Composition:
    settings: AppSettings
    repository: JobRepository
    snapshots: TranscriptSnapshotRepository
    use_case: TranscribeVideoUseCase
    rename_service: RenameSpeakersService
    export_service: TranscriptExportService
    plain_text_export_service: PlainTextTranscriptExportService
    summary_service: TranscriptSummaryService | None
    video_subtitle_export_service: VideoSoftSubtitleExportService
    healthcheck_service: HealthCheckService
    history_search_service: HistorySearchService
    lasterror_service: LastErrorService
    retention_policy: RetentionPolicy
    audit_logger: ExecutionAuditLogger


@dataclass(frozen=True)
class RuntimeComposition:
    core: Composition
    application: Any
    adapter: TelegramBotAdapter
    audience: TelegramAudiencePolicy
    denied_audience_filter: Any


def _make_gpu_detector() -> GpuDetector:
    try:
        from yt_transcriber_bot.infrastructure.gpu.torch_gpu_detector import (
            TorchGpuDetector,
        )

        return TorchGpuDetector()
    except ImportError as exc:
        logger.warning("torch indisponível, usando detector stub (CPU only): %s", exc)
        return _StubGpuDetector()


class _StubGpuDetector(GpuDetector):
    def detect(self) -> HardwareProfile:  # pragma: no cover - host fallback
        return HardwareProfile(
            has_cuda=False,
            cuda_compute_capability=None,
            vram_total_gb=0.0,
            gpu_name="",
        )


def _make_transcription_engine() -> TranscriptionEngine:
    from yt_transcriber_bot.infrastructure.transcription.whisperx_engine import (
        WhisperXTranscriptionEngine,
    )
    from yt_transcriber_bot.infrastructure.transcription.whisperx_real_backend import (
        RealWhisperXBackend,
    )

    return WhisperXTranscriptionEngine(RealWhisperXBackend())


def _make_diarization_engine(hf_token: str) -> DiarizationEngine:
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

    primary = WhisperXDiarizationEngine(
        RealWhisperXDiarBackend(model_name=_DIARIZATION_MODEL_NAME),
        hf_token=hf_token,
        model_id=_DIARIZATION_MODEL_NAME,
    )
    fallback = PyannoteDiarizationEngine(
        RealPyannoteBackend(model_name=_DIARIZATION_MODEL_NAME),
        hf_token=hf_token,
        model_id=_DIARIZATION_MODEL_NAME,
    )
    return CompositeDiarizationEngine([primary, fallback])


def _make_summary_service(
    settings: AppSettings,
    credentials: ProviderCredentials,
    snapshots: CanonicalTranscriptStore,
) -> TranscriptSummaryService | None:
    if settings.summary_backend == "disabled":
        return None

    endpoint = TextGenerationEndpointPolicy(
        base_url=settings.summary_base_url,
        model=settings.summary_model,
        explicitly_configured="summary_base_url" in settings.model_fields_set,
    )
    endpoint.require_transcript_disclosure_allowed()
    error_sanitizer = _bound_error_sanitizer(settings)

    summary_client = OpenAICompatibleChatClient(
        base_url=endpoint.base_url,
        model=endpoint.model,
        temperature=settings.summary_temperature,
        max_tokens=settings.summary_max_tokens,
        timeout_s=settings.summary_timeout_s,
        api_key=credentials.summary_api_key,
        disable_thinking=settings.summary_disable_thinking,
        validate_model=settings.summary_validate_model,
        strict_model_match=settings.summary_strict_model_match,
        error_sanitizer=error_sanitizer,
    )
    tokenizer_model = settings.summary_tokenizer_model or settings.summary_model
    tokenizer = make_text_tokenizer(
        backend=settings.summary_tokenizer_backend,
        model=tokenizer_model,
        chars_per_token=settings.summary_chars_per_token,
        trust_remote_code=settings.summary_tokenizer_trust_remote_code,
    )
    return TranscriptSummaryService(
        snapshots=snapshots,
        chat_client=summary_client,
        output_dir=settings.summaries_dir(),
        max_chars_per_chunk=settings.summary_max_chars_per_chunk,
        max_input_tokens=settings.summary_max_input_tokens,
        chars_per_token=settings.summary_chars_per_token,
        partial_max_tokens=settings.summary_partial_max_tokens,
        final_max_tokens=settings.summary_final_max_tokens,
        timeout_split_retries=settings.summary_timeout_split_retries,
        output_language=settings.summary_output_language,
        disable_thinking=settings.summary_disable_thinking,
        tokenizer_backend=settings.summary_tokenizer_backend,
        tokenizer_model=settings.summary_tokenizer_model,
        tokenizer_trust_remote_code=settings.summary_tokenizer_trust_remote_code,
        tokenizer=tokenizer,
        deduplicate_transcript=settings.summary_deduplicate_transcript,
        merge_same_speaker_gap_s=settings.summary_merge_same_speaker_gap_s,
        min_overlap_words=settings.summary_min_overlap_words,
    )


def build(
    settings: AppSettings,
    *,
    credentials: ProviderCredentials,
) -> Composition:
    settings.base_dir.mkdir(parents=True, exist_ok=True)
    settings.downloads_dir().mkdir(parents=True, exist_ok=True)
    settings.processed_dir().mkdir(parents=True, exist_ok=True)
    settings.transcripts_dir().mkdir(parents=True, exist_ok=True)
    settings.logs_dir().mkdir(parents=True, exist_ok=True)
    settings.video_exports_dir().mkdir(parents=True, exist_ok=True)
    settings.summaries_dir().mkdir(parents=True, exist_ok=True)
    segments_dir = settings.base_dir / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    settings.models_dir.mkdir(parents=True, exist_ok=True)
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)

    repository = SqlAlchemyJobRepository.from_url(f"sqlite:///{settings.db_path}")
    snapshots = TranscriptSnapshotRepository(segments_dir)

    error_sanitizer = _bound_error_sanitizer(settings)
    downloader: YouTubeDownloader = YtDlpDownloader(
        ydl_factory=real_ydl_factory,
        subtitle_fetcher=real_subtitle_fetcher,
        cookies_file=credentials.youtube_cookies_file or None,
        cookies_browser=credentials.youtube_cookies_browser or None,
        error_sanitizer=error_sanitizer,
    )
    converter: AudioConverter = FfmpegAudioConverter()

    gpu_detector = _make_gpu_detector()
    transcription_engine = _make_transcription_engine()
    diarization_engine = _make_diarization_engine(credentials.hf_token)
    renderer = MarkdownTranscriptRenderer()

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

    rename_service = RenameSpeakersService(snapshots, renderer)
    export_service = TranscriptExportService(snapshots)
    plain_text_export_service = PlainTextTranscriptExportService(snapshots)
    summary_service = _make_summary_service(settings, credentials, snapshots)

    video_subtitle_export_service = VideoSoftSubtitleExportService(
        snapshots=snapshots,
        transcript_exporter=export_service,
        ydl_factory=real_ydl_factory,
        output_dir=settings.video_exports_dir(),
        cookies_file=credentials.youtube_cookies_file or None,
        cookies_browser=credentials.youtube_cookies_browser or None,
        error_sanitizer=error_sanitizer,
        limits=VideoSubtitleExportLimits(
            max_duration_seconds=settings.max_video_subtitles_duration_min * 60,
            max_size_bytes=settings.max_video_subtitles_size_mb * 1024 * 1024,
        ),
    )
    healthcheck_service = HealthCheckService(
        settings=settings,
        models_probe=probe_openai_compatible_models,
        executable_finder=find_executable,
        module_checker=module_available,
        disk_usage=local_disk_usage,
        sqlite_probe=SqliteHealthProbe(),
    )
    history_search_service = HistorySearchService(repository)
    lasterror_service = LastErrorService(repository=repository, settings=settings)
    audit_logger = ExecutionAuditLogger(
        settings.logs_dir() / "execution_audit.jsonl",
        settings=settings,
    )
    retention_policy = RetentionPolicy(
        repository=repository,
        owned_roots=(
            settings.downloads_dir(),
            settings.processed_dir(),
            settings.logs_dir(),
        ),
        max_volatile_jobs=settings.retention_count,
    )

    return Composition(
        settings=settings,
        repository=repository,
        snapshots=snapshots,
        use_case=use_case,
        rename_service=rename_service,
        export_service=export_service,
        plain_text_export_service=plain_text_export_service,
        summary_service=summary_service,
        video_subtitle_export_service=video_subtitle_export_service,
        healthcheck_service=healthcheck_service,
        history_search_service=history_search_service,
        lasterror_service=lasterror_service,
        retention_policy=retention_policy,
        audit_logger=audit_logger,
    )


def _make_telegram_application(bot_token: str) -> Any:
    from telegram.ext import Application

    return Application.builder().token(bot_token).build()


def _make_telegram_runtime(
    settings: AppSettings,
    credentials: ProviderCredentials,
    core: Composition,
) -> RuntimeComposition:
    application = _make_telegram_application(credentials.telegram_bot_token)
    client = PTBBotClient(application.bot)
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,
        use_case=core.use_case,
        repository=core.repository,
        rename_service=core.rename_service,
        export_service=core.export_service,
        plain_text_export_service=core.plain_text_export_service,
        summary_service=core.summary_service,
        video_subtitle_export_service=core.video_subtitle_export_service,
        healthcheck_service=core.healthcheck_service,
        history_search_service=core.history_search_service,
        lasterror_service=core.lasterror_service,
        retention_policy=core.retention_policy,
        models_dir=settings.models_dir,
        audit_logger=core.audit_logger,
        media_downloader=client,
        duration_inspector=FfprobeAudioDurationInspector(),
    )
    audience = TelegramAudiencePolicy(settings.telegram_allowed_user_id)
    return RuntimeComposition(
        core=core,
        application=application,
        adapter=adapter,
        audience=audience,
        denied_audience_filter=DeniedAudienceFilter(audience),
    )


def build_runtime(
    settings: AppSettings,
    *,
    credentials: ProviderCredentials,
) -> RuntimeComposition:
    core = build(settings, credentials=credentials)
    return _make_telegram_runtime(settings, credentials, core)
