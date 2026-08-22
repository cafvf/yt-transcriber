from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.audio_converter import AudioConverter
from yt_transcriber_bot.application.ports.canonical_transcript import CanonicalTranscriptStore
from yt_transcriber_bot.application.ports.diarization_engine import DiarizationEngine
from yt_transcriber_bot.application.ports.gpu_detector import GpuDetector, HardwareProfile
from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.application.ports.staging_cleanup import PrivateStagingCleanup
from yt_transcriber_bot.application.ports.transcription_engine import TranscriptionEngine
from yt_transcriber_bot.application.ports.youtube_downloader import YouTubeDownloader
from yt_transcriber_bot.application.services.cache_maintenance import CacheMaintenanceService
from yt_transcriber_bot.application.services.healthcheck import HealthCheckService
from yt_transcriber_bot.application.services.last_error import LastErrorService
from yt_transcriber_bot.application.services.rename_speakers import RenameSpeakersService
from yt_transcriber_bot.application.services.retention_policy import RetentionPolicy
from yt_transcriber_bot.application.services.sanitization import sanitize_text
from yt_transcriber_bot.application.services.search_indexing import SearchIndexingService
from yt_transcriber_bot.application.services.startup_recovery import StartupRecoveryService
from yt_transcriber_bot.application.services.transcript_summary import TranscriptSummaryService
from yt_transcriber_bot.application.services.volatile_source_cleanup import (
    VolatileSourceCleanupService,
)
from yt_transcriber_bot.application.use_cases.transcribe_video import (
    TranscribeVideoDependencies,
    TranscribeVideoUseCase,
)
from yt_transcriber_bot.application.workflows.derivatives import TranscriptDerivativeWorkflow
from yt_transcriber_bot.application.workflows.execution import ExecutionLifecycleService
from yt_transcriber_bot.application.workflows.history import CompletedHistoryWorkflow
from yt_transcriber_bot.application.workflows.operations import OperationalWorkflow
from yt_transcriber_bot.application.workflows.summary import SummaryWorkflow
from yt_transcriber_bot.application.workflows.text_search import TextSearchWorkflow
from yt_transcriber_bot.configuration.credentials import ProviderCredentials
from yt_transcriber_bot.configuration.external_services import TextGenerationEndpointPolicy
from yt_transcriber_bot.infrastructure.audio.ffmpeg_converter import FfmpegAudioConverter
from yt_transcriber_bot.infrastructure.diarization.composite_engine import (
    CompositeDiarizationEngine,
)
from yt_transcriber_bot.infrastructure.exporting.plain_text_exporter import (
    PlainTextTranscriptExportService,
)
from yt_transcriber_bot.infrastructure.exporting.transcript_derivatives_adapter import (
    TranscriptDerivativesAdapter,
)
from yt_transcriber_bot.infrastructure.exporting.transcript_exporter import TranscriptExportService
from yt_transcriber_bot.infrastructure.exporting.video_subtitles_exporter import (
    VideoSoftSubtitleExportService,
    VideoSubtitleExportLimits,
)
from yt_transcriber_bot.infrastructure.logging.execution_audit import ExecutionAuditLogger
from yt_transcriber_bot.infrastructure.logging.runtime_logging import (
    configure_runtime_logging as _configure_runtime_logging,
)
from yt_transcriber_bot.infrastructure.operational.bounded_log_reader import BoundedTextLogReader
from yt_transcriber_bot.infrastructure.operational.health_environment_probe import (
    LocalHealthEnvironmentProbe,
)
from yt_transcriber_bot.infrastructure.operational.health_probes import (
    find_executable,
    local_disk_usage,
    module_available,
    probe_openai_compatible_models,
)
from yt_transcriber_bot.infrastructure.persistence.filesystem.canonical_markdown_writer import (
    FilesystemCanonicalMarkdownWriter,
)
from yt_transcriber_bot.infrastructure.persistence.filesystem.operational_error_store import (
    JsonlOperationalErrorStore,
)
from yt_transcriber_bot.infrastructure.persistence.filesystem.owned_artifact_cleanup import (
    FilesystemOwnedArtifactCleanup,
)
from yt_transcriber_bot.infrastructure.persistence.filesystem.private_staging_cleanup import (
    FilesystemPrivateStagingCleanup,
)
from yt_transcriber_bot.infrastructure.persistence.filesystem.reconstructible_cache import (
    FilesystemReconstructibleCache,
)
from yt_transcriber_bot.infrastructure.persistence.filesystem.summary_artifact_store import (
    FilesystemSummaryArtifactStore,
)
from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
    TranscriptSnapshotRepository,
)
from yt_transcriber_bot.infrastructure.persistence.sqlalchemy.job_repository import (
    SqlAlchemyJobRepository,
)
from yt_transcriber_bot.infrastructure.persistence.sqlalchemy.text_search_repository import (
    SqlAlchemyTextSearchRepository,
)
from yt_transcriber_bot.infrastructure.persistence.sqlite_health import SqliteHealthProbe
from yt_transcriber_bot.infrastructure.rendering.markdown_renderer import MarkdownTranscriptRenderer
from yt_transcriber_bot.infrastructure.summarization.openai_compatible_client import (
    OpenAICompatibleChatClient,
)
from yt_transcriber_bot.infrastructure.summarization.tokenizer import make_text_tokenizer
from yt_transcriber_bot.infrastructure.telegram.audience import (
    DeniedAudienceFilter,
    TelegramAudiencePolicy,
)
from yt_transcriber_bot.infrastructure.telegram.bot_adapter import TelegramBotAdapter
from yt_transcriber_bot.infrastructure.telegram.ffprobe_duration_inspector import (
    FfprobeAudioDurationInspector,
)
from yt_transcriber_bot.infrastructure.telegram.history import HistoryPresentation
from yt_transcriber_bot.infrastructure.telegram.ptb_bot_client import PTBBotClient
from yt_transcriber_bot.infrastructure.youtube.yt_dlp_downloader import YtDlpDownloader
from yt_transcriber_bot.infrastructure.youtube.yt_dlp_real_factory import (
    real_subtitle_fetcher,
    real_ydl_factory,
)

logger = logging.getLogger(__name__)
_DIARIZATION_MODEL_NAME = "pyannote/speaker-diarization-community-1"


def configure_runtime_logging(settings: AppSettings) -> None:
    _configure_runtime_logging(
        settings.logs_dir(),
        max_bytes=settings.operational_log_max_bytes,
        backup_count=settings.operational_log_backup_count,
    )


def _bound_error_sanitizer(settings: AppSettings) -> Callable[[str], str]:
    def sanitize(detail: str) -> str:
        return sanitize_text(detail, settings)

    return sanitize


def _readable_file(path: Path) -> bool:
    try:
        return path.is_file() and os.access(path, os.R_OK)
    except OSError:
        return False


@dataclass
class Composition:
    settings: AppSettings
    repository: JobRepository
    snapshots: TranscriptSnapshotRepository
    use_case: TranscribeVideoUseCase
    audit_logger: ExecutionAuditLogger
    history_presentation: HistoryPresentation
    history_workflow: CompletedHistoryWorkflow
    execution_lifecycle: ExecutionLifecycleService
    startup_recovery_service: StartupRecoveryService
    source_cleanup_service: VolatileSourceCleanupService
    staging_cleanup: PrivateStagingCleanup
    text_search_workflow: TextSearchWorkflow
    derivative_workflow: TranscriptDerivativeWorkflow
    summary_workflow: SummaryWorkflow | None
    operational_workflow: OperationalWorkflow


@dataclass(frozen=True)
class RuntimeComposition:
    core: Composition
    application: Any
    adapter: TelegramBotAdapter
    audience: TelegramAudiencePolicy
    denied_audience_filter: Any


def _make_gpu_detector() -> GpuDetector:
    try:
        from yt_transcriber_bot.infrastructure.gpu.torch_gpu_detector import TorchGpuDetector

        return TorchGpuDetector()
    except ImportError as exc:
        logger.warning("torch indisponível, usando detector stub (CPU only): %s", exc)
        return _StubGpuDetector()


class _StubGpuDetector(GpuDetector):
    def detect(self) -> HardwareProfile:
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
    error_sanitizer: Callable[[str], str],
) -> TranscriptSummaryService | None:
    if settings.summary_backend == "disabled":
        return None
    endpoint = TextGenerationEndpointPolicy(
        base_url=settings.summary_base_url,
        model=settings.summary_model,
        explicitly_configured="summary_base_url" in settings.model_fields_set,
    )
    endpoint.require_transcript_disclosure_allowed()
    client = OpenAICompatibleChatClient(
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
    tokenizer = make_text_tokenizer(
        backend=settings.summary_tokenizer_backend,
        model=settings.summary_tokenizer_model or settings.summary_model,
        chars_per_token=settings.summary_chars_per_token,
        trust_remote_code=settings.summary_tokenizer_trust_remote_code,
    )
    return TranscriptSummaryService(
        snapshots=snapshots,
        chat_client=client,
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


def build(settings: AppSettings, *, credentials: ProviderCredentials) -> Composition:
    for path in (
        settings.base_dir,
        settings.downloads_dir(),
        settings.processed_dir(),
        settings.transcripts_dir(),
        settings.logs_dir(),
        settings.video_exports_dir(),
        settings.summaries_dir(),
        settings.base_dir / "segments",
        settings.models_dir,
        settings.db_path.parent,
    ):
        path.mkdir(parents=True, exist_ok=True)

    error_sanitizer = _bound_error_sanitizer(settings)

    url = f"sqlite:///{settings.db_path}"
    repository = SqlAlchemyJobRepository.from_url(url)
    search_repository = SqlAlchemyTextSearchRepository.from_url(url)
    snapshots = TranscriptSnapshotRepository(settings.base_dir / "segments")
    summary_store = FilesystemSummaryArtifactStore(settings.summaries_dir())

    downloader: YouTubeDownloader = YtDlpDownloader(
        ydl_factory=real_ydl_factory,
        subtitle_fetcher=real_subtitle_fetcher,
        cookies_file=credentials.youtube_cookies_file or None,
        cookies_browser=credentials.youtube_cookies_browser or None,
        error_sanitizer=error_sanitizer,
    )
    converter: AudioConverter = FfmpegAudioConverter()
    renderer = MarkdownTranscriptRenderer()
    markdown_writer = FilesystemCanonicalMarkdownWriter()
    use_case = TranscribeVideoUseCase(
        TranscribeVideoDependencies(
            downloader=downloader,
            converter=converter,
            gpu_detector=_make_gpu_detector(),
            transcription_engine=_make_transcription_engine(),
            diarization_engine=_make_diarization_engine(credentials.hf_token),
            renderer=renderer,
            markdown_writer=markdown_writer,
            settings=settings,
            repository=repository,
            snapshot_repository=snapshots,
        )
    )

    rename_service = RenameSpeakersService(snapshots, renderer, markdown_writer)
    export_service = TranscriptExportService(snapshots)
    plain_text_export_service = PlainTextTranscriptExportService(snapshots)
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

    indexer = SearchIndexingService(
        repository=repository,
        canonical_transcripts=snapshots,
        index=search_repository,
        summaries=summary_store,
    )
    history = CompletedHistoryWorkflow(repository, markdown_available=_readable_file)
    history_presentation = HistoryPresentation(rename_service)
    text_search_workflow = TextSearchWorkflow(
        history=history, query=search_repository, indexer=indexer
    )
    derivative_workflow = TranscriptDerivativeWorkflow(
        repository=repository,
        history=history,
        rename_service=rename_service,
        gateway=TranscriptDerivativesAdapter(
            text=plain_text_export_service,
            transcript=export_service,
            video=video_subtitle_export_service,
        ),
        indexer=indexer,
        transcripts_dir=settings.transcripts_dir(),
    )

    summary_service = _make_summary_service(settings, credentials, snapshots, error_sanitizer)
    summary_workflow = (
        SummaryWorkflow(
            history=history,
            summary_policy=summary_service,
            store=summary_store,
            indexer=indexer,
        )
        if summary_service is not None
        else None
    )

    error_store = JsonlOperationalErrorStore(
        settings.logs_dir() / "operational_errors.jsonl",
        max_records=settings.operational_error_max_records,
        max_bytes=settings.audit_log_max_bytes,
    )
    healthcheck_service = HealthCheckService(
        settings=settings,
        environment_probe=LocalHealthEnvironmentProbe(
            settings=settings,
            models_probe=probe_openai_compatible_models,
            executable_finder=find_executable,
            module_checker=module_available,
            disk_usage=local_disk_usage,
            sqlite_probe=SqliteHealthProbe(),
            operational_errors=error_store,
        ),
    )
    lasterror_service = LastErrorService(
        repository=repository,
        settings=settings,
        error_store=error_store,
        log_reader=BoundedTextLogReader(),
        artifact_available=_readable_file,
    )
    artifact_cleanup = FilesystemOwnedArtifactCleanup(
        (settings.downloads_dir(), settings.processed_dir(), settings.logs_dir())
    )
    retention_policy = RetentionPolicy(
        repository=repository,
        artifact_cleanup=artifact_cleanup,
        max_volatile_jobs=settings.retention_count,
    )
    operational_workflow = OperationalWorkflow(
        healthcheck=healthcheck_service,
        last_error=lasterror_service,
        cache=CacheMaintenanceService(
            FilesystemReconstructibleCache(
                (settings.models_dir,),
                protected_paths=(
                    settings.downloads_dir(),
                    settings.processed_dir(),
                    settings.transcripts_dir(),
                    settings.logs_dir(),
                    settings.summaries_dir(),
                    settings.video_exports_dir(),
                    settings.base_dir / "segments",
                    settings.db_path,
                ),
            )
        ),
        retention=retention_policy,
    )
    audit_logger = ExecutionAuditLogger(
        settings.logs_dir() / "execution_audit.jsonl",
        settings=settings,
        max_bytes=settings.audit_log_max_bytes,
        backup_count=settings.audit_log_backup_count,
    )
    execution_lifecycle = ExecutionLifecycleService(
        repository,
        completed_observer=indexer.refresh,
    )
    startup_recovery_service = StartupRecoveryService(repository)
    source_cleanup_service = VolatileSourceCleanupService(repository, artifact_cleanup)
    staging_cleanup = FilesystemPrivateStagingCleanup(settings.downloads_dir())

    return Composition(
        settings=settings,
        repository=repository,
        snapshots=snapshots,
        use_case=use_case,
        audit_logger=audit_logger,
        history_presentation=history_presentation,
        history_workflow=history,
        execution_lifecycle=execution_lifecycle,
        startup_recovery_service=startup_recovery_service,
        source_cleanup_service=source_cleanup_service,
        staging_cleanup=staging_cleanup,
        text_search_workflow=text_search_workflow,
        derivative_workflow=derivative_workflow,
        summary_workflow=summary_workflow,
        operational_workflow=operational_workflow,
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
        audit_logger=core.audit_logger,
        media_downloader=client,
        duration_inspector=FfprobeAudioDurationInspector(),
        history_presentation=core.history_presentation,
        history_workflow=core.history_workflow,
        execution_lifecycle=core.execution_lifecycle,
        startup_recovery_service=core.startup_recovery_service,
        source_cleanup_service=core.source_cleanup_service,
        staging_cleanup=core.staging_cleanup,
        text_search_workflow=core.text_search_workflow,
        derivative_workflow=core.derivative_workflow,
        summary_workflow=core.summary_workflow,
        operational_workflow=core.operational_workflow,
    )
    audience = TelegramAudiencePolicy(settings.telegram_allowed_user_id)
    return RuntimeComposition(
        core=core,
        application=application,
        adapter=adapter,
        audience=audience,
        denied_audience_filter=DeniedAudienceFilter(audience),
    )


def build_runtime(settings: AppSettings, *, credentials: ProviderCredentials) -> RuntimeComposition:
    return _make_telegram_runtime(settings, credentials, build(settings, credentials=credentials))
