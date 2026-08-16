"""Porta ``DiarizationEngine`` — abstrai a diarização (separação por falante)."""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from yt_transcriber_bot.application.ports.transcription_engine import (
    TranscribedSegment,
)


class DiarizationError(Exception):
    """Erro durante a diarização."""


class DiarizationUnavailableError(DiarizationError):
    """Sinaliza que o engine atual nao pode atender (acionar fallback)."""


@dataclass(frozen=True)
class DiarizedSpeakerSegment:
    """Um trecho de áudio atribuído a um falante."""

    start_seconds: float
    end_seconds: float
    speaker_label: str  # ex.: "SPEAKER_00"


@dataclass(frozen=True)
class DiarizationResult:
    """Saída da diarização: segmentos com falantes e contagem."""

    speaker_segments: tuple[DiarizedSpeakerSegment, ...]
    total_speakers: int


ProgressCallback = Callable[[float, str], None]
"""Callback ``(percent_0_to_1, message)`` chamado durante a diarização."""


class DiarizationEngine(ABC):
    """Identifica quem fala em cada trecho do audio."""

    @abstractmethod
    def diarize(
        self,
        audio_path: Path,
        *,
        device: str,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
        progress: ProgressCallback | None = None,
        cancel_event: threading.Event | None = None,
    ) -> DiarizationResult: ...


def assign_speakers_to_segments(
    transcript_segments: tuple[TranscribedSegment, ...],
    diarization: DiarizationResult,
) -> tuple[tuple[TranscribedSegment, str], ...]:
    """Combina segmentos transcritos com falantes pelo critério de maior overlap.

    Para cada segmento de transcrição, escolhe o falante cujo intervalo
    diarizado tem maior interseção temporal. Se não houver nenhum overlap,
    o falante recebe o rótulo ``UNKNOWN``.
    """
    out: list[tuple[TranscribedSegment, str]] = []
    for seg in transcript_segments:
        best_label = "UNKNOWN"
        best_overlap = 0.0
        for spk in diarization.speaker_segments:
            overlap = min(seg.end_seconds, spk.end_seconds) - max(
                seg.start_seconds, spk.start_seconds
            )
            if overlap > best_overlap:
                best_overlap = overlap
                best_label = spk.speaker_label
        out.append((seg, best_label))
    return tuple(out)
