from __future__ import annotations

from pathlib import Path

import pytest

from yt_transcriber_bot.application.ports.text_search import SearchDocument
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.persistence.sqlalchemy.job_repository import (
    SqlAlchemyJobRepository,
)
from yt_transcriber_bot.infrastructure.persistence.sqlalchemy.text_search_repository import (
    SqlAlchemyTextSearchRepository,
)

pytestmark = pytest.mark.integration


def _complete(job: Job) -> None:
    for status in (
        JobStatus.ACQUIRING,
        JobStatus.CONVERTING,
        JobStatus.TRANSCRIBING,
        JobStatus.DIARIZING,
        JobStatus.RENDERING,
        JobStatus.DELIVERING,
        JobStatus.COMPLETED,
    ):
        job.transition_to(status)
    job.canonical_transcript_ref = job.video_id.value if job.video_id else "telegram"


def _repos(tmp_path: Path, *, fts: bool = False):
    url = f"sqlite:///{tmp_path / 'history.db'}"
    return (
        SqlAlchemyJobRepository.from_url(url),
        SqlAlchemyTextSearchRepository.from_url(url, enable_fts=fts),
    )


def test_job_save_has_no_hidden_search_side_effect(tmp_path: Path) -> None:
    jobs, search = _repos(tmp_path)
    job = Job.new(VideoId("dQw4w9WgXcQ"), user_id=7)
    _complete(job)
    jobs.save(job)
    assert search.search_completed_for_user(user_id=7, query="hexagonal", limit=10) == []


def test_explicit_index_is_user_scoped_and_canonical_bound(tmp_path: Path) -> None:
    jobs, search = _repos(tmp_path)
    own = Job.new(VideoId("dQw4w9WgXcQ"), user_id=7)
    other = Job.new(VideoId("aaaaaaaaaaa"), user_id=8)
    for job in (own, other):
        _complete(job)
        jobs.save(job)
        search.replace(
            SearchDocument(
                job_id=job.job_id,
                canonical_transcript_ref=job.canonical_transcript_ref or "",
                user_id=job.requested_by_user_id,
                title="Título",
                content="privacidade conteúdo",
                updated_at=job.updated_at,
            )
        )
    hits = search.search_completed_for_user(user_id=7, query="privacidade", limit=10)
    assert [hit.job_id for hit in hits] == [own.job_id]
    own.canonical_transcript_ref = "replacement"
    jobs.save(own)
    assert search.search_completed_for_user(user_id=7, query="privacidade", limit=10) == []


def test_job_deletion_invalidates_stale_search_document(tmp_path: Path) -> None:
    jobs, search = _repos(tmp_path)
    job = Job.new(VideoId("dQw4w9WgXcQ"), user_id=7)
    _complete(job)
    jobs.save(job)
    search.replace(
        SearchDocument(
            job.job_id,
            job.canonical_transcript_ref or "",
            7,
            "Título",
            "termo exclusivo",
            job.updated_at,
        )
    )
    jobs.delete(job.job_id)
    assert search.search_completed_for_user(user_id=7, query="termo", limit=10) == []
