"""Explicit provider-neutral diarization fallback policy."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import replace

from yt_transcriber_bot.application.cancellation import raise_if_cancelled
from yt_transcriber_bot.application.ports.diarization_engine import (
    DiarizationEngine,
    DiarizationError,
    DiarizationRequest,
    DiarizationResult,
    DiarizationUnavailableError,
)

logger = logging.getLogger(__name__)


class CompositeDiarizationEngine(DiarizationEngine):
    def __init__(self, engines: Sequence[DiarizationEngine]) -> None:
        if not engines:
            raise ValueError("CompositeDiarizationEngine requer ao menos um engine")
        self._engines = tuple(engines)

    def diarize(self, request: DiarizationRequest) -> DiarizationResult:
        last_unavailable: DiarizationUnavailableError | None = None
        for index, engine in enumerate(self._engines):
            raise_if_cancelled(request.cancel_event)
            if request.progress:
                stage = "primária" if index == 0 else f"fallback {index}"
                request.progress(0.10, f"Tentando diarização {stage}...")
            try:
                result = engine.diarize(request)
            except DiarizationUnavailableError as exc:
                last_unavailable = exc
                logger.warning(
                    "Backend de diarização %s indisponível; tentando próximo.",
                    "primário" if index == 0 else f"fallback {index}",
                )
                continue
            except DiarizationError:
                raise

            provenance = replace(
                result.provenance,
                fallback_used=result.provenance.fallback_used or index > 0,
            )
            return replace(result, provenance=provenance)

        assert last_unavailable is not None
        raise DiarizationError(
            "Nenhum backend de diarização configurado conseguiu atender a solicitação."
        ) from last_unavailable
