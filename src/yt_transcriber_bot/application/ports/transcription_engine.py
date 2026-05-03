"""Porta ``TranscriptionEngine`` — abstrai a transcrição via WhisperX/faster-whisper."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from yt_transcriber_bot.domain.value_objects.compute_type import ComputeType
from yt_transcriber_bot.domain.value_objects.device import Device
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.model_name import ModelName


class TranscriptionError(Exception):
    """Erro durante a transcrição."""


class OutOfMemoryError(TranscriptionError):
    """Erro especifico de OOM (CUDA/CPU)."""


@dataclass(frozen=True)
class TranscribedSegment:
    """Segmento bruto produzido pela transcrição (antes de diarização)."""

    start_seconds: float
    end_seconds: float
    text: str


@dataclass(frozen=True)
class TranscriptionResult:
    """Resultado completo da transcrição."""

    segments: tuple[TranscribedSegment, ...]
    detected_language: Language
    language_confidence: float


ProgressCallback = Callable[[float, str], None]
"""Callback ``(percent_0_to_1, message)`` chamado durante a transcrição."""


class TranscriptionEngine(ABC):
    """Motor de transcrição (Whisper / faster-whisper)."""

    @abstractmethod
    def transcribe(
        self,
        audio_path: Path,
        *,
        device: Device,
        compute_type: ComputeType,
        model: ModelName,
        allowed_languages: tuple[str, ...],
        language_hint: str | None = None,
        progress: ProgressCallback | None = None,
    ) -> TranscriptionResult: ...
