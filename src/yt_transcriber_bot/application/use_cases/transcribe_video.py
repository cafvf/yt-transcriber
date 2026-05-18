"""Use case ``TranscribeVideoUseCase`` — orquestra o pipeline completo.

Aplica padrão *Facade*: encapsula a montagem do pipeline e o gerenciamento
do ciclo de vida do ``Job`` (transições de status, persistência, erros).
"""

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
)
from yt_transcriber_bot.application.pipeline.steps import (
    ConvertAudioStep,
    DiarizeStep,
    DownloadAudioStep,
    FetchMetadataStep,
    PipelineRejectionError,
    RenderMarkdownStep,
    SelectRuntimeStep,
    TranscribeStep,
    TranscriptionStepProgress,
    TryYouTubeSubtitlesStep,
)
from yt_transcriber_bot.application.ports.audio_converter import AudioConverter
from yt_transcriber_bot.application.ports.diarization_engine import DiarizationEngine
from yt_transcriber_bot.application.ports.gpu_detector import GpuDetector
from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.application.ports.transcription_engine import (
    TranscriptionEngine,
)
from yt_transcriber_bot.application.ports.youtube_downloader import YouTubeDownloader
from yt_transcriber_bot.domain.entities.job import Job, JobStatus

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
        TranscriptSnapshotRepository,
    )


@dataclass
class TranscribeVideoResult:
    """Saída do use case."""

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
    """Container das dependências (injection point único)."""

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
    """Recebe um Job pendente e roda o pipeline completo, persistindo estados."""

    def __init__(
        self,
        deps: TranscribeVideoDependencies,
    ) -> None:
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
    ) -> TranscribeVideoResult:
        deps = self._deps
        runner = PipelineRunner(
            steps=(
                FetchMetadataStep(deps.downloader, deps.settings),
                TryYouTubeSubtitlesStep(deps.downloader, deps.settings),
                DownloadAudioStep(deps.downloader, deps.settings.downloads_dir()),
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
                ),
                RenderMarkdownStep(
                    deps.renderer,
                    deps.settings.transcripts_dir(),
                    deps.settings,
                    diarization_model_name=deps.diarization_model_name,
                    snapshot_repository=deps.snapshot_repository,
                ),
            ),
            cancel_event=cancel_event,
        )
        ctx = PipelineContext(job=job, requested_language=requested_language)
        deps.repository.save(job)

        try:
            runner.run(ctx, progress=progress_step, audit=audit)
        except PipelineCanceledError:
            job.transition_to(JobStatus.CANCELLED, error="cancelado pelo usuario")
            deps.repository.save(job)
            return TranscribeVideoResult(
                job=job,
                md_path=ctx.final_md_path,
                audio_path=ctx.converted_audio_path,
                diagnostics=tuple(ctx.diagnostics),
                language_code=ctx.transcription_language,
                language_source=ctx.language_source,
                language_confidence=ctx.transcription_confidence,
                canceled=True,
            )
        except PipelineRejectionError as exc:
            job.transition_to(JobStatus.FAILED, error=str(exc))
            deps.repository.save(job)
            return TranscribeVideoResult(
                job=job,
                md_path=None,
                audio_path=None,
                diagnostics=tuple(ctx.diagnostics),
                language_code=ctx.transcription_language,
                language_source=ctx.language_source,
                language_confidence=ctx.transcription_confidence,
                failure_reason=str(exc),
            )
        except Exception as exc:
            logger.exception("Pipeline falhou: %s", exc)
            job.transition_to(JobStatus.FAILED, error=f"{type(exc).__name__}: {exc}")
            deps.repository.save(job)
            return TranscribeVideoResult(
                job=job,
                md_path=None,
                audio_path=None,
                diagnostics=tuple(ctx.diagnostics),
                language_code=ctx.transcription_language,
                language_source=ctx.language_source,
                language_confidence=ctx.transcription_confidence,
                failure_reason=str(exc),
            )

        job.transition_to(JobStatus.COMPLETED)
        deps.repository.save(job)
        return TranscribeVideoResult(
            job=job,
            md_path=ctx.final_md_path,
            audio_path=ctx.converted_audio_path,
            diagnostics=tuple(ctx.diagnostics),
            language_code=ctx.transcription_language,
            language_source=ctx.language_source,
            language_confidence=ctx.transcription_confidence,
        )

    def runner_for(self, job: Job) -> PipelineRunner:
        """Devolve um runner separado para que o caller possa cancelar."""
        deps = self._deps
        return PipelineRunner(
            steps=(
                FetchMetadataStep(deps.downloader, deps.settings),
                TryYouTubeSubtitlesStep(deps.downloader, deps.settings),
                DownloadAudioStep(deps.downloader, deps.settings.downloads_dir()),
                ConvertAudioStep(deps.converter, deps.settings.processed_dir(), deps.settings),
                SelectRuntimeStep(deps.gpu_detector, deps.settings),
                TranscribeStep(deps.transcription_engine, deps.settings),
                DiarizeStep(deps.diarization_engine, deps.settings),
                RenderMarkdownStep(
                    deps.renderer,
                    deps.settings.transcripts_dir(),
                    deps.settings,
                    diarization_model_name=deps.diarization_model_name,
                    snapshot_repository=deps.snapshot_repository,
                ),
            )
        )
