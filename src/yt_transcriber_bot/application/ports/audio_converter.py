"""Porta ``AudioConverter`` — abstrai conversão de áudio para Opus/OGG."""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


class AudioConversionError(Exception):
    """Erro durante a conversão de áudio."""


@dataclass(frozen=True)
class ConvertedAudio:
    """Resultado da conversão de áudio."""

    path: Path
    bitrate_kbps: int
    sample_rate_hz: int
    channels: int
    container: str
    size_bytes: int


class AudioConverter(ABC):
    """Operações de conversão de áudio."""

    @abstractmethod
    def convert_to_opus_mono(
        self,
        source: Path,
        dest: Path,
        *,
        bitrate_kbps: int = 32,
        sample_rate_hz: int = 16000,
        cancel_event: threading.Event | None = None,
    ) -> ConvertedAudio: ...
