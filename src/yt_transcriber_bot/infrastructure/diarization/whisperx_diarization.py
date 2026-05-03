"""Engine de diarização via ``whisperx.diarize.DiarizationPipeline``.

A integração real com ``whisperx`` é abstraída por ``WhisperXDiarizeBackend``.
A implementação real do backend só importa ``whisperx`` no acto de instanciar.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from yt_transcriber_bot.application.ports.diarization_engine import (
    DiarizationEngine,
    DiarizationError,
    DiarizationResult,
    DiarizationUnavailableError,
    DiarizedSpeakerSegment,
)


@dataclass(frozen=True)
class _RawDiarSegment:
    start: float
    end: float
    speaker: str


class WhisperXDiarizeBackend(Protocol):
    """Interface mínima do backend WhisperX para diarização."""

    def diarize(
        self,
        audio_path: Path,
        *,
        device: str,
        hf_token: str,
        min_speakers: int | None,
        max_speakers: int | None,
        progress: Callable[[float, str], None] | None = None,
    ) -> Iterable[_RawDiarSegment]: ...


class WhisperXDiarizationEngine(DiarizationEngine):
    """Wrapper sobre ``whisperx.DiarizationPipeline``."""

    def __init__(self, backend: WhisperXDiarizeBackend) -> None:
        self._backend = backend

    def diarize(
        self,
        audio_path: Path,
        *,
        device: str,
        hf_token: str,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
        progress: Callable[[float, str], None] | None = None,
    ) -> DiarizationResult:
        if not audio_path.exists():
            raise DiarizationError(f"Audio nao existe: {audio_path}")
        if not hf_token:
            raise DiarizationUnavailableError("HF_TOKEN ausente")
        if progress:
            progress(0.10, "Preparando diarização WhisperX...")
        try:
            raw = list(
                self._backend.diarize(
                    audio_path,
                    device=device,
                    hf_token=hf_token,
                    min_speakers=min_speakers,
                    max_speakers=max_speakers,
                    progress=progress,
                )
            )
        except DiarizationError:
            raise
        except Exception as exc:
            raise DiarizationUnavailableError(
                f"WhisperX diar falhou (acionando fallback): {exc}"
            ) from exc

        if not raw:
            raise DiarizationUnavailableError("WhisperX devolveu zero segmentos")

        if progress:
            progress(0.90, "Diarização WhisperX concluída.")
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
