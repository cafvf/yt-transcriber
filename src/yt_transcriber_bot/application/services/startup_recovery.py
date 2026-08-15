"""Startup recovery com contexto de entrega separado e validação source-specific."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from yt_transcriber_bot.application.job_request_context import JobRequestContext
from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.media_source import MediaSourceType
from yt_transcriber_bot.domain.value_objects.video_id import InvalidYouTubeUrlError, VideoId

_INTERRUPTED_ACTIVE_STATES = frozenset(
    {
        JobStatus.ACQUIRING,
        JobStatus.CONVERTING,
        JobStatus.TRANSCRIBING,
        JobStatus.DIARIZING,
        JobStatus.RENDERING,
    }
)


@dataclass(frozen=True)
class StartupRecoveryResult:
    pending_to_requeue: tuple[Job, ...]
    interrupted_failed: tuple[Job, ...]
    interrupted_delivery_failed: tuple[Job, ...]


class StartupRecoveryService:
    """Repara jobs interrompidos e seleciona pending recuperáveis."""

    def __init__(self, repository: JobRepository) -> None:
        self._repository = repository

    def recover(self) -> StartupRecoveryResult:
        pending_to_requeue: list[Job] = []
        interrupted_failed: list[Job] = []
        interrupted_delivery_failed: list[Job] = []

        for job in self._repository.list_by_statuses_oldest_first({JobStatus.PENDING}):
            request_context = self._repository.get_request_context(job.job_id)
            if self._has_restart_payload(job, request_context):
                pending_to_requeue.append(job)
                continue
            job.transition_to(
                JobStatus.FAILED,
                error=(
                    "Job pendente legado sem payload suficiente para retomar após "
                    "reinício do processo."
                ),
            )
            self._repository.save(job)
            interrupted_failed.append(job)

        for job in self._repository.list_by_statuses_oldest_first(set(_INTERRUPTED_ACTIVE_STATES)):
            job.transition_to(
                JobStatus.FAILED,
                error=(
                    "Job interrompido por reinício do processo antes da conclusão; "
                    "reenvie o vídeo ou use /redo."
                ),
            )
            self._repository.save(job)
            interrupted_failed.append(job)

        for job in self._repository.list_by_statuses_oldest_first({JobStatus.DELIVERING}):
            job.transition_to(
                JobStatus.DELIVERY_FAILED,
                error=(
                    "Entrega interrompida por reinício do processo; consulte "
                    "/lasterror para recuperar os artefatos locais."
                ),
            )
            self._repository.save(job)
            interrupted_delivery_failed.append(job)

        return StartupRecoveryResult(
            pending_to_requeue=tuple(pending_to_requeue),
            interrupted_failed=tuple(interrupted_failed),
            interrupted_delivery_failed=tuple(interrupted_delivery_failed),
        )

    @staticmethod
    def _has_restart_payload(job: Job, request_context: JobRequestContext | None) -> bool:
        if (
            request_context is None
            or request_context.delivery_chat_id is None
            or not job.artifact_policy.strip()
            or not request_context.source_locator
            or not request_context.source_locator.strip()
            or job.media_source is None
        ):
            return False

        if job.media_source.source_type is MediaSourceType.YOUTUBE:
            if job.video_id is None:
                return False
            try:
                return VideoId.from_url(request_context.source_locator) == job.video_id
            except (InvalidYouTubeUrlError, ValueError):
                return False

        if job.media_source.source_type is MediaSourceType.TELEGRAM_AUDIO:
            if job.source_duration_seconds is None or job.source_duration_seconds <= 0:
                return False
            try:
                return Path(request_context.source_locator).is_file()
            except OSError:
                return False

        return False
