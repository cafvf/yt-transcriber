"""Testes da política de retenção FIFO."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from yt_transcriber_bot.application.job_request_context import JobRequestContext
from yt_transcriber_bot.application.services.retention_policy import RetentionPolicy
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.media_source import MediaSource
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.persistence.filesystem.owned_artifact_cleanup import (
    FilesystemOwnedArtifactCleanup,
)


class FakeRepo:
    def __init__(
        self,
        jobs: list[Job],
        contexts: dict[str, JobRequestContext] | None = None,
    ) -> None:
        self.jobs = jobs
        self.contexts = dict(contexts or {})

    def list_completed_oldest_first(self) -> list[Job]:
        return list(self.jobs)

    def list_by_statuses_oldest_first(self, statuses: set[JobStatus]) -> list[Job]:
        return [job for job in self.jobs if job.status in statuses]

    def save_request_context(self, context: JobRequestContext) -> None:
        self.contexts[context.job_id] = context

    def get_request_context(self, job_id: str) -> JobRequestContext | None:
        return self.contexts.get(job_id)

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
        artifact_cleanup=FilesystemOwnedArtifactCleanup((root,)),
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
            FakeRepo([]),
            artifact_cleanup=FilesystemOwnedArtifactCleanup((tmp_path,)),
            max_volatile_jobs=0,
        )


def test_requires_explicit_owned_root() -> None:
    with pytest.raises(ValueError, match="owned_roots"):
        FilesystemOwnedArtifactCleanup(())


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


def test_retention_preserves_canonical_snapshot_reference_and_markdown(tmp_path: Path) -> None:
    jobs = [_job_at(tmp_path, i) for i in range(2)]
    canonical = tmp_path / "canonical-0.json"
    canonical.write_text('{"schema_version": 2}', encoding="utf-8")
    jobs[0].canonical_transcript_ref = "canonical-0"

    _policy(FakeRepo(jobs), tmp_path, max_jobs=1).apply()

    assert jobs[0].canonical_transcript_ref == "canonical-0"
    assert canonical.exists()
    assert Path(jobs[0].md_path or "").exists()


def test_retention_clears_missing_volatile_references(tmp_path: Path) -> None:
    jobs = [_job_at(tmp_path, i) for i in range(2)]
    Path(jobs[0].audio_path or "").unlink()
    Path(jobs[0].log_path or "").unlink()

    _policy(FakeRepo(jobs), tmp_path, max_jobs=1).apply()

    assert jobs[0].audio_path is None
    assert jobs[0].log_path is None
    assert jobs[0].md_path is not None


def test_retention_clears_telegram_source_context_after_owned_source_removal(
    tmp_path: Path,
) -> None:
    source = tmp_path / "telegram-source.ogg"
    source.write_bytes(b"source")
    audio = tmp_path / "telegram-converted.ogg"
    audio.write_bytes(b"converted")
    log = tmp_path / "telegram.log"
    log.write_text("log", encoding="utf-8")
    md = tmp_path / "telegram.md"
    md.write_text("# transcript", encoding="utf-8")
    job = Job.new(
        None,
        42,
        media_source=MediaSource.telegram_audio("private-file-id"),
        source_duration_seconds=10,
    )
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
    context = JobRequestContext(job.job_id, delivery_chat_id=10, source_locator=str(source))
    newer = _job_at(tmp_path, 2)
    repo = FakeRepo([job, newer], {job.job_id: context})

    _policy(repo, tmp_path, max_jobs=1).apply()

    assert not source.exists()
    assert repo.contexts[job.job_id].source_locator is None
    assert job.audio_path is None
    assert job.log_path is None
    assert job.md_path == str(md)
