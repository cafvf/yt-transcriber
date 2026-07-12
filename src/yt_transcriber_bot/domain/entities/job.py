"""Entidade ``Job`` — agrega o ciclo de vida de um pedido de transcrição."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from yt_transcriber_bot.domain.value_objects.media_source import MediaSource, MediaSourceType
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class JobStatus(StrEnum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    CONVERTING = "converting"
    TRANSCRIBING = "transcribing"
    DIARIZING = "diarizing"
    RENDERING = "rendering"
    DELIVERING = "delivering"
    COMPLETED = "completed"
    DELIVERY_FAILED = "delivery_failed"
    FAILED = "failed"
    CANCELLED = "cancelled"


_TERMINAL_STATES = frozenset(
    {JobStatus.COMPLETED, JobStatus.DELIVERY_FAILED, JobStatus.FAILED, JobStatus.CANCELLED}
)


@dataclass
class Job:
    """Representa um trabalho de transcrição."""

    job_id: str
    video_id: VideoId | None
    status: JobStatus
    requested_by_user_id: int
    requested_at: datetime
    updated_at: datetime
    error_message: str | None = None
    config_signature: str = ""
    media_source: MediaSource | None = None
    source_url: str | None = None
    source_title: str | None = None
    source_duration_seconds: int | None = None
    requested_chat_id: int | None = None
    requested_language: str | None = None
    artifact_policy: str = "audio+markdown"
    speaker_renames: dict[str, str] = field(default_factory=dict)
    md_path: str | None = None
    audio_path: str | None = None
    log_path: str | None = None

    def __post_init__(self) -> None:
        """Valida a identidade da origem sem acoplar o agregado ao transporte."""
        if self.media_source is None:
            if self.video_id is None:
                raise ValueError("video_id é obrigatório quando a origem não é informada")
            self.media_source = MediaSource.youtube(self.video_id)
        if self.media_source.source_type is MediaSourceType.YOUTUBE:
            if self.video_id is None:
                raise ValueError("video_id é obrigatório para origem YouTube")
            if self.media_source.canonical_reference != self.video_id.canonical_url():
                raise ValueError("A referência canônica YouTube deve corresponder ao video_id")

    @classmethod
    def new(
        cls,
        video_id: VideoId | None,
        user_id: int,
        config_signature: str = "",
        *,
        source_url: str | None = None,
        requested_chat_id: int | None = None,
        requested_language: str | None = None,
        artifact_policy: str = "audio+markdown",
        media_source: MediaSource | None = None,
        source_title: str | None = None,
        source_duration_seconds: int | None = None,
    ) -> Job:
        now = datetime.now(UTC)
        return cls(
            job_id=str(uuid.uuid4()),
            video_id=video_id,
            status=JobStatus.PENDING,
            requested_by_user_id=user_id,
            requested_at=now,
            updated_at=now,
            config_signature=config_signature,
            media_source=media_source or (MediaSource.youtube(video_id) if video_id else None),
            source_url=source_url,
            source_title=source_title,
            source_duration_seconds=source_duration_seconds,
            requested_chat_id=requested_chat_id,
            requested_language=requested_language,
            artifact_policy=artifact_policy,
        )

    def transition_to(self, new_status: JobStatus, *, error: str | None = None) -> None:
        if self.status in _TERMINAL_STATES and new_status != self.status:
            raise ValueError(
                f"Não é possível transitar de {self.status.value} para {new_status.value} "
                "(estado terminal)"
            )
        self.status = new_status
        self.updated_at = datetime.now(UTC)
        if error is not None:
            self.error_message = error

    def is_terminal(self) -> bool:
        return self.status in _TERMINAL_STATES

    def apply_rename(self, original_label: str, new_name: str) -> None:
        if not original_label:
            raise ValueError("original_label não pode ser vazio")
        if not new_name or not new_name.strip():
            raise ValueError("new_name não pode ser vazio")
        self.speaker_renames[original_label] = new_name.strip()
        self.updated_at = datetime.now(UTC)

    def reset_renames(self) -> None:
        self.speaker_renames = {}
        self.updated_at = datetime.now(UTC)
