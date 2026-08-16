"""Application-owned canonical transcript evidence and durable store contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from yt_transcriber_bot.domain.entities.transcript import Transcript
from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata
from yt_transcriber_bot.domain.value_objects.provenance import ProcessingProvenance


class CanonicalTranscriptNotFoundError(FileNotFoundError):
    """The requested canonical transcript reference does not exist."""

    def __init__(self, reference: str) -> None:
        super().__init__(f"Snapshot inexistente: {reference}")
        self.reference = reference


class CanonicalTranscriptCorruptError(ValueError):
    """Persisted canonical transcript evidence cannot be decoded safely."""


@dataclass(frozen=True, slots=True)
class TranscriptRenderContext:
    """Execution facts required by approved transcript renderers."""

    rendered_at: datetime
    whisper_model: str
    diarization_model: str
    transcription_source: str


@dataclass(frozen=True, slots=True)
class CanonicalTranscriptRecord:
    """Structured evidence persisted under an explicit canonical reference."""

    metadata: VideoMetadata
    transcript: Transcript
    context: TranscriptRenderContext
    processing_fingerprint: str = ""
    processing_provenance: ProcessingProvenance = field(
        default_factory=ProcessingProvenance.unknown
    )


class CanonicalTranscriptStore(ABC):
    """Durable structured-transcript capability; no filename/filesystem API."""

    @abstractmethod
    def persist(self, reference: str, record: CanonicalTranscriptRecord) -> None: ...

    @abstractmethod
    def delete(self, reference: str) -> None: ...

    @abstractmethod
    def load(self, reference: str) -> CanonicalTranscriptRecord | None: ...

    @abstractmethod
    def load_metadata(self, reference: str) -> VideoMetadata | None: ...

    @abstractmethod
    def load_metadata_many(
        self,
        references: tuple[str, ...],
    ) -> dict[str, VideoMetadata]: ...

    def require(self, reference: str) -> CanonicalTranscriptRecord:
        record = self.load(reference)
        if record is None:
            raise CanonicalTranscriptNotFoundError(reference)
        return record
