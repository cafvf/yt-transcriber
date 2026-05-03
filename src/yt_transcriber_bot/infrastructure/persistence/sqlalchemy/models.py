"""Modelos SQLAlchemy para persistência de jobs."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarativa do SQLAlchemy."""


class JobModel(Base):
    """Tabela ``jobs``: 1:1 com a entidade ``Job``."""

    __tablename__ = "jobs"

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    video_id: Mapped[str] = mapped_column(String(11), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    requested_by_user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_signature: Mapped[str] = mapped_column(String(64), nullable=False, default="")
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
