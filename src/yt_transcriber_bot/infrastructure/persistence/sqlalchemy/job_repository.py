"""Implementação SQLAlchemy de ``JobRepository``."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from sqlalchemy import Engine, Table, asc, create_engine, delete, desc, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from yt_transcriber_bot.application.job_request_context import JobRequestContext
from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.media_source import MediaSource, MediaSourceType
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.persistence.sqlalchemy.models import (
    Base,
    JobModel,
)


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
    model.source_title = job.source_title
    model.source_duration_seconds = job.source_duration_seconds
    model.requested_language = job.requested_language
    model.artifact_policy = job.artifact_policy
    model.canonical_transcript_ref = job.canonical_transcript_ref
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
        status=JobStatus.from_persisted(model.status),
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
        source_title=model.source_title,
        source_duration_seconds=model.source_duration_seconds,
        requested_language=model.requested_language,
        artifact_policy=model.artifact_policy,
        speaker_renames=model.renames_dict(),
        canonical_transcript_ref=model.canonical_transcript_ref,
        md_path=model.md_path,
        audio_path=model.audio_path,
        log_path=model.log_path,
    )


class SqlAlchemyJobRepository(JobRepository):
    """Implementação síncrona baseada em SQLAlchemy 2.x."""

    def __init__(self, engine: Engine, *, enable_fts: bool = True) -> None:
        self._engine = engine
        self._session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        _ = enable_fts  # compatibility-only; search has its own adapter.

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

    def save_request_context(self, context: JobRequestContext) -> None:
        with self._session() as session, session.begin():
            model = session.get(JobModel, context.job_id)
            if model is None:
                raise KeyError(f"job inexistente para request context: {context.job_id}")
            model.requested_chat_id = context.delivery_chat_id
            model.source_url = context.source_locator

    def get_request_context(self, job_id: str) -> JobRequestContext | None:
        with self._session() as session:
            model = session.get(JobModel, job_id)
            if model is None:
                return None
            return JobRequestContext(
                job_id=job_id,
                delivery_chat_id=model.requested_chat_id,
                source_locator=model.source_url,
            )

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
        persisted_statuses = {status.value for status in statuses}
        if JobStatus.ACQUIRING in statuses:
            persisted_statuses.add("downloading")
        with self._session() as session:
            stmt = (
                select(JobModel)
                .where(JobModel.status.in_(sorted(persisted_statuses)))
                .order_by(asc(JobModel.requested_at))
            )
            models: Iterable[JobModel] = session.execute(stmt).scalars().all()
            return [_to_entity(m) for m in models]

    def delete(self, job_id: str) -> None:
        with self._session() as session, session.begin():
            session.execute(delete(JobModel).where(JobModel.job_id == job_id))


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
        "canonical_transcript_ref": "TEXT",
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
        legacy_rows = connection.execute(
            text(
                "SELECT job_id, md_path FROM jobs "
                "WHERE (canonical_transcript_ref IS NULL OR canonical_transcript_ref = '') "
                "AND md_path IS NOT NULL AND md_path != ''"
            )
        ).mappings()
        for row in legacy_rows:
            legacy_ref = Path(str(row["md_path"])).stem
            if legacy_ref:
                connection.execute(
                    text(
                        "UPDATE jobs SET canonical_transcript_ref = :reference "
                        "WHERE job_id = :job_id"
                    ),
                    {"reference": legacy_ref, "job_id": row["job_id"]},
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
