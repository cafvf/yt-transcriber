"""Política de retenção FIFO consolidada.

A política expurga apenas artefatos voláteis de jobs concluídos e nunca usa um
path persistido como autorização implícita para apagar fora dos roots locais
explicitamente pertencentes ao aplicativo.
"""

from __future__ import annotations

import logging
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.application.services.filesystem_safety import (
    UnsafeFilesystemTargetError,
    remove_empty_owned_dir,
    unlink_owned_file,
)
from yt_transcriber_bot.domain.entities.job import Job
from yt_transcriber_bot.domain.value_objects.media_source import MediaSourceType

logger = logging.getLogger(__name__)

DEFAULT_MAX_VOLATILE_JOBS = 5


@dataclass(frozen=True)
class RetentionResult:
    """Resultado de uma execução da política."""

    expired_jobs: tuple[str, ...]
    removed_files: tuple[Path, ...]


class RetentionPolicy:
    """Aplica retenção FIFO somente dentro de roots voláteis explicitamente owned."""

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
        """Remove source/audio/log dos jobs mais antigos sem tocar evidência canônica."""

        jobs = self._repository.list_completed_oldest_first()
        if len(jobs) <= self._max:
            return RetentionResult(expired_jobs=(), removed_files=())

        to_expire = jobs[: -self._max]
        expired_ids: list[str] = []
        removed: list[Path] = []
        for job in to_expire:
            removed.extend(self._purge_volatiles(job))
            expired_ids.append(job.job_id)
        return RetentionResult(
            expired_jobs=tuple(expired_ids),
            removed_files=tuple(removed),
        )

    def _purge_volatiles(self, job: Job) -> list[Path]:
        removed: list[Path] = []
        source_path = (
            job.source_url
            if job.media_source is not None
            and job.media_source.source_type is MediaSourceType.TELEGRAM_AUDIO
            else None
        )
        for label, str_path in (
            ("source", source_path),
            ("audio", job.audio_path),
            ("log", job.log_path),
        ):
            if not str_path:
                continue
            path = Path(str_path)
            try:
                if unlink_owned_file(path, self._owned_roots):
                    removed.append(path)
            except UnsafeFilesystemTargetError:
                logger.warning(
                    "Retenção recusou target fora dos roots owned. job_id=%s artifact=%s",
                    job.job_id,
                    label,
                )
            except OSError as exc:
                logger.warning(
                    "Falha ao remover artefato volátil. job_id=%s artifact=%s error=%s",
                    job.job_id,
                    label,
                    type(exc).__name__,
                )
        if source_path:
            with suppress(OSError, UnsafeFilesystemTargetError):
                remove_empty_owned_dir(Path(source_path).parent, self._owned_roots)
        return removed
