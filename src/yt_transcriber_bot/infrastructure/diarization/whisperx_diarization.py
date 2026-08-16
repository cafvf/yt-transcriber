"""WhisperX adapter for the provider-neutral diarization application contract."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from yt_transcriber_bot.application.cancellation import OperationCanceledError, raise_if_cancelled
from yt_transcriber_bot.application.ports.diarization_engine import (
    DiarizationEngine,
    DiarizationError,
    DiarizationProvenance,
    DiarizationRequest,
    DiarizationResult,
    DiarizationUnavailableError,
    DiarizedSpeakerSegment,
)
from yt_transcriber_bot.application.ports.transcription_engine import ProcessingTarget

DEFAULT_DIARIZATION_MODEL = "pyannote/speaker-diarization-community-1"


@dataclass(frozen=True)
class _RawDiarSegment:
    start: float
    end: float
    speaker: str


class WhisperXDiarizeBackend(Protocol):
    def diarize(
        self,
        audio_path: Path,
        *,
        device: str,
        hf_token: str,
        min_speakers: int | None,
        max_speakers: int | None,
        progress: Callable[[float, str], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> Iterable[_RawDiarSegment]: ...


class WhisperXDiarizationEngine(DiarizationEngine):
    def __init__(
        self,
        backend: WhisperXDiarizeBackend,
        *,
        hf_token: str = "",
        model_id: str = DEFAULT_DIARIZATION_MODEL,
    ) -> None:
        if not model_id.strip():
            raise ValueError("model_id cannot be empty")
        self._backend = backend
        self._hf_token = hf_token
        self._model_id = model_id

    def diarize(self, request: DiarizationRequest) -> DiarizationResult:
        raise_if_cancelled(request.cancel_event)
        if not request.audio_path.exists():
            raise DiarizationError(f"Audio nao existe: {request.audio_path}")
        if not self._hf_token:
            raise DiarizationUnavailableError("WhisperX diarization unavailable")
        if request.progress:
            request.progress(0.10, "Preparando diarização WhisperX...")
        try:
            raw = list(
                self._backend.diarize(
                    request.audio_path,
                    device=_backend_device(request.processing_target),
                    hf_token=self._hf_token,
                    min_speakers=request.min_speakers,
                    max_speakers=request.max_speakers,
                    progress=request.progress,
                    cancel_event=request.cancel_event,
                )
            )
        except OperationCanceledError:
            raise
        except DiarizationError:
            raise
        except Exception as exc:
            raise DiarizationUnavailableError("WhisperX diarization unavailable") from exc

        raise_if_cancelled(request.cancel_event)
        segments = tuple(_to_domain(raw))
        if not segments:
            raise DiarizationUnavailableError(
                "WhisperX diarization returned no usable speaker segments"
            )
        if request.progress:
            request.progress(0.90, "Diarização WhisperX concluída.")
        speakers = {segment.speaker_label for segment in segments}
        return DiarizationResult(
            speaker_segments=segments,
            total_speakers=len(speakers),
            provenance=DiarizationProvenance(
                backend="whisperx",
                model=self._model_id,
                fallback_used=False,
            ),
        )


def _backend_device(target: ProcessingTarget) -> str:
    return "cuda" if target is ProcessingTarget.GPU else "cpu"


def _to_domain(raw: Iterable[_RawDiarSegment | Any]) -> Iterable[DiarizedSpeakerSegment]:
    for segment in raw:
        try:
            start = float(segment.start)
            end = float(segment.end)
            label = str(segment.speaker)
        except (AttributeError, TypeError, ValueError):
            continue
        if end <= start or not label:
            continue
        yield DiarizedSpeakerSegment(
            start_seconds=start,
            end_seconds=end,
            speaker_label=label,
        )
