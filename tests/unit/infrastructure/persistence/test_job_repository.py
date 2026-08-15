"""Testes do ``SqlAlchemyJobRepository`` usando SQLite em memória.

Marcados como ``integration`` porque tocam o engine SQLite de verdade.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest
from sqlalchemy import text

from yt_transcriber_bot.application.job_request_context import JobRequestContext
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.media_source import MediaSource
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.persistence.sqlalchemy.job_repository import (
    SqlAlchemyJobRepository,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def repo() -> SqlAlchemyJobRepository:
    return SqlAlchemyJobRepository.from_url("sqlite:///:memory:")


def _make_job(user_id: int = 1, video: str = "dQw4w9WgXcQ") -> Job:
    return Job.new(
        VideoId(value=video),
        user_id=user_id,
        requested_language="pt",
        artifact_policy="audio+markdown",
    )


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
        with repo._engine.begin() as connection:
            connection.execute(
                text("UPDATE jobs SET status = 'downloading' WHERE job_id = :job_id"),
                {"job_id": job.job_id},
            )
        loaded = repo.get_by_id(job.job_id)
        assert loaded is not None
        assert loaded.status is JobStatus.ACQUIRING

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
        job.canonical_transcript_ref = "x"
        repo.save(job)
        loaded = repo.get_by_id(job.job_id)
        assert loaded is not None
        assert loaded.md_path == "/tmp/x.md"
        assert loaded.audio_path == "/tmp/x.ogg"
        assert loaded.log_path == "/tmp/x.log"
        assert loaded.canonical_transcript_ref == "x"

    def test_persists_error_message(self, repo: SqlAlchemyJobRepository) -> None:
        job = _make_job()
        job.transition_to(JobStatus.FAILED, error="boom")
        repo.save(job)
        loaded = repo.get_by_id(job.job_id)
        assert loaded is not None
        assert loaded.error_message == "boom"

    def test_persists_recovery_request_payload(self, repo: SqlAlchemyJobRepository) -> None:
        job = _make_job()
        repo.save(job)
        repo.save_request_context(
            JobRequestContext(
                job_id=job.job_id,
                delivery_chat_id=1001,
                source_locator="https://youtu.be/dQw4w9WgXcQ",
            )
        )
        loaded = repo.get_by_id(job.job_id)
        context = repo.get_request_context(job.job_id)
        assert loaded is not None
        assert loaded.requested_language == "pt"
        assert loaded.artifact_policy == "audio+markdown"
        assert context == JobRequestContext(job.job_id, 1001, "https://youtu.be/dQw4w9WgXcQ")

    def test_persists_default_youtube_media_source(self, repo: SqlAlchemyJobRepository) -> None:
        job = _make_job()

        repo.save(job)
        loaded = repo.get_by_id(job.job_id)

        assert loaded is not None
        assert loaded.media_source.source_type == "youtube"
        assert loaded.media_source.canonical_reference == (
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )

    def test_telegram_job_round_trip_persists_null_video_id(
        self, repo: SqlAlchemyJobRepository
    ) -> None:
        job = Job.new(
            None,
            user_id=1,
            media_source=MediaSource.telegram_audio("private-file-id"),
            source_title="Mensagem de voz",
        )

        repo.save(job)

        loaded = repo.get_by_id(job.job_id)
        assert loaded is not None
        assert loaded.video_id is None
        assert loaded.media_source == MediaSource.telegram_audio("private-file-id")
        with repo._engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT video_id FROM jobs WHERE job_id = :job_id"),
                    {"job_id": job.job_id},
                ).scalar_one()
                is None
            )


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
        _complete(a)
        repo.save(a)
        time.sleep(0.01)
        b = _make_job(user_id=1)
        _complete(b)
        repo.save(b)
        latest = repo.get_latest_completed_for_user(1)
        assert latest is not None
        assert latest.job_id == b.job_id

    def test_get_latest_completed_skips_other_users(self, repo: SqlAlchemyJobRepository) -> None:
        other = _make_job(user_id=999)
        _complete(other)
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
        _complete(a)
        repo.save(a)
        time.sleep(0.01)
        b = _make_job(user_id=1)
        _complete(b)
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


class TestRecoveryQueries:
    def test_list_by_statuses_oldest_first(self, repo: SqlAlchemyJobRepository) -> None:
        pending = _make_job()
        repo.save(pending)
        time.sleep(0.01)
        delivering = _make_job(video="aaaaaaaaaaa")
        for status in (
            JobStatus.ACQUIRING,
            JobStatus.CONVERTING,
            JobStatus.TRANSCRIBING,
            JobStatus.DIARIZING,
            JobStatus.RENDERING,
            JobStatus.DELIVERING,
        ):
            delivering.transition_to(status)
        repo.save(delivering)
        time.sleep(0.01)
        failed = _make_job(video="bbbbbbbbbbb")
        failed.transition_to(JobStatus.FAILED, error="boom")
        repo.save(failed)

        rows = repo.list_by_statuses_oldest_first({JobStatus.PENDING, JobStatus.DELIVERING})
        assert [job.job_id for job in rows] == [pending.job_id, delivering.job_id]


def test_migrates_existing_sqlite_database_with_phase2_columns(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE jobs (
            job_id TEXT PRIMARY KEY,
            video_id TEXT NOT NULL,
            status TEXT NOT NULL,
            requested_by_user_id INTEGER NOT NULL,
            requested_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            error_message TEXT,
            config_signature TEXT NOT NULL DEFAULT '',
            speaker_renames_json TEXT NOT NULL DEFAULT '{}',
            md_path TEXT,
            audio_path TEXT,
            log_path TEXT
        )
        """
    )
    conn.commit()
    conn.close()

    repo = SqlAlchemyJobRepository.from_url(f"sqlite:///{db_path}")
    job = _make_job()
    repo.save(job)
    repo.save_request_context(JobRequestContext(job.job_id, 1001, "https://youtu.be/dQw4w9WgXcQ"))
    loaded = repo.get_by_id(job.job_id)
    context = repo.get_request_context(job.job_id)

    assert loaded is not None
    assert loaded.requested_language == "pt"
    assert loaded.artifact_policy == "audio+markdown"
    assert context == JobRequestContext(job.job_id, 1001, "https://youtu.be/dQw4w9WgXcQ")


def test_migrates_legacy_jobs_to_youtube_media_source(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy-source.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE jobs (
            job_id TEXT PRIMARY KEY,
            video_id TEXT NOT NULL,
            status TEXT NOT NULL,
            requested_by_user_id INTEGER NOT NULL,
            requested_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            error_message TEXT,
            config_signature TEXT NOT NULL DEFAULT '',
            speaker_renames_json TEXT NOT NULL DEFAULT '{}',
            md_path TEXT,
            audio_path TEXT,
            log_path TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO jobs (
            job_id, video_id, status, requested_by_user_id, requested_at, updated_at,
            config_signature, speaker_renames_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "legacy-job",
            "dQw4w9WgXcQ",
            "completed",
            42,
            "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00",
            "",
            "{}",
        ),
    )
    conn.commit()
    conn.close()

    repo = SqlAlchemyJobRepository.from_url(f"sqlite:///{db_path}")
    loaded = repo.get_by_id("legacy-job")

    assert loaded is not None
    assert loaded.video_id == VideoId(value="dQw4w9WgXcQ")
    assert loaded.media_source.source_type == "youtube"
    assert loaded.media_source.canonical_reference == (
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )


def test_migration_backfills_explicit_snapshot_reference_for_legacy_markdown(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "legacy-canonical-ref.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE jobs (
            job_id TEXT PRIMARY KEY,
            video_id TEXT NOT NULL,
            status TEXT NOT NULL,
            requested_by_user_id INTEGER NOT NULL,
            requested_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            error_message TEXT,
            config_signature TEXT NOT NULL DEFAULT '',
            speaker_renames_json TEXT NOT NULL DEFAULT '{}',
            md_path TEXT,
            audio_path TEXT,
            log_path TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO jobs (
            job_id, video_id, status, requested_by_user_id, requested_at, updated_at,
            config_signature, speaker_renames_json, md_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "legacy-canonical",
            "dQw4w9WgXcQ",
            "completed",
            42,
            "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00",
            "",
            "{}",
            "/private/transcripts/legacy-title.md",
        ),
    )
    conn.commit()
    conn.close()

    repo = SqlAlchemyJobRepository.from_url(f"sqlite:///{db_path}")
    loaded = repo.get_by_id("legacy-canonical")

    assert loaded is not None
    assert loaded.canonical_transcript_ref == "legacy-title"


def test_nullable_video_id_migration_rebuilds_indexed_legacy_sqlite_table(tmp_path: Path) -> None:
    db_path = tmp_path / "indexed-legacy.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE jobs (
            job_id TEXT PRIMARY KEY, video_id TEXT NOT NULL, status TEXT NOT NULL,
            requested_by_user_id INTEGER NOT NULL, requested_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, error_message TEXT, config_signature TEXT NOT NULL DEFAULT '',
            speaker_renames_json TEXT NOT NULL DEFAULT '{}', md_path TEXT, audio_path TEXT, log_path TEXT
        )
        """
    )
    conn.execute("CREATE INDEX ix_jobs_video_id ON jobs (video_id)")
    conn.execute(
        "INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "legacy",
            "dQw4w9WgXcQ",
            "completed",
            7,
            "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00",
            None,
            "",
            "{}",
            None,
            None,
            None,
        ),
    )
    conn.commit()
    conn.close()

    repo = SqlAlchemyJobRepository.from_url(f"sqlite:///{db_path}")
    assert repo.get_by_id("legacy") is not None
    telegram = Job.new(None, user_id=7, media_source=MediaSource.telegram_audio("private-file-id"))
    repo.save(telegram)
    assert repo.get_by_id(telegram.job_id) is not None
    with repo._engine.connect() as connection:
        assert connection.execute(text("PRAGMA index_list('jobs')")).mappings().all()
    assert SqlAlchemyJobRepository.from_url(f"sqlite:///{db_path}").get_by_id("legacy") is not None
