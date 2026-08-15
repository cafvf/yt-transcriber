"""Colaboração de histórico compartilhada pelos comandos Telegram numerados.

Mantém a consulta, ordenação, seleção e apresentação do histórico fora do
``TelegramBotAdapter``. A camada ainda recebe mensagens e aplica autorização;
esta colaboração apenas preserva as regras de dados usadas por esses fluxos.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata


class HistoryTitleSource(Protocol):
    """Leitura opcional de metadados de snapshots para títulos do histórico."""

    def metadata_for(self, slug: str) -> VideoMetadata | None: ...


class HistoryCollaboration:
    """Regras de histórico reutilizadas por ``/list`` e comandos com índice."""

    def __init__(
        self,
        repository: JobRepository | None,
        title_source: HistoryTitleSource | None = None,
    ) -> None:
        self._repository = repository
        self._title_source = title_source

    def completed_jobs_for_user(self, user_id: int, *, limit: int) -> list[Job]:
        if self._repository is None:
            return []
        jobs = self._repository.list_recent_for_user(user_id, limit=max(limit * 3, limit))
        completed = [
            job
            for job in jobs
            if job.requested_by_user_id == user_id and job.status == JobStatus.COMPLETED
        ]
        completed.sort(key=lambda job: job.updated_at, reverse=True)
        return completed[:limit]

    def select_completed_job(self, user_id: int, *, index: int) -> Job | None:
        jobs = self.completed_jobs_for_user(user_id, limit=max(index, 10))
        return self.select_from_completed_jobs(jobs, index=index)

    @staticmethod
    def select_from_completed_jobs(jobs: list[Job], *, index: int) -> Job | None:
        if index <= 0 or index > len(jobs):
            return None
        return jobs[index - 1]

    def prefetch_titles(self, jobs: list[Job]) -> dict[str, str]:
        if self._title_source is None:
            return {}
        slugs = tuple(
            slug for slug in (self.snapshot_ref_for_job(job) for job in jobs) if slug is not None
        )
        if not slugs:
            return {}
        metadata_for_many = getattr(self._title_source, "metadata_for_many", None)
        if callable(metadata_for_many):
            return {slug: metadata.title for slug, metadata in metadata_for_many(slugs).items()}
        titles: dict[str, str] = {}
        for slug in slugs:
            metadata = self._title_source.metadata_for(slug)
            if metadata is not None:
                titles[slug] = metadata.title
        return titles

    def format_job(self, job: Job, prefetched_titles: dict[str, str] | None = None) -> str:
        slug = self.snapshot_ref_for_job(job)
        title: str | None = None
        if slug is not None and prefetched_titles is not None:
            title = prefetched_titles.get(slug)
        elif slug is not None and self._title_source is not None:
            metadata = self._title_source.metadata_for(slug)
            if metadata is not None:
                title = metadata.title
        source_label = (
            "Telegram (mídia privada)"
            if job.media_source is not None
            and job.media_source.source_type.value == "telegram_audio"
            else "YouTube"
        )
        label = title or (Path(job.md_path).stem if job.md_path else source_label)
        when = job.updated_at.strftime("%Y-%m-%d %H:%M")
        identity = job.video_id.value if job.video_id is not None else source_label
        return f"{label} — {identity} — executado em {when}"

    @staticmethod
    def slug_from_md_path(md_path: str | None) -> str | None:
        return Path(md_path).stem if md_path is not None else None

    @staticmethod
    def snapshot_ref_for_job(job: Job) -> str | None:
        """Retorna apenas a associação estruturada durável.

        Jobs históricos recebem essa referência durante a migração SQLite; não
        reconstruímos silenciosamente uma referência ausente a partir do Markdown.
        """

        return job.canonical_transcript_ref


def parse_history_index(text: str) -> int:
    """Extrai o índice legado, usando 1 quando o argumento é omitido ou inválido."""
    parts = (text or "").strip().split()
    if len(parts) < 2:
        return 1
    try:
        return int(parts[1])
    except ValueError:
        return 1
