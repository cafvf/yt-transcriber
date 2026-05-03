"""Implementação SQLAlchemy de ``JobRepository``."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy import Engine, asc, create_engine, delete, desc, select
from sqlalchemy.orm import Session, sessionmaker

from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.persistence.sqlalchemy.models import (
    Base,
    JobModel,
)


def _to_model(job: Job, model: JobModel | None = None) -> JobModel:
    if model is None:
        model = JobModel(job_id=job.job_id)
    model.video_id = job.video_id.value
    model.status = job.status.value
    model.requested_by_user_id = job.requested_by_user_id
    model.requested_at = _ensure_aware(job.requested_at)
    model.updated_at = _ensure_aware(job.updated_at)
    model.error_message = job.error_message
    model.config_signature = job.config_signature
    model.set_renames(job.speaker_renames)
    model.md_path = job.md_path
    model.audio_path = job.audio_path
    model.log_path = job.log_path
    return model


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _to_entity(model: JobModel) -> Job:
    return Job(
        job_id=model.job_id,
        video_id=VideoId(value=model.video_id),
        status=JobStatus(model.status),
        requested_by_user_id=model.requested_by_user_id,
        requested_at=_ensure_aware(model.requested_at),
        updated_at=_ensure_aware(model.updated_at),
        error_message=model.error_message,
        config_signature=model.config_signature,
        speaker_renames=model.renames_dict(),
        md_path=model.md_path,
        audio_path=model.audio_path,
        log_path=model.log_path,
    )


class SqlAlchemyJobRepository(JobRepository):
    """Implementação síncrona baseada em SQLAlchemy 2.x."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    @classmethod
    def from_url(cls, url: str) -> SqlAlchemyJobRepository:
        engine = create_engine(url, future=True)
        Base.metadata.create_all(engine)
        return cls(engine=engine)

    def _session(self) -> Session:
        return self._session_factory()

    def save(self, job: Job) -> None:
        with self._session() as session, session.begin():
            existing = session.get(JobModel, job.job_id)
            model = _to_model(job, existing)
            session.add(model)

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

    def delete(self, job_id: str) -> None:
        with self._session() as session, session.begin():
            session.execute(delete(JobModel).where(JobModel.job_id == job_id))
