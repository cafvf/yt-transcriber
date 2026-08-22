"""Use case de transcrição com evidência canônica obrigatória para sucesso."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.operational_errors import (
    OperationalError,
    OperationalErrorCode,
    PipelineRejectionError,
    classify_operational_error,
    error_for_code,
)
from yt_transcriber_bot.application.pipeline.context import PipelineContext
from yt_transcriber_bot.application.pipeline.runner import (
    AuditFn,
    PipelineCanceledError,
    PipelineRunner,
    PipelineStep,
)
from yt_transcriber_bot.application.pipeline.source_acquisition import SourceAcquisitionResolver
from yt_transcriber_bot.application.pipeline.steps import (
    ConvertAudioStep,
    DiarizeStep,
    RenderMarkdownStep,
    SelectRuntimeStep,
    TranscribeStep,
    TranscriptionStepProgress,
)
from yt_transcriber_bot.application.ports.audio_converter import AudioConverter
from yt_transcriber_bot.application.ports.canonical_markdown import CanonicalMarkdownWriter
from yt_transcriber_bot.application.ports.canonical_transcript import CanonicalTranscriptStore
from yt_transcriber_bot.application.ports.diarization_engine import DiarizationEngine
from yt_transcriber_bot.application.ports.gpu_detector import GpuDetector
from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.application.ports.transcript_renderer import TranscriptRenderer
from yt_transcriber_bot.application.ports.transcription_engine import TranscriptionEngine
from yt_transcriber_bot.application.ports.youtube_downloader import YouTubeDownloader
from yt_transcriber_bot.application.services.processing_fingerprint import (
    compute_processing_fingerprint,
)
from yt_transcriber_bot.application.services.sanitization import sanitize_text
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.language import Language

logger = logging.getLogger(__name__)


@dataclass
class TranscribeVideoResult:
    job: Job
    md_path: Path | None
    audio_path: Path | None
    diagnostics: tuple[str, ...]
    language_code: str | None = None
    language_source: str | None = None
    language_confidence: float | None = None
    canceled: bool = False
    failure_reason: str | None = None
    operational_error: OperationalError | None = None


@dataclass
class TranscribeVideoDependencies:
    downloader: YouTubeDownloader
    converter: AudioConverter
    gpu_detector: GpuDetector
    transcription_engine: TranscriptionEngine
    diarization_engine: DiarizationEngine
    renderer: TranscriptRenderer
    markdown_writer: CanonicalMarkdownWriter
    settings: AppSettings
    repository: JobRepository
    snapshot_repository: CanonicalTranscriptStore | None = None
    diarization_model_name: str = "pyannote/speaker-diarization-community-1"


class TranscribeVideoUseCase:
    def __init__(self, deps: TranscribeVideoDependencies) -> None:
        self._deps = deps

    def execute(
        self,
        job: Job,
        *,
        progress_step: Callable[[str, str], None] | None = None,
        progress_transcribe: Callable[[float, str], None] | None = None,
        progress_diarize: Callable[[float, str], None] | None = None,
        audit: AuditFn | None = None,
        cancel_event: threading.Event | None = None,
        requested_language: Language | None = None,
        source_locator: str | None = None,
    ) -> TranscribeVideoResult:
        deps = self._deps
        effective_requested_language = (
            requested_language if requested_language is not None else job.requested_language
        )
        job.requested_language = effective_requested_language
        source_type = job.media_source.source_type if job.media_source else None
        job.processing_fingerprint = compute_processing_fingerprint(
            deps.settings,
            requested_language=effective_requested_language,
            source_type=source_type,
        )
        runner = PipelineRunner(
            steps=self._assemble_steps(
                job,
                progress_transcribe=progress_transcribe,
                progress_diarize=progress_diarize,
            ),
            cancel_event=cancel_event,
        )
        ctx = PipelineContext(
            job=job,
            requested_language=effective_requested_language,
            source_locator=source_locator,
        )
        deps.repository.save(job)

        try:
            runner.run(ctx, progress=progress_step, audit=audit)
        except PipelineCanceledError as exc:
            error = error_for_code(
                OperationalErrorCode.OPERATION_CANCELLED,
                technical_context={"detail": sanitize_text(str(exc), deps.settings)},
            )
            job.transition_to(JobStatus.CANCELLED, error=error.safe_message)
            deps.repository.save(job)
            return self._result(ctx, canceled=True, operational_error=error)
        except PipelineRejectionError as exc:
            error = self._classify(exc)
            return self._failed_result(ctx, error)
        except Exception as exc:
            error = self._classify(exc)
            logger.error("Pipeline falhou [%s]", error.code.value)
            return self._failed_result(ctx, error)

        if ctx.final_md_path is None or not job.canonical_transcript_ref:
            error = error_for_code(
                OperationalErrorCode.INTERNAL_INVARIANT_VIOLATION,
                safe_message="O processamento terminou sem evidência canônica válida.",
            )
            return self._failed_result(ctx, error)

        job.transition_to(JobStatus.DELIVERING)
        deps.repository.save(job)
        return self._result(ctx)

    def _classify(self, exc: BaseException) -> OperationalError:
        return classify_operational_error(
            exc,
            sanitizer=lambda text: sanitize_text(text, self._deps.settings),
        )

    def _failed_result(
        self, ctx: PipelineContext, error: OperationalError
    ) -> TranscribeVideoResult:
        ctx.job.transition_to(JobStatus.FAILED, error=error.safe_message)
        self._deps.repository.save(ctx.job)
        return self._result(
            ctx,
            failure_reason=error.safe_message,
            operational_error=error,
            canonical=False,
        )

    def _result(
        self,
        ctx: PipelineContext,
        *,
        canceled: bool = False,
        failure_reason: str | None = None,
        operational_error: OperationalError | None = None,
        canonical: bool = True,
    ) -> TranscribeVideoResult:
        return TranscribeVideoResult(
            job=ctx.job,
            md_path=ctx.final_md_path if canonical else None,
            audio_path=ctx.converted_audio_path if canonical else None,
            diagnostics=tuple(ctx.diagnostics),
            language_code=(
                ctx.transcription_language.code if ctx.transcription_language is not None else None
            ),
            language_source=ctx.language_source.value,
            language_confidence=ctx.transcription_confidence,
            canceled=canceled,
            failure_reason=failure_reason,
            operational_error=operational_error,
        )

    def runner_for(self, job: Job) -> PipelineRunner:
        return PipelineRunner(steps=self._assemble_steps(job))

    def _assemble_steps(
        self,
        job: Job,
        *,
        progress_transcribe: Callable[[float, str], None] | None = None,
        progress_diarize: Callable[[float, str], None] | None = None,
    ) -> tuple[PipelineStep, ...]:
        deps = self._deps
        source = job.media_source
        if source is None:
            raise ValueError("Job sem origem de mídia")
        source_steps = (
            SourceAcquisitionResolver(deps.downloader, deps.settings)
            .resolve(source.source_type)
            .steps()
        )
        fingerprint = job.processing_fingerprint or compute_processing_fingerprint(
            deps.settings,
            requested_language=job.requested_language,
            source_type=source.source_type,
        )
        common_suffix: tuple[PipelineStep, ...] = (
            ConvertAudioStep(
                deps.converter,
                deps.settings.processed_dir(),
                deps.settings,
            ),
            SelectRuntimeStep(deps.gpu_detector, deps.settings),
            TranscribeStep(
                deps.transcription_engine,
                deps.settings,
                progress=TranscriptionStepProgress(on_progress=progress_transcribe),
            ),
            DiarizeStep(
                deps.diarization_engine,
                deps.settings,
                progress=TranscriptionStepProgress(on_progress=progress_diarize),
                diarization_model_name=deps.diarization_model_name,
            ),
            RenderMarkdownStep(
                deps.renderer,
                deps.markdown_writer,
                deps.settings.transcripts_dir(),
                deps.settings,
                diarization_model_name=deps.diarization_model_name,
                snapshot_repository=deps.snapshot_repository,
                processing_fingerprint=fingerprint,
            ),
        )
        return source_steps + common_suffix
