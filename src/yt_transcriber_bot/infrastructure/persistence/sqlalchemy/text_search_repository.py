from __future__ import annotations

import re
from datetime import UTC, datetime

from sqlalchemy import Engine, delete, desc, inspect, select, text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from yt_transcriber_bot.application.ports.text_search import (
    HistorySearchHit,
    SearchDocument,
    TextSearchIndex,
    TextSearchQuery,
)
from yt_transcriber_bot.domain.entities.job import JobStatus
from yt_transcriber_bot.domain.value_objects.media_source import MediaSourceType
from yt_transcriber_bot.infrastructure.persistence.sqlalchemy.models import (
    Base,
    JobModel,
    SearchDocumentModel,
)

_MAX_CANDIDATES = 200
_MAX_SNIPPET_CHARS = 240
_TERM_RE = re.compile(r"[^\W_]+", re.UNICODE)


def _aware(value: datetime | str) -> datetime:
    dt = datetime.fromisoformat(value) if isinstance(value, str) else value
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


class SqlAlchemyTextSearchRepository(TextSearchIndex, TextSearchQuery):
    def __init__(self, engine: Engine, *, enable_fts: bool = True) -> None:
        self._engine = engine
        self._session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        self._enable_fts = enable_fts
        self._fts_state: bool | None = None
        _migrate_search_documents_table(engine)

    @classmethod
    def from_url(cls, url: str, *, enable_fts: bool = True) -> SqlAlchemyTextSearchRepository:
        from sqlalchemy import create_engine

        engine = create_engine(url, future=True)
        Base.metadata.create_all(engine)
        return cls(engine, enable_fts=enable_fts)

    def _session(self) -> Session:
        return self._session_factory()

    def replace(self, document: SearchDocument) -> None:
        with self._session() as session, session.begin():
            job = session.get(JobModel, document.job_id)
            if (
                job is None
                or job.status != JobStatus.COMPLETED.value
                or not job.canonical_transcript_ref
                or job.canonical_transcript_ref != document.canonical_transcript_ref
            ):
                self._remove(session, document.job_id)
                return
            model = session.get(SearchDocumentModel, document.job_id)
            if model is None:
                model = SearchDocumentModel(job_id=document.job_id)
                session.add(model)
            model.user_id = document.user_id
            model.canonical_transcript_ref = document.canonical_transcript_ref
            model.title = document.title
            model.content = document.content
            model.updated_at = _aware(document.updated_at)
            self._replace_fts(session, document)

    def remove(self, job_id: str) -> None:
        with self._session() as session, session.begin():
            self._remove(session, job_id)

    def _remove(self, session: Session, job_id: str) -> None:
        session.execute(delete(SearchDocumentModel).where(SearchDocumentModel.job_id == job_id))
        if self._fts_available(session):
            session.execute(
                text("DELETE FROM job_search_fts WHERE job_id = :job_id"),
                {"job_id": job_id},
            )

    def search_completed_for_user(
        self, *, user_id: int, query: str, limit: int
    ) -> list[HistorySearchHit]:
        if limit <= 0 or not _terms(query):
            return []
        with self._session() as session:
            if self._fts_available(session):
                try:
                    return self._search_fts(session, user_id=user_id, query=query, limit=limit)
                except SQLAlchemyError:
                    self._fts_state = False
            return self._search_fallback(session, user_id=user_id, query=query, limit=limit)

    def _fts_available(self, session: Session) -> bool:
        if not self._enable_fts:
            return False
        if self._fts_state is not None:
            return self._fts_state
        try:
            session.execute(
                text(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS job_search_fts "
                    "USING fts5(job_id UNINDEXED, user_id UNINDEXED, title, content)"
                )
            )
            self._fts_state = True
        except SQLAlchemyError:
            self._fts_state = False
        return self._fts_state

    def _replace_fts(self, session: Session, document: SearchDocument) -> None:
        if not self._fts_available(session):
            return
        session.execute(
            text("DELETE FROM job_search_fts WHERE job_id = :job_id"),
            {"job_id": document.job_id},
        )
        session.execute(
            text(
                "INSERT INTO job_search_fts (job_id, user_id, title, content) "
                "VALUES (:job_id, :user_id, :title, :content)"
            ),
            {
                "job_id": document.job_id,
                "user_id": document.user_id,
                "title": document.title,
                "content": document.content,
            },
        )

    def _search_fts(
        self, session: Session, *, user_id: int, query: str, limit: int
    ) -> list[HistorySearchHit]:
        rows = (
            session.execute(
                text(
                    "SELECT d.job_id, d.title, j.video_id, j.source_type, j.updated_at, d.content "
                    "FROM job_search_fts f "
                    "JOIN job_search_documents d ON d.job_id=f.job_id "
                    "JOIN jobs j ON j.job_id=d.job_id "
                    "WHERE f.user_id=:user_id AND job_search_fts MATCH :query "
                    "AND j.status=:completed "
                    "AND d.canonical_transcript_ref=j.canonical_transcript_ref "
                    "ORDER BY bm25(job_search_fts), j.updated_at DESC "
                    "LIMIT :limit"
                ),
                {
                    "user_id": user_id,
                    "query": _fts_query(query),
                    "completed": JobStatus.COMPLETED.value,
                    "limit": limit,
                },
            )
            .mappings()
            .all()
        )
        return [_row_hit(row, query) for row in rows]

    def _search_fallback(
        self, session: Session, *, user_id: int, query: str, limit: int
    ) -> list[HistorySearchHit]:
        terms = _terms(query)
        stmt = (
            select(SearchDocumentModel, JobModel)
            .join(JobModel, JobModel.job_id == SearchDocumentModel.job_id)
            .where(SearchDocumentModel.user_id == user_id)
            .where(JobModel.status == JobStatus.COMPLETED.value)
            .where(
                SearchDocumentModel.canonical_transcript_ref == JobModel.canonical_transcript_ref
            )
        )
        for term in terms:
            stmt = stmt.where(
                SearchDocumentModel.title.ilike(f"%{term}%")
                | SearchDocumentModel.content.ilike(f"%{term}%")
            )
        candidates = list(
            session.execute(stmt.order_by(desc(JobModel.updated_at)).limit(_MAX_CANDIDATES)).all()
        )
        candidates.sort(
            key=lambda pair: (
                _score(pair[0], terms),
                _aware(pair[1].updated_at),
                pair[0].job_id,
            ),
            reverse=True,
        )
        return [
            HistorySearchHit(
                job_id=document.job_id,
                title=document.title,
                video_id=job.video_id,
                source_label=_source_label(job.source_type),
                completed_at=_aware(job.updated_at),
                snippet=_snippet(document.content, query),
            )
            for document, job in candidates[:limit]
        ]


def _terms(query: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(match.group(0).casefold() for match in _TERM_RE.finditer(query)))


def _fts_query(query: str) -> str:
    return " AND ".join(f'"{term}"' for term in _terms(query))


def _score(document: SearchDocumentModel, terms: tuple[str, ...]) -> int:
    all_text = f"{document.title}\n{document.content}".casefold()
    title = document.title.casefold()
    return sum(all_text.count(term) + 3 * title.count(term) for term in terms)


def _row_hit(row: RowMapping, query: str) -> HistorySearchHit:
    return HistorySearchHit(
        job_id=str(row["job_id"]),
        title=str(row["title"]),
        video_id=str(row["video_id"]) if row["video_id"] else None,
        source_label=_source_label(str(row["source_type"])),
        completed_at=_aware(row["updated_at"]),
        snippet=_snippet(str(row["content"]), query),
    )


def _source_label(source_type: str) -> str:
    return (
        "Telegram (mídia privada)"
        if source_type == MediaSourceType.TELEGRAM_AUDIO.value
        else "YouTube"
    )


def _snippet(content: str, query: str) -> str:
    cleaned = " ".join("".join(c if c.isprintable() else " " for c in content).split())
    folded = cleaned.casefold()
    positions = [folded.find(term) for term in _terms(query) if term in folded]
    position = min(positions, default=0)
    start = max(0, position - 80)
    end = min(len(cleaned), start + _MAX_SNIPPET_CHARS)
    return ("…" if start else "") + cleaned[start:end].strip() + ("…" if end < len(cleaned) else "")


def _migrate_search_documents_table(engine: Engine) -> None:
    inspector = inspect(engine)
    if "job_search_documents" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("job_search_documents")}
    if "canonical_transcript_ref" in columns:
        return
    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE job_search_documents ADD COLUMN canonical_transcript_ref TEXT")
        )
        connection.execute(
            text(
                "UPDATE job_search_documents SET canonical_transcript_ref=("
                "SELECT canonical_transcript_ref FROM jobs "
                "WHERE jobs.job_id=job_search_documents.job_id"
                ") WHERE canonical_transcript_ref IS NULL"
            )
        )
