from __future__ import annotations

import logging
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from yt_transcriber_bot.application.job_request_context import JobRequestContext
from yt_transcriber_bot.application.ports.artifact_cleanup import (
    ArtifactCleanupRefusedError,
    OwnedArtifactCleanup,
)
from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.domain.entities.job import Job
from yt_transcriber_bot.domain.value_objects.artifact import ArtifactClass
from yt_transcriber_bot.domain.value_objects.media_source import MediaSourceType

logger = logging.getLogger(__name__)
DEFAULT_MAX_VOLATILE_JOBS = 5


@dataclass(frozen=True)
class RetentionResult:
    expired_jobs: tuple[str, ...]
    removed_files: tuple[Path, ...]


class RetentionPolicy:
    def __init__(
        self,
        repository: JobRepository,
        *,
        artifact_cleanup: OwnedArtifactCleanup,
        max_volatile_jobs: int = DEFAULT_MAX_VOLATILE_JOBS,
    ) -> None:
        if max_volatile_jobs < 1:
            raise ValueError("max_volatile_jobs deve ser >= 1")
        self._repository = repository
        self._cleanup = artifact_cleanup
        self._max = max_volatile_jobs

    def apply(self) -> RetentionResult:
        jobs = self._repository.list_completed_oldest_first()
        if len(jobs) <= self._max:
            return RetentionResult((), ())
        expired: list[str] = []
        removed: list[Path] = []
        for job in jobs[: -self._max]:
            removed.extend(self._purge(job))
            expired.append(job.job_id)
        return RetentionResult(tuple(expired), tuple(removed))

    def _save_context_without_source(self, context: JobRequestContext) -> None:
        saver = getattr(self._repository, "save_request_context", None)
        if callable(saver):
            saver(
                JobRequestContext(
                    job_id=context.job_id,
                    delivery_chat_id=context.delivery_chat_id,
                    source_locator=None,
                )
            )

    def _purge(self, job: Job) -> list[Path]:
        removed: list[Path] = []
        getter = getattr(self._repository, "get_request_context", None)
        context = getter(job.job_id) if callable(getter) else None
        source_path = (
            context.source_locator
            if context is not None
            and job.media_source is not None
            and job.media_source.source_type is MediaSourceType.TELEGRAM_AUDIO
            else None
        )
        candidates = (
            (ArtifactClass.VOLATILE_SOURCE_MEDIA, source_path, "request_source_locator"),
            (ArtifactClass.VOLATILE_CONVERTED_AUDIO, job.audio_path, "audio_path"),
            (ArtifactClass.OPERATIONAL_LOG, job.log_path, "log_path"),
        )
        changed = False
        for artifact_class, raw_path, field in candidates:
            if not raw_path:
                continue
            path = Path(raw_path)
            try:
                if self._cleanup.remove_file(path):
                    removed.append(path)
            except ArtifactCleanupRefusedError:
                logger.warning(
                    "Retention refused non-owned target. job_id=%s artifact=%s",
                    job.job_id,
                    artifact_class.value,
                )
            except OSError as exc:
                logger.warning(
                    "Retention cleanup failed. job_id=%s artifact=%s error=%s",
                    job.job_id,
                    artifact_class.value,
                    type(exc).__name__,
                )
                continue
            if field == "request_source_locator":
                if context is not None:
                    self._save_context_without_source(context)
            else:
                setattr(job, field, None)
                changed = True
        if source_path:
            with suppress(OSError, ArtifactCleanupRefusedError):
                self._cleanup.remove_empty_directory(Path(source_path).parent)
        if changed:
            self._repository.save(job)
        return removed
