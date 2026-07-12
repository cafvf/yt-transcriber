"""Implementação SQLAlchemy de ``JobRepository``."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from sqlalchemy import Engine, Table, asc, create_engine, delete, desc, inspect, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from yt_transcriber_bot.application.ports.history_search import (
    HistorySearchHit,
    HistorySearchRepository,
)
from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.media_source import MediaSource, MediaSourceType
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.persistence.sqlalchemy.models import (
    Base,
    JobModel,
    SearchDocumentModel,
)

_MAX_BACKFILL_JOBS = 200
_MAX_DOCUMENT_CHARS = 200_000
_MAX_SNIPPET_CHARS = 240
_TERM_RE = re.compile(r"[^\W_]+", re.UNICODE)
_TITLE_RE = re.compile(r"^#\s*Transcri(?:ç|c)[aã]o\s+[—-]\s*(.+)$", re.MULTILINE)


def _to_model(job: Job, model: JobModel | None = None) -> JobModel:
    if model is None:
        model = JobModel(job_id=job.job_id)
    # ``Job.__post_init__`` garante a origem padrão para todos os jobs legados.
    media_source = job.media_source
    assert media_source is not None
    model.video_id = job.video_id.value if job.video_id is not None else None
    model.status = job.status.value
    model.requested_by_user_id = job.requested_by_user_id
    model.requested_at = _ensure_aware(job.requested_at)
    model.updated_at = _ensure_aware(job.updated_at)
    model.error_message = job.error_message
    model.config_signature = job.config_signature
    model.source_type = media_source.source_type.value
    model.canonical_reference = media_source.canonical_reference
    model.source_url = job.source_url
    model.source_title = job.source_title
    model.source_duration_seconds = job.source_duration_seconds
    model.requested_chat_id = job.requested_chat_id
    model.requested_language = job.requested_language
    model.artifact_policy = job.artifact_policy
    model.set_renames(job.speaker_renames)
    model.md_path = job.md_path
    model.audio_path = job.audio_path
    model.log_path = job.log_path
    return model


def _ensure_aware(dt: datetime | str) -> datetime:
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _to_entity(model: JobModel) -> Job:
    video_id = VideoId(value=model.video_id) if model.video_id else None
    source_type = MediaSourceType(model.source_type or MediaSourceType.YOUTUBE)
    if source_type is MediaSourceType.YOUTUBE and video_id is None:
        raise ValueError("job YouTube persistido sem video_id")
    return Job(
        job_id=model.job_id,
        video_id=video_id,
        status=JobStatus(model.status),
        requested_by_user_id=model.requested_by_user_id,
        requested_at=_ensure_aware(model.requested_at),
        updated_at=_ensure_aware(model.updated_at),
        error_message=model.error_message,
        config_signature=model.config_signature,
        media_source=MediaSource(
            source_type=source_type,
            canonical_reference=model.canonical_reference
            or (video_id.canonical_url() if video_id is not None else "telegram:legacy"),
        ),
        source_url=model.source_url,
        source_title=model.source_title,
        source_duration_seconds=model.source_duration_seconds,
        requested_chat_id=model.requested_chat_id,
        requested_language=model.requested_language,
        artifact_policy=model.artifact_policy,
        speaker_renames=model.renames_dict(),
        md_path=model.md_path,
        audio_path=model.audio_path,
        log_path=model.log_path,
    )


class SqlAlchemyJobRepository(JobRepository, HistorySearchRepository):
    """Implementação síncrona baseada em SQLAlchemy 2.x."""

    def __init__(self, engine: Engine, *, enable_fts: bool = True) -> None:
        self._engine = engine
        self._session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        self._enable_fts = enable_fts
        self._fts_state: bool | None = None

    @classmethod
    def from_url(cls, url: str, *, enable_fts: bool = True) -> SqlAlchemyJobRepository:
        engine = create_engine(url, future=True)
        Base.metadata.create_all(engine)
        _migrate_jobs_table(engine)
        return cls(engine=engine, enable_fts=enable_fts)

    def _session(self) -> Session:
        return self._session_factory()

    def save(self, job: Job) -> None:
        with self._session() as session, session.begin():
            existing = session.get(JobModel, job.job_id)
            model = _to_model(job, existing)
            session.add(model)
        if job.status is JobStatus.COMPLETED:
            self.refresh_search_index(job.job_id)

    def get_by_id(self, job_id: str) -> Job | None:
        with self._session() as session:
            model = session.get(JobModel, job_id)
            return _to_entity(model) if model else None

    def get_latest_by_video_id(self, video_id: VideoId) -> Job | None:
        with self._session() as session:
            stmt = (
                select(JobModel)
                .where(JobModel.video_id == video_id.value)
                .order_by(desc(JobModel.requested_at))
                .limit(1)
            )
            model = session.execute(stmt).scalar_one_or_none()
            return _to_entity(model) if model else None

    def get_latest_completed_for_user(self, user_id: int) -> Job | None:
        with self._session() as session:
            stmt = (
                select(JobModel)
                .where(JobModel.requested_by_user_id == user_id)
                .where(JobModel.status == JobStatus.COMPLETED.value)
                .order_by(desc(JobModel.updated_at))
                .limit(1)
            )
            model = session.execute(stmt).scalar_one_or_none()
            return _to_entity(model) if model else None

    def list_recent_for_user(self, user_id: int, limit: int) -> list[Job]:
        if limit <= 0:
            return []
        with self._session() as session:
            stmt = (
                select(JobModel)
                .where(JobModel.requested_by_user_id == user_id)
                .order_by(desc(JobModel.requested_at))
                .limit(limit)
            )
            models: Iterable[JobModel] = session.execute(stmt).scalars().all()
            return [_to_entity(m) for m in models]

    def list_completed_oldest_first(self) -> list[Job]:
        with self._session() as session:
            stmt = (
                select(JobModel)
                .where(JobModel.status == JobStatus.COMPLETED.value)
                .order_by(asc(JobModel.updated_at))
            )
            models: Iterable[JobModel] = session.execute(stmt).scalars().all()
            return [_to_entity(m) for m in models]

    def list_by_statuses_oldest_first(self, statuses: set[JobStatus]) -> list[Job]:
        if not statuses:
            return []
        with self._session() as session:
            stmt = (
                select(JobModel)
                .where(JobModel.status.in_([status.value for status in statuses]))
                .order_by(asc(JobModel.requested_at))
            )
            models: Iterable[JobModel] = session.execute(stmt).scalars().all()
            return [_to_entity(m) for m in models]

    def delete(self, job_id: str) -> None:
        with self._session() as session, session.begin():
            session.execute(delete(JobModel).where(JobModel.job_id == job_id))
            session.execute(delete(SearchDocumentModel).where(SearchDocumentModel.job_id == job_id))
            if self._fts_is_available(session):
                session.execute(
                    text("DELETE FROM job_search_fts WHERE job_id = :job_id"), {"job_id": job_id}
                )

    def refresh_search_index(self, job_id: str) -> None:
        """Atualiza um documento usando apenas artefatos explicitamente ligados ao job."""
        with self._session() as session, session.begin():
            model = session.get(JobModel, job_id)
            if model is None or model.status != JobStatus.COMPLETED.value:
                session.execute(
                    delete(SearchDocumentModel).where(SearchDocumentModel.job_id == job_id)
                )
                return
            self._upsert_search_document(session, model)

    def search_completed_for_user(
        self, *, user_id: int, query: str, limit: int
    ) -> list[HistorySearchHit]:
        if limit <= 0 or not _query_terms(query):
            return []
        self._backfill_user_documents(user_id)
        with self._session() as session:
            if self._fts_is_available(session):
                try:
                    hits = self._search_fts(session, user_id=user_id, query=query, limit=limit)
                    if hits is not None:
                        return hits
                except SQLAlchemyError:
                    # FTS é uma otimização opcional: query/capacidade falha -> fallback portátil.
                    self._fts_state = False
            return self._search_fallback(session, user_id=user_id, query=query, limit=limit)

    def _backfill_user_documents(self, user_id: int) -> None:
        """Backfill lazy e limitado; não varre artefatos fora do histórico do usuário."""
        with self._session() as session, session.begin():
            models = session.execute(
                select(JobModel)
                .where(JobModel.requested_by_user_id == user_id)
                .where(JobModel.status == JobStatus.COMPLETED.value)
                .order_by(desc(JobModel.updated_at))
                .limit(_MAX_BACKFILL_JOBS)
            ).scalars()
            for model in models:
                self._upsert_search_document(session, model)

    def _upsert_search_document(self, session: Session, model: JobModel) -> None:
        title, content = _document_from_artifacts(model)
        existing = session.get(SearchDocumentModel, model.job_id)
        if existing is None:
            existing = SearchDocumentModel(
                job_id=model.job_id,
                user_id=model.requested_by_user_id,
                title=title,
                content=content,
                updated_at=_ensure_aware(model.updated_at),
            )
            session.add(existing)
        else:
            existing.user_id = model.requested_by_user_id
            existing.title = title
            existing.content = content
            existing.updated_at = _ensure_aware(model.updated_at)
        if self._fts_is_available(session):
            session.execute(
                text("DELETE FROM job_search_fts WHERE job_id = :job_id"), {"job_id": model.job_id}
            )
            session.execute(
                text(
                    "INSERT INTO job_search_fts (job_id, user_id, title, content) "
                    "VALUES (:job_id, :user_id, :title, :content)"
                ),
                {
                    "job_id": model.job_id,
                    "user_id": model.requested_by_user_id,
                    "title": title,
                    "content": content,
                },
            )

    def _fts_is_available(self, session: Session) -> bool:
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
        except SQLAlchemyError:
            self._fts_state = False
        else:
            self._fts_state = True
        return self._fts_state

    def _search_fts(
        self, session: Session, *, user_id: int, query: str, limit: int
    ) -> list[HistorySearchHit] | None:
        match = _fts_query(query)
        if not match:
            return []
        rows = (
            session.execute(
                text(
                    "SELECT d.job_id, d.title, j.video_id, j.source_type, j.updated_at, d.content "
                    "FROM job_search_fts f "
                    "JOIN job_search_documents d ON d.job_id = f.job_id "
                    "JOIN jobs j ON j.job_id = d.job_id "
                    "WHERE f.user_id = :user_id AND job_search_fts MATCH :match "
                    "AND j.status = :completed "
                    "ORDER BY bm25(job_search_fts), j.updated_at DESC, d.job_id DESC LIMIT :limit"
                ),
                {
                    "user_id": user_id,
                    "match": match,
                    "completed": JobStatus.COMPLETED.value,
                    "limit": limit,
                },
            )
            .mappings()
            .all()
        )
        return [_hit_from_row(row, query) for row in rows]

    def _search_fallback(
        self, session: Session, *, user_id: int, query: str, limit: int
    ) -> list[HistorySearchHit]:
        terms = _query_terms(query)
        statement = (
            select(SearchDocumentModel, JobModel)
            .join(JobModel, JobModel.job_id == SearchDocumentModel.job_id)
            .where(SearchDocumentModel.user_id == user_id)
            .where(JobModel.status == JobStatus.COMPLETED.value)
        )
        for term in terms:
            statement = statement.where(
                (SearchDocumentModel.title.ilike(f"%{term}%"))
                | (SearchDocumentModel.content.ilike(f"%{term}%"))
            )
        candidates = session.execute(
            statement.order_by(desc(JobModel.updated_at), desc(SearchDocumentModel.job_id)).limit(
                _MAX_BACKFILL_JOBS
            )
        ).all()
        ranked = sorted(
            candidates,
            key=lambda pair: (
                _fallback_score(pair[0], terms),
                _ensure_aware(pair[1].updated_at),
                pair[0].job_id,
            ),
            reverse=True,
        )[:limit]
        return [
            HistorySearchHit(
                job_id=document.job_id,
                title=document.title,
                video_id=job.video_id,
                source_label=_source_label(job.source_type),
                completed_at=_ensure_aware(job.updated_at),
                snippet=_snippet(document.content, query),
            )
            for document, job in ranked
        ]


def _document_from_artifacts(model: JobModel) -> tuple[str, str]:
    """Monta texto derivado de metadados e artefatos conhecidos de um job.

    Erros ou artefatos ausentes não impedem a busca por metadados e nunca são
    propagados para o comando. Caminhos vêm do próprio job; não há descoberta
    por diretórios nem leitura de logs.
    """
    markdown = _read_artifact(model.md_path)
    title_match = _TITLE_RE.search(markdown)
    title = _safe_text(title_match.group(1) if title_match else "")
    if not title:
        title = Path(model.md_path).stem if model.md_path else _source_label(model.source_type)
    metadata = " ".join(
        value
        for value in (
            title,
            _source_label(model.source_type),
            model.video_id or "",
            model.source_url or "" if model.source_type == MediaSourceType.YOUTUBE.value else "",
            model.requested_language or "",
            " ".join(model.renames_dict().values()),
        )
        if value
    )
    summary = "\n".join(_read_artifact(path) for path in _summary_candidates(model.md_path))
    content = _safe_text("\n".join(part for part in (metadata, markdown, summary) if part))
    return _truncate(title, 300), _truncate(content, _MAX_DOCUMENT_CHARS)


def _summary_candidates(md_path: str | None) -> tuple[Path, ...]:
    if not md_path:
        return ()
    transcript = Path(md_path)
    filename = f"{transcript.stem}.summary.md"
    # O primeiro candidato permite instalações customizadas; o segundo segue
    # a estrutura padrão data/transcripts -> data/summaries.
    candidates = (transcript.with_name(filename), transcript.parent.parent / "summaries" / filename)
    return tuple(dict.fromkeys(candidates))


def _read_artifact(path: str | Path | None) -> str:
    if path is None:
        return ""
    try:
        candidate = Path(path)
        if not candidate.is_file():
            return ""
        return candidate.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _query_terms(query: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(match.group(0).casefold() for match in _TERM_RE.finditer(query)))


def _fts_query(query: str) -> str:
    # Cada termo é uma frase citada: operadores FTS fornecidos pelo usuário
    # não alteram a expressão e caracteres especiais não são interpolados.
    return " AND ".join(f'"{term.replace(chr(34), "")}"' for term in _query_terms(query))


def _fallback_score(document: SearchDocumentModel, terms: tuple[str, ...]) -> int:
    haystack = f"{document.title}\n{document.content}".casefold()
    title = document.title.casefold()
    return sum(haystack.count(term) + (3 * title.count(term)) for term in terms)


def _hit_from_row(row: object, query: str) -> HistorySearchHit:
    values = row  # typed Mapping at the SQLAlchemy boundary
    return HistorySearchHit(
        job_id=str(values["job_id"]),  # type: ignore[index]
        title=str(values["title"]),  # type: ignore[index]
        video_id=str(values["video_id"]) if values["video_id"] else None,  # type: ignore[index]
        source_label=_source_label(str(values["source_type"])),  # type: ignore[index]
        completed_at=_ensure_aware(values["updated_at"]),  # type: ignore[index]
        snippet=_snippet(str(values["content"]), query),  # type: ignore[index]
    )


def _source_label(source_type: str) -> str:
    if source_type == MediaSourceType.TELEGRAM_AUDIO.value:
        return "Telegram (mídia privada)"
    return "YouTube"


def _snippet(content: str, query: str) -> str:
    cleaned = _safe_text(content)
    terms = _query_terms(query)
    position = min(
        (cleaned.casefold().find(term) for term in terms if term in cleaned.casefold()), default=0
    )
    start = max(0, position - 80)
    end = min(len(cleaned), start + _MAX_SNIPPET_CHARS)
    prefix = "…" if start else ""
    suffix = "…" if end < len(cleaned) else ""
    return f"{prefix}{cleaned[start:end].strip()}{suffix}"


def _safe_text(value: str) -> str:
    without_controls = "".join(char if char.isprintable() else " " for char in value)
    return " ".join(without_controls.split())


def _truncate(value: str, length: int) -> str:
    return value[:length]


def _migrate_jobs_table(engine: Engine) -> None:
    inspector = inspect(engine)
    if "jobs" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("jobs")}
    additive_columns = {
        "source_type": "VARCHAR(32) NOT NULL DEFAULT 'youtube'",
        "canonical_reference": "TEXT",
        "source_url": "TEXT",
        "source_title": "TEXT",
        "source_duration_seconds": "INTEGER",
        "requested_chat_id": "INTEGER",
        "requested_language": "VARCHAR(16)",
        "artifact_policy": "VARCHAR(32) NOT NULL DEFAULT 'audio+markdown'",
    }
    with engine.begin() as connection:
        for column_name, ddl in additive_columns.items():
            if column_name in existing:
                continue
            connection.execute(text(f"ALTER TABLE jobs ADD COLUMN {column_name} {ddl}"))
        connection.execute(
            text(
                "UPDATE jobs SET source_type = 'youtube' "
                "WHERE source_type IS NULL OR source_type = ''"
            )
        )
        connection.execute(
            text(
                "UPDATE jobs SET canonical_reference = "
                "'https://www.youtube.com/watch?v=' || video_id "
                "WHERE canonical_reference IS NULL OR canonical_reference = ''"
            )
        )
    _make_video_id_nullable_if_needed(engine)


def _make_video_id_nullable_if_needed(engine: Engine) -> None:
    """Reconstrói apenas SQLite legado, cuja coluna original era NOT NULL."""
    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    columns = inspector.get_columns("jobs")
    video_column = next((column for column in columns if column["name"] == "video_id"), None)
    if video_column is None or not video_column["nullable"]:
        if video_column is None:
            return
    else:
        return
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE jobs RENAME TO jobs_legacy_video_id"))
        legacy_indexes = inspect(connection).get_indexes("jobs_legacy_video_id")
        for index in legacy_indexes:
            connection.execute(text(f'DROP INDEX "{index["name"]}"'))
        Base.metadata.create_all(
            connection, tables=[cast(Table, JobModel.__table__)], checkfirst=False
        )
        legacy_columns = {
            column["name"] for column in inspect(connection).get_columns("jobs_legacy_video_id")
        }
        shared_columns = [
            column.name for column in JobModel.__table__.columns if column.name in legacy_columns
        ]
        joined_columns = ", ".join(shared_columns)
        connection.execute(
            text(
                f"INSERT INTO jobs ({joined_columns}) "
                f"SELECT {joined_columns} FROM jobs_legacy_video_id"
            )
        )
        connection.execute(text("DROP TABLE jobs_legacy_video_id"))
