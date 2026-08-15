"""Porta ``TranscriptionEngine`` — contrato source-neutral de transcrição."""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from yt_transcriber_bot.domain.value_objects.compute_type import ComputeType
from yt_transcriber_bot.domain.value_objects.device import Device
from yt_transcriber_bot.domain.value_objects.language import Language, LanguageSource
from yt_transcriber_bot.domain.value_objects.model_name import ModelName


class TranscriptionError(Exception):
    """Erro durante a transcrição."""


class OutOfMemoryError(TranscriptionError):
    """Erro específico de OOM (CUDA/CPU)."""


@dataclass(frozen=True)
class TranscribedSegment:
    start_seconds: float
    end_seconds: float
    text: str


@dataclass(frozen=True)
class TranscriptionResult:
    """Resultado da transcrição sem inventar observação/confiança.

    ``detected_language`` é o idioma efetivo usado pela transcrição por
    compatibilidade de API. Quando um idioma foi forçado, ``language_confidence``
    é ``None`` e a observação independente do backend, quando utilizável, fica
    separada em ``observed_language``/``observed_language_confidence``.
    """

    segments: tuple[TranscribedSegment, ...]
    detected_language: Language | None
    language_confidence: float | None
    language_source: LanguageSource = LanguageSource.ASR
    requested_language: Language | None = None
    observed_language: Language | None = None
    observed_language_confidence: float | None = None


ProgressCallback = Callable[[float, str], None]


class TranscriptionEngine(ABC):
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
        cancel_event: threading.Event | None = None,
    ) -> TranscriptionResult: ...
