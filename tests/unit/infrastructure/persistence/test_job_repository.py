"""Testes do ``SqlAlchemyJobRepository`` usando SQLite em memória.

Marcados como ``integration`` porque tocam o engine SQLite de verdade.
"""

from __future__ import annotations

import time

import pytest

from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.persistence.sqlalchemy.job_repository import (
    SqlAlchemyJobRepository,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def repo() -> SqlAlchemyJobRepository:
    return SqlAlchemyJobRepository.from_url("sqlite:///:memory:")


def _make_job(user_id: int = 1, video: str = "dQw4w9WgXcQ") -> Job:
    return Job.new(VideoId(value=video), user_id=user_id)


class TestRoundtrip:
    def test_save_and_get_by_id(self, repo: SqlAlchemyJobRepository) -> None:
        job = _make_job()
        repo.save(job)
        loaded = repo.get_by_id(job.job_id)
        assert loaded is not None
        assert loaded.job_id == job.job_id
        assert loaded.video_id.value == "dQw4w9WgXcQ"
        assert loaded.status is JobStatus.PENDING

    def test_get_by_id_missing_returns_none(self, repo: SqlAlchemyJobRepository) -> None:
        assert repo.get_by_id("nonexistent") is None

    def test_save_is_upsert(self, repo: SqlAlchemyJobRepository) -> None:
        job = _make_job()
        repo.save(job)
        job.transition_to(JobStatus.DOWNLOADING)
        repo.save(job)
        loaded = repo.get_by_id(job.job_id)
        assert loaded is not None
        assert loaded.status is JobStatus.DOWNLOADING

    def test_persists_speaker_renames(self, repo: SqlAlchemyJobRepository) -> None:
        job = _make_job()
        job.apply_rename("SPEAKER_00", "Eduardo")
        job.apply_rename("SPEAKER_01", "Maria")
        repo.save(job)
        loaded = repo.get_by_id(job.job_id)
        assert loaded is not None
        assert loaded.speaker_renames == {
            "SPEAKER_00": "Eduardo",
            "SPEAKER_01": "Maria",
        }

    def test_persists_paths(self, repo: SqlAlchemyJobRepository) -> None:
        job = _make_job()
        job.md_path = "/tmp/x.md"
        job.audio_path = "/tmp/x.ogg"
        job.log_path = "/tmp/x.log"
        repo.save(job)
        loaded = repo.get_by_id(job.job_id)
        assert loaded is not None
        assert loaded.md_path == "/tmp/x.md"
        assert loaded.audio_path == "/tmp/x.ogg"
        assert loaded.log_path == "/tmp/x.log"

    def test_persists_error_message(self, repo: SqlAlchemyJobRepository) -> None:
        job = _make_job()
        job.transition_to(JobStatus.FAILED, error="boom")
        repo.save(job)
        loaded = repo.get_by_id(job.job_id)
        assert loaded is not None
        assert loaded.error_message == "boom"


class TestQueriesByVideoId:
    def test_get_latest_by_video_id_returns_most_recent(
        self, repo: SqlAlchemyJobRepository
    ) -> None:
        first = _make_job()
        repo.save(first)
        time.sleep(0.01)
        second = _make_job()
        repo.save(second)
        latest = repo.get_latest_by_video_id(VideoId(value="dQw4w9WgXcQ"))
        assert latest is not None
        assert latest.job_id == second.job_id

    def test_get_latest_by_video_id_missing(self, repo: SqlAlchemyJobRepository) -> None:
        assert repo.get_latest_by_video_id(VideoId(value="aaaaaaaaaaa")) is None


class TestQueriesPerUser:
    def test_get_latest_completed_for_user(self, repo: SqlAlchemyJobRepository) -> None:
        a = _make_job(user_id=1)
        a.transition_to(JobStatus.COMPLETED)
        repo.save(a)
        time.sleep(0.01)
        b = _make_job(user_id=1)
        b.transition_to(JobStatus.COMPLETED)
        repo.save(b)
        latest = repo.get_latest_completed_for_user(1)
        assert latest is not None
        assert latest.job_id == b.job_id

    def test_get_latest_completed_skips_other_users(self, repo: SqlAlchemyJobRepository) -> None:
        other = _make_job(user_id=999)
        other.transition_to(JobStatus.COMPLETED)
        repo.save(other)
        assert repo.get_latest_completed_for_user(1) is None

    def test_get_latest_completed_skips_non_completed(self, repo: SqlAlchemyJobRepository) -> None:
        pending = _make_job(user_id=1)
        repo.save(pending)
        assert repo.get_latest_completed_for_user(1) is None

    def test_list_recent_for_user_respects_limit(self, repo: SqlAlchemyJobRepository) -> None:
        for _ in range(5):
            repo.save(_make_job(user_id=1))
            time.sleep(0.005)
        rows = repo.list_recent_for_user(1, limit=3)
        assert len(rows) == 3

    def test_list_recent_returns_newest_first(self, repo: SqlAlchemyJobRepository) -> None:
        first = _make_job(user_id=1)
        repo.save(first)
        time.sleep(0.01)
        second = _make_job(user_id=1)
        repo.save(second)
        rows = repo.list_recent_for_user(1, limit=2)
        assert rows[0].job_id == second.job_id
        assert rows[1].job_id == first.job_id

    def test_list_recent_zero_limit(self, repo: SqlAlchemyJobRepository) -> None:
        repo.save(_make_job(user_id=1))
        assert repo.list_recent_for_user(1, limit=0) == []


class TestRetentionQuery:
    def test_list_completed_oldest_first(self, repo: SqlAlchemyJobRepository) -> None:
        a = _make_job(user_id=1)
        a.transition_to(JobStatus.COMPLETED)
        repo.save(a)
        time.sleep(0.01)
        b = _make_job(user_id=1)
        b.transition_to(JobStatus.COMPLETED)
        repo.save(b)
        rows = repo.list_completed_oldest_first()
        assert [j.job_id for j in rows] == [a.job_id, b.job_id]

    def test_list_completed_skips_non_completed(self, repo: SqlAlchemyJobRepository) -> None:
        pending = _make_job(user_id=1)
        repo.save(pending)
        assert repo.list_completed_oldest_first() == []


class TestDelete:
    def test_delete_removes_job(self, repo: SqlAlchemyJobRepository) -> None:
        job = _make_job()
        repo.save(job)
        repo.delete(job.job_id)
        assert repo.get_by_id(job.job_id) is None

    def test_delete_nonexistent_silent(self, repo: SqlAlchemyJobRepository) -> None:
        repo.delete("doesnotexist")  # não levanta
