"""Entidade ``Job`` e máquina de estados semântica do processamento."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.media_source import MediaSource, MediaSourceType
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class JobStatus(StrEnum):
    PENDING = "pending"
    ACQUIRING = "acquiring"
    # Alias interno temporário: código antigo que referencia DOWNLOADING passa a
    # observar a semântica atual. O literal persistido legado "downloading" é
    # tratado explicitamente por ``from_persisted`` e nunca é gravado de novo.
    DOWNLOADING = "acquiring"
    CONVERTING = "converting"
    TRANSCRIBING = "transcribing"
    DIARIZING = "diarizing"
    RENDERING = "rendering"
    DELIVERING = "delivering"
    COMPLETED = "completed"
    DELIVERY_FAILED = "delivery_failed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def from_persisted(cls, value: str) -> JobStatus:
        """Decodifica representação atual e o literal legado ``downloading``."""

        if value == "downloading":
            return cls.ACQUIRING
        return cls(value)


_TERMINAL_STATES = frozenset(
    {
        JobStatus.COMPLETED,
        JobStatus.DELIVERY_FAILED,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
    }
)

_ALLOWED_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.PENDING: frozenset({JobStatus.ACQUIRING, JobStatus.CANCELLED, JobStatus.FAILED}),
    JobStatus.ACQUIRING: frozenset(
        {JobStatus.CONVERTING, JobStatus.RENDERING, JobStatus.CANCELLED, JobStatus.FAILED}
    ),
    JobStatus.CONVERTING: frozenset(
        {JobStatus.TRANSCRIBING, JobStatus.CANCELLED, JobStatus.FAILED}
    ),
    JobStatus.TRANSCRIBING: frozenset({JobStatus.DIARIZING, JobStatus.CANCELLED, JobStatus.FAILED}),
    JobStatus.DIARIZING: frozenset({JobStatus.RENDERING, JobStatus.CANCELLED, JobStatus.FAILED}),
    JobStatus.RENDERING: frozenset({JobStatus.DELIVERING, JobStatus.FAILED}),
    JobStatus.DELIVERING: frozenset({JobStatus.COMPLETED, JobStatus.DELIVERY_FAILED}),
    JobStatus.COMPLETED: frozenset(),
    JobStatus.DELIVERY_FAILED: frozenset(),
    JobStatus.FAILED: frozenset(),
    JobStatus.CANCELLED: frozenset(),
}


@dataclass
class Job:
    """Agregado que registra identidade e ciclo de vida do trabalho."""

    job_id: str
    video_id: VideoId | None
    status: JobStatus
    requested_by_user_id: int
    requested_at: datetime
    updated_at: datetime
    error_message: str | None = None
    processing_fingerprint: str = ""
    media_source: MediaSource | None = None
    source_title: str | None = None
    source_duration_seconds: int | None = None
    requested_language: Language | None = None
    speaker_renames: dict[str, str] = field(default_factory=dict)
    canonical_transcript_ref: str | None = None
    md_path: str | None = None
    audio_path: str | None = None
    log_path: str | None = None

    def __post_init__(self) -> None:
        if self.requested_language is not None and not isinstance(
            self.requested_language, Language
        ):
            raise TypeError("Job.requested_language exige Language | None")

        if self.media_source is None:
            if self.video_id is None:
                raise ValueError("Job sem video_id exige media_source explícito")
            self.media_source = MediaSource.youtube(self.video_id)

        if self.media_source.source_type is MediaSourceType.YOUTUBE:
            if self.video_id is None:
                raise ValueError("Job YouTube exige video_id")
            if self.media_source.canonical_reference != self.video_id.canonical_url():
                raise ValueError("media_source YouTube não corresponde ao video_id")
        elif self.media_source.source_type is MediaSourceType.TELEGRAM_AUDIO:
            if self.video_id is not None:
                raise ValueError("Job Telegram não deve fabricar video_id YouTube")

    @classmethod
    def new(
        cls,
        video_id: VideoId | None,
        user_id: int,
        processing_fingerprint: str = "",
        *,
        media_source: MediaSource | None = None,
        source_title: str | None = None,
        source_duration_seconds: int | None = None,
        requested_language: Language | None = None,
    ) -> Job:
        now = datetime.now(UTC)
        return cls(
            job_id=str(uuid4()),
            video_id=video_id,
            status=JobStatus.PENDING,
            requested_by_user_id=user_id,
            requested_at=now,
            updated_at=now,
            processing_fingerprint=processing_fingerprint,
            media_source=media_source,
            source_title=source_title,
            source_duration_seconds=source_duration_seconds,
            requested_language=requested_language,
        )

    def transition_to(self, new_status: JobStatus, error: str | None = None) -> None:
        """Aplica uma transição legal da máquina de estados."""

        if new_status is self.status:
            return
        if new_status not in _ALLOWED_TRANSITIONS[self.status]:
            raise ValueError(f"transição inválida de {self.status.value} para {new_status.value}")
        self.status = new_status
        self.updated_at = datetime.now(UTC)
        if error is not None:
            self.error_message = error

    def is_terminal(self) -> bool:
        return self.status in _TERMINAL_STATES

    def apply_rename(self, speaker_label: str, display_name: str) -> None:
        """Registra um rename de falante no agregado."""

        label = speaker_label.strip()
        name = display_name.strip()
        if not label:
            raise ValueError("original_label não pode ser vazio")
        if not name:
            raise ValueError("new_name não pode ser vazio")
        self.speaker_renames[label] = name

    def reset_renames(self) -> None:
        self.speaker_renames.clear()
