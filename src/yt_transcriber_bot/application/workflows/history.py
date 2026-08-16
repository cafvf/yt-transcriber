"""Portable completed-history selection and Markdown retrieval policy."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.domain.entities.job import Job, JobStatus

MarkdownAvailabilityProbe = Callable[[Path], bool]


class MarkdownRetrievalState(StrEnum):
    AVAILABLE = "available"
    MISSING_REFERENCE = "missing_reference"
    MISSING_FILE = "missing_file"


@dataclass(frozen=True, slots=True)
class CompletedHistorySelection:
    job: Job
    markdown_path: Path | None
    markdown_state: MarkdownRetrievalState


class CompletedHistoryWorkflow:
    """Own completed-history scoping, ordering, selection and retrieval decisions."""

    def __init__(
        self,
        repository: JobRepository | None,
        *,
        markdown_available: MarkdownAvailabilityProbe | None = None,
    ) -> None:
        self._repository = repository
        self._markdown_available = markdown_available

    def list_completed(self, user_id: int, *, limit: int) -> list[Job]:
        if self._repository is None or limit <= 0:
            return []
        jobs = self._repository.list_recent_for_user(
            user_id,
            limit=max(limit * 3, limit),
        )
        completed = [
            job
            for job in jobs
            if job.requested_by_user_id == user_id and job.status is JobStatus.COMPLETED
        ]
        completed.sort(key=lambda job: job.updated_at, reverse=True)
        return completed[:limit]

    @staticmethod
    def select_from_completed(jobs: list[Job], *, index: int) -> Job | None:
        if index <= 0 or index > len(jobs):
            return None
        return jobs[index - 1]

    def select(self, user_id: int, *, index: int) -> Job | None:
        jobs = self.list_completed(user_id, limit=max(index, 10))
        return self.select_from_completed(jobs, index=index)

    def resolve_markdown(self, job: Job) -> CompletedHistorySelection:
        if job.md_path is None:
            return CompletedHistorySelection(
                job=job,
                markdown_path=None,
                markdown_state=MarkdownRetrievalState.MISSING_REFERENCE,
            )
        path = Path(job.md_path)
        available = self._markdown_available is not None and self._markdown_available(path)
        return CompletedHistorySelection(
            job=job,
            markdown_path=path,
            markdown_state=(
                MarkdownRetrievalState.AVAILABLE
                if available
                else MarkdownRetrievalState.MISSING_FILE
            ),
        )
