"""Política de retenção FIFO consolidada.

Decisões:
- Dúvida 19: máximo 5 arquivos por pasta. 6º entra → mais antigo sai.
- Dúvida 28 (refinado por Dúvida 19/28 combinadas): MDs ficam como legado;
  só áudios brutos (downloads/), áudios comprimidos (processed/) e logs por
  job (logs/<slug>.log) são expurgados. Os arquivos JSON de turnos crus
  (data/segments/), também são mantidos para suportar /rename em legado.

A política expurga **por job** (não por arquivo individual) para manter
consistência: quando um job é elegido para expurgo, todos os artefatos
voláteis daquele job vão juntos (audio bruto + .ogg + log), e o MD/JSON
permanecem.
"""

from __future__ import annotations

import logging
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from yt_transcriber_bot.application.ports.job_repository import JobRepository
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
    """Aplica retenção FIFO sobre jobs concluídos."""

    def __init__(
        self,
        repository: JobRepository,
        *,
        max_volatile_jobs: int = DEFAULT_MAX_VOLATILE_JOBS,
    ) -> None:
        if max_volatile_jobs < 1:
            raise ValueError("max_volatile_jobs deve ser >= 1")
        self._repository = repository
        self._max = max_volatile_jobs

    def apply(self) -> RetentionResult:
        """Aplica a política e retorna o resultado.

        - Lista jobs concluídos do mais antigo para o mais recente.
        - Mantém os ``max_volatile_jobs`` mais novos com áudios+logs.
        - Para os mais antigos, remove áudios brutos, comprimidos e logs;
          mantém o MD intacto.
        """
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

    @staticmethod
    def _purge_volatiles(job: Job) -> list[Path]:
        removed: list[Path] = []
        source_path = (
            job.source_url
            if job.media_source is not None
            and job.media_source.source_type is MediaSourceType.TELEGRAM_AUDIO
            else None
        )
        for str_path in (source_path, job.audio_path, job.log_path):
            if not str_path:
                continue
            path = Path(str_path)
            try:
                if path.is_file():
                    path.unlink()
                    removed.append(path)
            except OSError as exc:
                logger.warning("Falha ao remover %s: %s", path, exc)
        if source_path:
            with suppress(OSError):
                Path(source_path).parent.rmdir()
        return removed
