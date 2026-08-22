"""Application-owned, backend-neutral ASR capability contract."""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from yt_transcriber_bot.domain.value_objects.language import Language, LanguageSource


class TranscriptionError(Exception):
    """Failure while executing ASR."""


class OutOfMemoryError(TranscriptionError):
    """Backend reported an out-of-memory execution failure."""


class ObservedLanguageNotAllowedError(TranscriptionError):
    """ASR observed a language outside the application allowlist."""


class ProcessingTarget(StrEnum):
    CPU = "cpu"
    GPU = "gpu"


class ProcessingPrecision(StrEnum):
    AUTOMATIC = "automatic"
    FULL = "full"
    HALF = "half"
    EIGHT_BIT = "eight_bit"
    EIGHT_BIT_HALF = "eight_bit_half"


@dataclass(frozen=True, slots=True)
class TranscriptionProcessingProfile:
    """Backend-neutral execution facts selected by application runtime policy."""

    target: ProcessingTarget
    precision: ProcessingPrecision
    model_id: str

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise ValueError("model_id cannot be empty")


@dataclass(frozen=True)
class TranscribedSegment:
    start_seconds: float
    end_seconds: float
    text: str


@dataclass(frozen=True)
class TranscriptionResult:
    """Structured ASR result with requested and independently observed language."""

    segments: tuple[TranscribedSegment, ...]
    detected_language: Language | None
    language_confidence: float | None
    language_source: LanguageSource = LanguageSource.ASR
    requested_language: Language | None = None
    observed_language: Language | None = None
    observed_language_confidence: float | None = None


ProgressCallback = Callable[[float, str], None]


@dataclass(frozen=True)
class TranscriptionRequest:
    """Everything the application asks of an ASR capability."""

    audio_path: Path
    processing_profile: TranscriptionProcessingProfile
    allowed_languages: tuple[Language, ...]
    requested_language: Language | None = None
    progress: ProgressCallback | None = None
    cancel_event: threading.Event | None = None


class TranscriptionEngine(ABC):
    @abstractmethod
    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult: ...
