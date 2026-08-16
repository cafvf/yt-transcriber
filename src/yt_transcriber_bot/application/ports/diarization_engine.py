"""Application-owned provider-neutral speaker diarization capability."""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from yt_transcriber_bot.application.ports.transcription_engine import (
    ProcessingTarget,
    TranscribedSegment,
)


class DiarizationError(Exception):
    """Hard diarization failure that must not silently trigger another provider."""


class DiarizationUnavailableError(DiarizationError):
    """The current provider cannot serve this request and fallback may be attempted."""


@dataclass(frozen=True, slots=True)
class DiarizedSpeakerSegment:
    start_seconds: float
    end_seconds: float
    speaker_label: str


@dataclass(frozen=True, slots=True)
class DiarizationProvenance:
    backend: str | None = None
    model: str | None = None
    fallback_used: bool = False


@dataclass(frozen=True, slots=True)
class DiarizationResult:
    speaker_segments: tuple[DiarizedSpeakerSegment, ...]
    total_speakers: int
    provenance: DiarizationProvenance = field(default_factory=DiarizationProvenance)


ProgressCallback = Callable[[float, str], None]


@dataclass(frozen=True, slots=True)
class DiarizationRequest:
    audio_path: Path
    processing_target: ProcessingTarget
    min_speakers: int | None = None
    max_speakers: int | None = None
    progress: ProgressCallback | None = None
    cancel_event: threading.Event | None = None


class DiarizationEngine(ABC):
    @abstractmethod
    def diarize(self, request: DiarizationRequest) -> DiarizationResult: ...


def assign_speakers_to_segments(
    transcript_segments: tuple[TranscribedSegment, ...],
    diarization: DiarizationResult,
) -> tuple[tuple[TranscribedSegment, str], ...]:
    out: list[tuple[TranscribedSegment, str]] = []
    for seg in transcript_segments:
        best_label = "UNKNOWN"
        best_overlap = 0.0
        for speaker in diarization.speaker_segments:
            overlap = min(seg.end_seconds, speaker.end_seconds) - max(
                seg.start_seconds,
                speaker.start_seconds,
            )
            if overlap > best_overlap:
                best_overlap = overlap
                best_label = speaker.speaker_label
        out.append((seg, best_label))
    return tuple(out)
