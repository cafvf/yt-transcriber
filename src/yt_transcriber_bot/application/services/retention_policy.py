"""Retenção FIFO orientada por Job e taxonomia explícita de artefatos."""

from __future__ import annotations

import logging
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from yt_transcriber_bot.application.job_request_context import JobRequestContext
from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.application.services.filesystem_safety import (
    UnsafeFilesystemTargetError,
    remove_empty_owned_dir,
    unlink_owned_file,
)
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
    """Expurga somente artefatos voláteis e reconcilia referências persistidas."""

    def __init__(
        self,
        repository: JobRepository,
        *,
        owned_roots: tuple[Path, ...],
        max_volatile_jobs: int = DEFAULT_MAX_VOLATILE_JOBS,
    ) -> None:
        if max_volatile_jobs < 1:
            raise ValueError("max_volatile_jobs deve ser >= 1")
        if not owned_roots:
            raise ValueError("owned_roots deve conter ao menos um diretório volátil")
        self._repository = repository
        self._owned_roots = tuple(owned_roots)
        self._max = max_volatile_jobs

    def apply(self) -> RetentionResult:
        jobs = self._repository.list_completed_oldest_first()
        if len(jobs) <= self._max:
            return RetentionResult(expired_jobs=(), removed_files=())

        expired_ids: list[str] = []
        removed: list[Path] = []
        for job in jobs[: -self._max]:
            removed.extend(self._purge_volatiles(job))
            expired_ids.append(job.job_id)
        return RetentionResult(tuple(expired_ids), tuple(removed))

    def _save_request_context_without_source(self, context: JobRequestContext) -> None:
        saver = getattr(self._repository, "save_request_context", None)
        if callable(saver):
            saver(
                JobRequestContext(
                    job_id=context.job_id,
                    delivery_chat_id=context.delivery_chat_id,
                    source_locator=None,
                )
            )

    def _purge_volatiles(self, job: Job) -> list[Path]:
        removed: list[Path] = []
        get_context = getattr(self._repository, "get_request_context", None)
        request_context = get_context(job.job_id) if callable(get_context) else None
        source_path = (
            request_context.source_locator
            if request_context is not None
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
        for artifact_class, str_path, field_name in candidates:
            if not str_path:
                continue
            path = Path(str_path)
            try:
                if unlink_owned_file(path, self._owned_roots):
                    removed.append(path)
                # Um target owned ausente também não deve continuar anunciado.
                if field_name == "request_source_locator":
                    if request_context is not None:
                        self._save_request_context_without_source(request_context)
                else:
                    setattr(job, field_name, None)
                    changed = True
            except UnsafeFilesystemTargetError:
                logger.warning(
                    "Retenção recusou target fora dos roots owned. job_id=%s artifact=%s",
                    job.job_id,
                    artifact_class.value,
                )
                if field_name == "request_source_locator":
                    if request_context is not None:
                        self._save_request_context_without_source(request_context)
                else:
                    setattr(job, field_name, None)
                    changed = True
            except OSError as exc:
                logger.warning(
                    "Falha ao remover artefato volátil. job_id=%s artifact=%s error=%s",
                    job.job_id,
                    artifact_class.value,
                    type(exc).__name__,
                )
        if source_path:
            with suppress(OSError, UnsafeFilesystemTargetError):
                remove_empty_owned_dir(Path(source_path).parent, self._owned_roots)
        if changed:
            self._repository.save(job)
        return removed
