"""Engine de diarização via ``pyannote.audio.Pipeline`` (fallback)."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from yt_transcriber_bot.application.cancellation import raise_if_cancelled
from yt_transcriber_bot.application.ports.diarization_engine import (
    DiarizationEngine,
    DiarizationError,
    DiarizationResult,
    DiarizedSpeakerSegment,
)


@dataclass(frozen=True)
class _RawDiarSegment:
    start: float
    end: float
    speaker: str


class PyannoteBackend(Protocol):
    """Interface mínima do pipeline pyannote para diarização."""

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


class PyannoteDiarizationEngine(DiarizationEngine):
    """Wrapper direto sobre ``pyannote.audio.Pipeline.from_pretrained``."""

    def __init__(
        self,
        backend: PyannoteBackend,
        *,
        hf_token: str = "",
    ) -> None:
        self._backend = backend
        self._hf_token = hf_token

    def diarize(
        self,
        audio_path: Path,
        *,
        device: str,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
        progress: Callable[[float, str], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> DiarizationResult:
        raise_if_cancelled(cancel_event)
        if not audio_path.exists():
            raise DiarizationError(f"Audio nao existe: {audio_path}")
        if not self._hf_token:
            raise DiarizationError("HF_TOKEN ausente; aceite os termos do pyannote")
        if progress:
            progress(0.10, "Preparando diarização pyannote...")
        try:
            raw = list(
                self._backend.diarize(
                    audio_path,
                    device=device,
                    hf_token=self._hf_token,
                    min_speakers=min_speakers,
                    max_speakers=max_speakers,
                    progress=progress,
                    cancel_event=cancel_event,
                )
            )
        except DiarizationError:
            raise
        except Exception as exc:
            raise DiarizationError(f"pyannote diar falhou: {exc}") from exc

        if not raw:
            raise DiarizationError("pyannote devolveu zero segmentos")

        raise_if_cancelled(cancel_event)
        if progress:
            progress(0.90, "Diarização pyannote concluída.")
        segments = tuple(_to_domain(raw))
        speakers = {s.speaker_label for s in segments}
        return DiarizationResult(speaker_segments=segments, total_speakers=len(speakers))


def _to_domain(raw: Iterable[_RawDiarSegment | Any]) -> Iterable[DiarizedSpeakerSegment]:
    for seg in raw:
        try:
            start = float(seg.start)
            end = float(seg.end)
            label = str(seg.speaker)
        except (AttributeError, TypeError, ValueError):
            continue
        if end <= start or not label:
            continue
        yield DiarizedSpeakerSegment(start_seconds=start, end_seconds=end, speaker_label=label)
