"""Implementação de ``TranscriptionEngine`` baseada em WhisperX/faster-whisper."""

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
    OutOfMemoryError,
    ProgressCallback,
    TranscribedSegment,
    TranscriptionEngine,
    TranscriptionError,
    TranscriptionResult,
)
from yt_transcriber_bot.domain.value_objects.compute_type import ComputeType
from yt_transcriber_bot.domain.value_objects.device import Device
from yt_transcriber_bot.domain.value_objects.language import Language, LanguageSource
from yt_transcriber_bot.domain.value_objects.model_name import ModelName


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


class WhisperXTranscriptionEngine(TranscriptionEngine):
    def __init__(self, backend: WhisperXBackend) -> None:
        self._backend = backend

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
    ) -> TranscriptionResult:
        raise_if_cancelled(cancel_event)
        if not audio_path.exists():
            raise TranscriptionError(f"Arquivo de audio nao existe: {audio_path}")
        if not allowed_languages:
            raise TranscriptionError("allowed_languages nao pode ser vazio")

        hint = _normalize_language_code(language_hint) if language_hint else None
        if language_hint and hint not in allowed_languages:
            raise TranscriptionError(f"idioma solicitado não permitido: {language_hint}")

        if progress:
            progress(0.10, "Preparando transcrição WhisperX...")
            progress(0.25, "Carregando modelo e áudio...")
        try:
            raw = self._backend.transcribe(
                audio_path,
                device=str(device),
                compute_type=str(compute_type),
                model=model.name,
                allowed_languages=allowed_languages,
                language_hint=hint,
                cancel_event=cancel_event,
            )
        except Exception as exc:
            raise self._map_exception(exc) from exc

        raise_if_cancelled(cancel_event)
        if progress:
            progress(0.50, "Transcrição bruta concluída.")
            progress(0.75, "Alinhando timestamps...")
        try:
            aligned = self._backend.align(
                raw,
                audio_path,
                device=str(device),
                cancel_event=cancel_event,
            )
        except Exception as exc:
            raise self._map_exception(exc) from exc

        raise_if_cancelled(cancel_event)
        if progress:
            progress(0.90, "Alinhamento concluído.")

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
                raise TranscriptionError(
                    "Idioma observado pelo ASR não suportado nesta versão: "
                    f"{observed_code}. Permitidos: {', '.join(allowed_languages)}"
                )
            effective_language = Language(observed_code)
            confidence = observed_confidence
            source = LanguageSource.ASR

        return TranscriptionResult(
            segments=tuple(_to_domain_segments(aligned.segments)),
            detected_language=effective_language,
            language_confidence=confidence,
            language_source=source,
            requested_language=Language(hint) if hint else None,
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
