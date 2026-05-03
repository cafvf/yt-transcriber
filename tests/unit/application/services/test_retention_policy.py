"""Testes da política de retenção FIFO."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from yt_transcriber_bot.application.services.retention_policy import (
    RetentionPolicy,
)
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class FakeRepo:
    def __init__(self, jobs: list[Job]) -> None:
        self.jobs = jobs

    def list_completed_oldest_first(self) -> list[Job]:
        return list(self.jobs)

    # restantes não são chamadas pela RetentionPolicy
    def save(self, job: Job) -> None: ...
    def get_by_id(self, job_id: str) -> Job | None: ...
    def get_latest_by_video_id(self, video_id: VideoId) -> Job | None: ...
    def get_latest_completed_for_user(self, user_id: int) -> Job | None: ...
    def list_recent_for_user(self, user_id: int, limit: int) -> list[Job]: ...
    def delete(self, job_id: str) -> None: ...


def _job_at(tmp_path: Path, idx: int) -> Job:
    """Cria job concluído com arquivos físicos no tmp_path."""
    audio = tmp_path / f"audio_{idx}.ogg"
    audio.write_bytes(b"OggS_data")
    log = tmp_path / f"job_{idx}.log"
    log.write_text("log content")
    md = tmp_path / f"transcript_{idx}.md"
    md.write_text("# legacy")

    job = Job.new(VideoId("d" + "Q" * 10), 42)
    # Setar timestamps progressivos (idx 0 é o mais antigo)
    base = datetime(2024, 1, 1, tzinfo=UTC)
    object.__setattr__(job, "requested_at", base + timedelta(hours=idx))
    object.__setattr__(job, "updated_at", base + timedelta(hours=idx))
    job.transition_to(JobStatus.COMPLETED)
    job.audio_path = str(audio)
    job.log_path = str(log)
    job.md_path = str(md)
    return job


def test_no_expiration_when_under_limit(tmp_path: Path) -> None:
    jobs = [_job_at(tmp_path, i) for i in range(3)]
    repo = FakeRepo(jobs)
    policy = RetentionPolicy(repo, max_volatile_jobs=5)  # type: ignore[arg-type]
    result = policy.apply()
    assert result.expired_jobs == ()
    assert result.removed_files == ()
    # Todos os arquivos ainda existem
    for j in jobs:
        assert Path(j.audio_path or "").exists()
        assert Path(j.log_path or "").exists()


def test_expires_oldest_when_over_limit(tmp_path: Path) -> None:
    jobs = [_job_at(tmp_path, i) for i in range(7)]
    repo = FakeRepo(jobs)
    policy = RetentionPolicy(repo, max_volatile_jobs=5)  # type: ignore[arg-type]
    result = policy.apply()
    # Os 2 mais antigos foram expirados
    assert len(result.expired_jobs) == 2
    assert result.expired_jobs[0] == jobs[0].job_id
    assert result.expired_jobs[1] == jobs[1].job_id
    # Audios e logs dos 2 mais antigos foram removidos
    assert not Path(jobs[0].audio_path or "").exists()
    assert not Path(jobs[0].log_path or "").exists()
    assert not Path(jobs[1].audio_path or "").exists()
    # Os 5 mais recentes ainda existem
    for j in jobs[2:]:
        assert Path(j.audio_path or "").exists()


def test_md_is_preserved(tmp_path: Path) -> None:
    """MDs ficam como legado mesmo após expurgo."""
    jobs = [_job_at(tmp_path, i) for i in range(7)]
    repo = FakeRepo(jobs)
    policy = RetentionPolicy(repo, max_volatile_jobs=5)  # type: ignore[arg-type]
    policy.apply()
    # MDs de TODOS os jobs (inclusive os expirados) ainda existem
    for j in jobs:
        assert Path(j.md_path or "").exists()


def test_handles_missing_files_gracefully(tmp_path: Path) -> None:
    jobs = [_job_at(tmp_path, i) for i in range(7)]
    # Apaga manualmente o áudio do job 0 antes da política rodar
    Path(jobs[0].audio_path or "").unlink()
    repo = FakeRepo(jobs)
    policy = RetentionPolicy(repo, max_volatile_jobs=5)  # type: ignore[arg-type]
    result = policy.apply()
    # Não deve crashar; expira normalmente
    assert len(result.expired_jobs) == 2


def test_invalid_max_jobs() -> None:
    repo = FakeRepo([])
    with pytest.raises(ValueError, match="max_volatile_jobs"):
        RetentionPolicy(repo, max_volatile_jobs=0)  # type: ignore[arg-type]


def test_max_jobs_one(tmp_path: Path) -> None:
    """Caso extremo: max=1 → todos exceto o último são expirados."""
    jobs = [_job_at(tmp_path, i) for i in range(3)]
    repo = FakeRepo(jobs)
    policy = RetentionPolicy(repo, max_volatile_jobs=1)  # type: ignore[arg-type]
    result = policy.apply()
    assert len(result.expired_jobs) == 2
    # Apenas o último (idx=2) tem áudio
    assert Path(jobs[-1].audio_path or "").exists()
    assert not Path(jobs[0].audio_path or "").exists()
    assert not Path(jobs[1].audio_path or "").exists()
