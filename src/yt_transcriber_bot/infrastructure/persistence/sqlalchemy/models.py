"""Modelos SQLAlchemy para persistência de jobs."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class JobModel(Base):
    __tablename__ = "jobs"

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    video_id: Mapped[str | None] = mapped_column(String(11), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    requested_by_user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_signature: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="youtube")
    canonical_reference: Mapped[str] = mapped_column(Text, nullable=False)
    # Compatibilidade física: ``source_url`` guarda o locator opaco da
    # requisição, não a identidade canônica da mídia.
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Contexto de entrega da aplicação; deliberadamente não é campo de Job.
    requested_chat_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requested_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    artifact_policy: Mapped[str] = mapped_column(
        String(32), nullable=False, default="audio+markdown"
    )
    canonical_transcript_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    speaker_renames_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    md_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    log_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    def renames_dict(self) -> dict[str, str]:
        if not self.speaker_renames_json:
            return {}
        loaded = json.loads(self.speaker_renames_json)
        if not isinstance(loaded, dict):
            return {}
        return {str(k): str(v) for k, v in loaded.items()}

    def set_renames(self, mapping: dict[str, str]) -> None:
        self.speaker_renames_json = json.dumps(mapping, ensure_ascii=False)


class SearchDocumentModel(Base):
    __tablename__ = "job_search_documents"

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
