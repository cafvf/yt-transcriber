"""Testes da política de retenção FIFO."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from yt_transcriber_bot.application.services.retention_policy import RetentionPolicy
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class FakeRepo:
    def __init__(self, jobs: list[Job]) -> None:
        self.jobs = jobs

    def list_completed_oldest_first(self) -> list[Job]:
        return list(self.jobs)

    def list_by_statuses_oldest_first(self, statuses: set[JobStatus]) -> list[Job]:
        return [job for job in self.jobs if job.status in statuses]

    def save(self, job: Job) -> None: ...
    def get_by_id(self, job_id: str) -> Job | None: ...
    def get_latest_by_video_id(self, video_id: VideoId) -> Job | None: ...
    def get_latest_completed_for_user(self, user_id: int) -> Job | None: ...
    def list_recent_for_user(self, user_id: int, limit: int) -> list[Job]: ...
    def delete(self, job_id: str) -> None: ...


def _job_at(tmp_path: Path, idx: int) -> Job:
    audio = tmp_path / f"audio_{idx}.ogg"
    audio.write_bytes(b"OggS_data")
    log = tmp_path / f"job_{idx}.log"
    log.write_text("log content", encoding="utf-8")
    md = tmp_path / f"transcript_{idx}.md"
    md.write_text("# legacy", encoding="utf-8")

    job = Job.new(VideoId("d" + "Q" * 10), 42)
    base = datetime(2024, 1, 1, tzinfo=UTC)
    object.__setattr__(job, "requested_at", base + timedelta(hours=idx))
    object.__setattr__(job, "updated_at", base + timedelta(hours=idx))
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
    job.audio_path = str(audio)
    job.log_path = str(log)
    job.md_path = str(md)
    return job


def _policy(repo: FakeRepo, root: Path, *, max_jobs: int = 5) -> RetentionPolicy:
    return RetentionPolicy(  # type: ignore[arg-type]
        repo,
        owned_roots=(root,),
        max_volatile_jobs=max_jobs,
    )


def test_no_expiration_when_under_limit(tmp_path: Path) -> None:
    jobs = [_job_at(tmp_path, i) for i in range(3)]
    result = _policy(FakeRepo(jobs), tmp_path).apply()
    assert result.expired_jobs == ()
    assert result.removed_files == ()
    for job in jobs:
        assert Path(job.audio_path or "").exists()
        assert Path(job.log_path or "").exists()


def test_expires_oldest_when_over_limit(tmp_path: Path) -> None:
    jobs = [_job_at(tmp_path, i) for i in range(7)]
    result = _policy(FakeRepo(jobs), tmp_path).apply()
    assert len(result.expired_jobs) == 2
    assert result.expired_jobs[0] == jobs[0].job_id
    assert result.expired_jobs[1] == jobs[1].job_id
    assert jobs[0].audio_path is None
    assert jobs[0].log_path is None
    assert jobs[1].audio_path is None
    for job in jobs[2:]:
        assert Path(job.audio_path or "").exists()


def test_md_is_preserved(tmp_path: Path) -> None:
    jobs = [_job_at(tmp_path, i) for i in range(7)]
    _policy(FakeRepo(jobs), tmp_path).apply()
    for job in jobs:
        assert Path(job.md_path or "").exists()


def test_handles_missing_files_gracefully(tmp_path: Path) -> None:
    jobs = [_job_at(tmp_path, i) for i in range(7)]
    Path(jobs[0].audio_path or "").unlink()
    result = _policy(FakeRepo(jobs), tmp_path).apply()
    assert len(result.expired_jobs) == 2


def test_invalid_max_jobs(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="max_volatile_jobs"):
        RetentionPolicy(  # type: ignore[arg-type]
            FakeRepo([]), owned_roots=(tmp_path,), max_volatile_jobs=0
        )


def test_requires_explicit_owned_root() -> None:
    with pytest.raises(ValueError, match="owned_roots"):
        RetentionPolicy(FakeRepo([]), owned_roots=())  # type: ignore[arg-type]


def test_max_jobs_one(tmp_path: Path) -> None:
    jobs = [_job_at(tmp_path, i) for i in range(3)]
    first_audio = Path(jobs[0].audio_path or "")
    second_audio = Path(jobs[1].audio_path or "")
    kept_audio = Path(jobs[2].audio_path or "")

    result = _policy(FakeRepo(jobs), tmp_path, max_jobs=1).apply()

    assert len(result.expired_jobs) == 2
    assert jobs[0].audio_path is None
    assert jobs[1].audio_path is None
    assert not first_audio.exists()
    assert not second_audio.exists()
    assert kept_audio.exists()


def test_retention_refuses_persisted_path_outside_owned_root(tmp_path: Path) -> None:
    owned = tmp_path / "owned"
    owned.mkdir()
    outside = tmp_path / "outside.log"
    outside.write_text("keep", encoding="utf-8")
    jobs = [_job_at(owned, i) for i in range(2)]
    jobs[0].log_path = str(outside)

    result = _policy(FakeRepo(jobs), owned, max_jobs=1).apply()

    assert outside.read_text(encoding="utf-8") == "keep"
    assert outside not in result.removed_files
    assert jobs[0].audio_path is None
    assert jobs[0].log_path is None


def test_retention_refuses_symlink_escape(tmp_path: Path) -> None:
    owned = tmp_path / "owned"
    owned.mkdir()
    outside = tmp_path / "outside.log"
    outside.write_text("keep", encoding="utf-8")
    jobs = [_job_at(owned, i) for i in range(2)]
    link = owned / "escape.log"
    link.symlink_to(outside)
    jobs[0].log_path = str(link)

    result = _policy(FakeRepo(jobs), owned, max_jobs=1).apply()

    assert outside.read_text(encoding="utf-8") == "keep"
    assert link.is_symlink()
    assert link not in result.removed_files
