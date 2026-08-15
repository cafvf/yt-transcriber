"""Contrato do índice textual derivado do histórico SQLite."""

from __future__ import annotations

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


def _completed_job(tmp_path: Path, *, user_id: int, video_id: str, body: str) -> Job:
    transcripts = tmp_path / "transcripts"
    transcripts.mkdir(exist_ok=True)
    path = transcripts / f"{video_id}.md"
    path.write_text(
        f"# Transcrição — Título seguro\n\n**Canal**: Canal de teste\n\n## Transcrição\n\n{body}",
        encoding="utf-8",
    )
    job = Job.new(
        VideoId(video_id),
        user_id=user_id,
        requested_language="pt",
    )
    job.md_path = str(path)
    _complete(job)
    return job


def test_fts_searches_metadata_transcript_and_summary(tmp_path: Path) -> None:
    repo = SqlAlchemyJobRepository.from_url(f"sqlite:///{tmp_path / 'history.db'}")
    job = _completed_job(
        tmp_path,
        user_id=7,
        video_id="dQw4w9WgXcQ",
        body="A arquitetura hexagonal protege o núcleo.",
    )
    summary_dir = tmp_path / "summaries"
    summary_dir.mkdir()
    (summary_dir / "dQw4w9WgXcQ.summary.md").write_text(
        "Resumo: decisão importante sobre privacidade.", encoding="utf-8"
    )
    repo.save(job)

    hits = repo.search_completed_for_user(user_id=7, query="privacidade", limit=10)

    assert [(hit.video_id, hit.title) for hit in hits] == [("dQw4w9WgXcQ", "Título seguro")]
    assert "privacidade" in hits[0].snippet.casefold()
    with repo._engine.connect() as connection:  # capability evidence; SQLite local may lack FTS5.
        available = connection.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='job_search_fts'")
        ).scalar()
    if available is None:
        pytest.skip("SQLite local sem FTS5; fallback foi exercitado")


def test_fallback_is_user_scoped_ranked_and_sanitized(tmp_path: Path) -> None:
    repo = SqlAlchemyJobRepository.from_url(
        f"sqlite:///{tmp_path / 'history.db'}", enable_fts=False
    )
    own = _completed_job(
        tmp_path,
        user_id=7,
        video_id="dQw4w9WgXcQ",
        body="privacidade privacidade\x00\nconteúdo particular",
    )
    other = _completed_job(
        tmp_path, user_id=8, video_id="aaaaaaaaaaa", body="privacidade secreta de outro usuário"
    )
    repo.save(own)
    repo.save(other)

    hits = repo.search_completed_for_user(user_id=7, query="privacidade", limit=10)

    assert [hit.job_id for hit in hits] == [own.job_id]
    assert "\x00" not in hits[0].snippet
    assert "\n" not in hits[0].snippet


def test_telegram_search_index_omits_private_staging_path(tmp_path: Path) -> None:
    repo = SqlAlchemyJobRepository.from_url(
        f"sqlite:///{tmp_path / 'history.db'}", enable_fts=False
    )
    path = tmp_path / "transcripts" / "telegram.md"
    path.parent.mkdir()
    path.write_text("# Transcrição — Mensagem de voz\n\nconteúdo seguro", encoding="utf-8")
    job = Job.new(
        None,
        user_id=7,
        media_source=MediaSource.telegram_audio("private-file-id"),
    )
    job.md_path = str(path)
    _complete(job)
    repo.save(job)
    repo.save_request_context(
        JobRequestContext(job.job_id, source_locator="/private/staging/secret-audio.ogg")
    )

    assert repo.search_completed_for_user(user_id=7, query="secret-audio", limit=10) == []
    hits = repo.search_completed_for_user(user_id=7, query="Telegram", limit=10)
    assert len(hits) == 1
    assert hits[0].video_id is None
    assert hits[0].source_label == "Telegram (mídia privada)"


def test_refresh_removes_non_completed_document_and_empty_query_is_safe(tmp_path: Path) -> None:
    repo = SqlAlchemyJobRepository.from_url(
        f"sqlite:///{tmp_path / 'history.db'}", enable_fts=False
    )
    job = _completed_job(tmp_path, user_id=7, video_id="dQw4w9WgXcQ", body="termo exclusivo")
    repo.save(job)
    assert repo.search_completed_for_user(user_id=7, query="termo", limit=10)

    # A entidade não permite uma transição terminal reversa; simulamos a remoção
    # por exclusão, que também deve manter o documento derivado consistente.
    repo.delete(job.job_id)
    assert repo.search_completed_for_user(user_id=7, query="termo", limit=10) == []
    assert repo.search_completed_for_user(user_id=7, query="   ", limit=10) == []
