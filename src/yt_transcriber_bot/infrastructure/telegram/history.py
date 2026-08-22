"""Telegram presentation helpers for numbered completed-history commands."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from yt_transcriber_bot.domain.entities.job import Job
from yt_transcriber_bot.domain.entities.media_metadata import MediaMetadata


class HistoryTitleSource(Protocol):
    """Optional canonical metadata reader used only for presentation titles."""

    def metadata_for(self, slug: str) -> MediaMetadata | None: ...


class HistoryPresentation:
    """Title lookup and rendering kept at the Telegram presentation boundary."""

    def __init__(self, title_source: HistoryTitleSource | None = None) -> None:
        self._title_source = title_source

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

    def format_job(
        self,
        job: Job,
        prefetched_titles: dict[str, str] | None = None,
    ) -> str:
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
        return job.canonical_transcript_ref


def parse_history_index(text: str) -> int:
    """Parse transport command index; omitted or invalid preserves legacy index 1."""

    parts = (text or "").strip().split()
    if len(parts) < 2:
        return 1
    try:
        return int(parts[1])
    except ValueError:
        return 1
