"""Engine composto que tenta WhisperX e cai para pyannote em caso de falha.

Aplica padrão *Chain of Responsibility* sobre dois engines concretos
(``WhisperXDiarizationEngine`` e ``PyannoteDiarizationEngine``). A política
é simples: tenta o primeiro; se ele lançar ``DiarizationUnavailableError``
(ou qualquer erro genérico mapeado), o composto tenta o seguinte.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Sequence
from pathlib import Path

from yt_transcriber_bot.application.cancellation import raise_if_cancelled
from yt_transcriber_bot.application.ports.diarization_engine import (
    DiarizationEngine,
    DiarizationError,
    DiarizationResult,
    DiarizationUnavailableError,
)

logger = logging.getLogger(__name__)


class CompositeDiarizationEngine(DiarizationEngine):
    """Tenta cada engine na ordem; o primeiro a ter sucesso vence."""

    def __init__(self, engines: Sequence[DiarizationEngine]) -> None:
        if not engines:
            raise ValueError("CompositeDiarizationEngine requer ao menos um engine")
        self._engines = tuple(engines)

    def diarize(
        self,
        audio_path: Path,
        *,
        device: str,
        hf_token: str,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
        progress: Callable[[float, str], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> DiarizationResult:
        last_error: Exception | None = None
        for engine in self._engines:
            raise_if_cancelled(cancel_event)
            try:
                if progress:
                    progress(0.10, f"Tentando diarização com {engine.__class__.__name__}...")
                return engine.diarize(
                    audio_path,
                    device=device,
                    hf_token=hf_token,
                    min_speakers=min_speakers,
                    max_speakers=max_speakers,
                    progress=progress,
                    cancel_event=cancel_event,
                )
            except DiarizationUnavailableError as exc:
                logger.warning(
                    "Engine %s indisponivel, tentando proximo: %s",
                    engine.__class__.__name__,
                    exc,
                )
                last_error = exc
                continue
            except DiarizationError as exc:
                logger.warning(
                    "Engine %s falhou, tentando proximo: %s",
                    engine.__class__.__name__,
                    exc,
                )
                last_error = exc
                continue
        raise DiarizationError(
            f"Todos os engines de diarizacao falharam. Ultimo erro: {last_error}"
        )
