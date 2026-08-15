"""Use case de transcrição com evidência canônica obrigatória para sucesso."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from yt_transcriber_bot.application.config import AppSettings
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
    PipelineRejectionError,
    RenderMarkdownStep,
    SelectRuntimeStep,
    TranscribeStep,
    TranscriptionStepProgress,
)
from yt_transcriber_bot.application.ports.audio_converter import AudioConverter
from yt_transcriber_bot.application.ports.diarization_engine import DiarizationEngine
from yt_transcriber_bot.application.ports.gpu_detector import GpuDetector
from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.application.ports.transcription_engine import TranscriptionEngine
from yt_transcriber_bot.application.ports.youtube_downloader import YouTubeDownloader
from yt_transcriber_bot.application.services.config_signature import (
    compute_processing_fingerprint,
)
from yt_transcriber_bot.application.services.sanitization import sanitize_text
from yt_transcriber_bot.domain.entities.job import Job, JobStatus

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
        TranscriptSnapshotRepository,
    )


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


@dataclass
class TranscribeVideoDependencies:
    downloader: YouTubeDownloader
    converter: AudioConverter
    gpu_detector: GpuDetector
    transcription_engine: TranscriptionEngine
    diarization_engine: DiarizationEngine
    renderer: object
    settings: AppSettings
    repository: JobRepository
    snapshot_repository: TranscriptSnapshotRepository | None = None
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
        requested_language: str | None = None,
        source_locator: str | None = None,
    ) -> TranscribeVideoResult:
        deps = self._deps
        effective_requested_language = requested_language or job.requested_language
        job.requested_language = effective_requested_language
        source_type = job.media_source.source_type.value if job.media_source else None
        job.config_signature = compute_processing_fingerprint(
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
        except PipelineCanceledError:
            job.transition_to(JobStatus.CANCELLED, error="cancelado pelo usuario")
            deps.repository.save(job)
            return self._result(ctx, canceled=True)
        except PipelineRejectionError as exc:
            failure_reason = sanitize_text(str(exc), deps.settings)
            job.transition_to(JobStatus.FAILED, error=failure_reason)
            deps.repository.save(job)
            return self._result(ctx, failure_reason=failure_reason, canonical=False)
        except Exception as exc:
            failure_reason = sanitize_text(f"{type(exc).__name__}: {exc}", deps.settings)
            logger.error("Pipeline falhou: %s", failure_reason)
            job.transition_to(JobStatus.FAILED, error=failure_reason)
            deps.repository.save(job)
            return self._result(ctx, failure_reason=failure_reason, canonical=False)

        if ctx.final_md_path is None or not job.canonical_transcript_ref:
            failure_reason = "Evidência canônica da transcrição não foi persistida."
            job.transition_to(JobStatus.FAILED, error=failure_reason)
            deps.repository.save(job)
            return self._result(ctx, failure_reason=failure_reason, canonical=False)

        job.transition_to(JobStatus.DELIVERING)
        deps.repository.save(job)
        return self._result(ctx)

    def _result(
        self,
        ctx: PipelineContext,
        *,
        canceled: bool = False,
        failure_reason: str | None = None,
        canonical: bool = True,
    ) -> TranscribeVideoResult:
        return TranscribeVideoResult(
            job=ctx.job,
            md_path=ctx.final_md_path if canonical else None,
            audio_path=ctx.converted_audio_path if canonical else None,
            diagnostics=tuple(ctx.diagnostics),
            language_code=ctx.transcription_language,
            language_source=ctx.language_source,
            language_confidence=ctx.transcription_confidence,
            canceled=canceled,
            failure_reason=failure_reason,
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
        fingerprint = job.config_signature or compute_processing_fingerprint(
            deps.settings,
            requested_language=job.requested_language,
            source_type=source.source_type.value,
        )
        common_suffix: tuple[PipelineStep, ...] = (
            ConvertAudioStep(deps.converter, deps.settings.processed_dir(), deps.settings),
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
                deps.settings.transcripts_dir(),
                deps.settings,
                diarization_model_name=deps.diarization_model_name,
                snapshot_repository=deps.snapshot_repository,
                processing_fingerprint=fingerprint,
            ),
        )
        return source_steps + common_suffix
