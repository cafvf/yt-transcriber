"""WhisperX adapter for the backend-neutral application ASR contract."""

from __future__ import annotations

import re
import threading
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from yt_transcriber_bot.application.cancellation import (
    OperationCanceledError,
    raise_if_cancelled,
)
from yt_transcriber_bot.application.ports.transcription_engine import (
    ObservedLanguageNotAllowedError,
    OutOfMemoryError,
    ProcessingPrecision,
    ProcessingTarget,
    TranscribedSegment,
    TranscriptionEngine,
    TranscriptionError,
    TranscriptionRequest,
    TranscriptionResult,
)
from yt_transcriber_bot.domain.value_objects.language import Language, LanguageSource


@dataclass(frozen=True)
class _RawTranscription:
    segments: tuple[dict[str, Any], ...]
    language: str
    language_probability: float


@dataclass(frozen=True)
class _AlignedTranscription:
    segments: tuple[dict[str, Any], ...]


class WhisperXBackend(Protocol):
    def transcribe(
        self,
        audio_path: Path,
        *,
        device: str,
        compute_type: str,
        model: str,
        allowed_languages: tuple[str, ...],
        language_hint: str | None = None,
        cancel_event: threading.Event | None = None,
    ) -> _RawTranscription: ...

    def align(
        self,
        raw: _RawTranscription,
        audio_path: Path,
        *,
        device: str,
        cancel_event: threading.Event | None = None,
    ) -> _AlignedTranscription: ...


_BACKEND_PRECISION = {
    ProcessingPrecision.AUTOMATIC: "auto",
    ProcessingPrecision.FULL: "float32",
    ProcessingPrecision.HALF: "float16",
    ProcessingPrecision.EIGHT_BIT: "int8",
    ProcessingPrecision.EIGHT_BIT_HALF: "int8_float16",
}


class WhisperXTranscriptionEngine(TranscriptionEngine):
    def __init__(self, backend: WhisperXBackend) -> None:
        self._backend = backend

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        cancel_event = request.cancel_event
        raise_if_cancelled(cancel_event)
        if not request.audio_path.exists():
            raise TranscriptionError(f"Arquivo de audio nao existe: {request.audio_path}")
        if not request.allowed_languages:
            raise TranscriptionError("allowed_languages nao pode ser vazio")

        allowed_languages = tuple(language.code for language in request.allowed_languages)
        hint = request.requested_language.code if request.requested_language is not None else None
        if hint is not None and hint not in allowed_languages:
            raise TranscriptionError(f"idioma solicitado não permitido: {hint}")

        profile = request.processing_profile
        device = "cuda" if profile.target is ProcessingTarget.GPU else "cpu"
        compute_type = _BACKEND_PRECISION[profile.precision]
        model = profile.model_id

        if request.progress:
            request.progress(0.10, "Preparando transcrição WhisperX...")
            request.progress(0.25, "Carregando modelo e áudio...")
        try:
            raw = self._backend.transcribe(
                request.audio_path,
                device=device,
                compute_type=compute_type,
                model=model,
                allowed_languages=allowed_languages,
                language_hint=hint,
                cancel_event=cancel_event,
            )
        except Exception as exc:
            raise self._map_exception(exc) from exc

        raise_if_cancelled(cancel_event)
        if request.progress:
            request.progress(0.50, "Transcrição bruta concluída.")
            request.progress(0.75, "Alinhando timestamps...")
        try:
            aligned = self._backend.align(
                raw,
                request.audio_path,
                device=device,
                cancel_event=cancel_event,
            )
        except Exception as exc:
            raise self._map_exception(exc) from exc

        raise_if_cancelled(cancel_event)
        if request.progress:
            request.progress(0.90, "Alinhamento concluído.")

        observed_code = _normalize_language_code(raw.language)
        observed_language = Language(observed_code) if observed_code else None
        observed_confidence = _normalize_confidence(raw.language_probability)

        if hint is not None:
            effective_language = Language(hint)
            confidence = None
            source = LanguageSource.REQUESTED
        else:
            if observed_code is None:
                raise TranscriptionError(
                    f"WhisperX não retornou idioma observável válido: {raw.language!r}"
                )
            if observed_code not in allowed_languages:
                raise ObservedLanguageNotAllowedError(
                    "Idioma observado pelo ASR não suportado pela configuração atual."
                )
            effective_language = Language(observed_code)
            confidence = observed_confidence
            source = LanguageSource.ASR

        return TranscriptionResult(
            segments=tuple(_to_domain_segments(aligned.segments)),
            detected_language=effective_language,
            language_confidence=confidence,
            language_source=source,
            requested_language=request.requested_language,
            observed_language=observed_language,
            observed_language_confidence=observed_confidence,
        )

    @staticmethod
    def _map_exception(exc: Exception) -> Exception:
        msg = str(exc).lower()
        if isinstance(exc, OperationCanceledError):
            return exc
        if "out of memory" in msg or "cuda oom" in msg or "oom" in msg:
            return OutOfMemoryError(str(exc))
        if isinstance(exc, TranscriptionError):
            return exc
        return TranscriptionError(str(exc))


def _normalize_language_code(value: str | None) -> str | None:
    if not value:
        return None
    base = value.strip().lower().split("-", 1)[0]
    return base if re.fullmatch(r"[a-z]{2}", base) else None


def _normalize_confidence(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    try:
        confidence = float(value)
    except ValueError:
        return None
    return confidence if 0.0 <= confidence <= 1.0 else None


def _to_domain_segments(raw_segments: Iterable[dict[str, Any]]) -> Iterable[TranscribedSegment]:
    for seg in raw_segments:
        try:
            start = float(seg.get("start"))  # type: ignore[arg-type]
            end = float(seg.get("end"))  # type: ignore[arg-type]
            text = str(seg.get("text") or "").strip()
        except (TypeError, ValueError):
            continue
        if end <= start or not text:
            continue
        yield TranscribedSegment(start_seconds=start, end_seconds=end, text=text)
