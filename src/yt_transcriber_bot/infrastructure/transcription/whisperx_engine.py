"""Implementação de ``TranscriptionEngine`` baseada em WhisperX/faster-whisper.

A integração real com ``whisperx`` é abstraída via uma interface
``WhisperXBackend``, permitindo que a lógica de validação, mapeamento de
erros e seleção de idioma seja testada sem rodar modelos.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

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
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.model_name import ModelName


@dataclass(frozen=True)
class _RawTranscription:
    """Saída crua antes do alinhamento."""

    segments: tuple[dict[str, Any], ...]
    language: str
    language_probability: float


@dataclass(frozen=True)
class _AlignedTranscription:
    """Saída do passo de alinhamento (timestamps mais precisos por palavra)."""

    segments: tuple[dict[str, Any], ...]


class WhisperXBackend(Protocol):
    """Interface mínima do backend WhisperX que precisamos."""

    def transcribe(
        self,
        audio_path: Path,
        *,
        device: str,
        compute_type: str,
        model: str,
        allowed_languages: tuple[str, ...],
        language_hint: str | None = None,
    ) -> _RawTranscription: ...

    def align(
        self,
        raw: _RawTranscription,
        audio_path: Path,
        *,
        device: str,
    ) -> _AlignedTranscription: ...


class WhisperXTranscriptionEngine(TranscriptionEngine):
    """Adapter sobre ``whisperx`` operado via ``WhisperXBackend``."""

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
    ) -> TranscriptionResult:
        if not audio_path.exists():
            raise TranscriptionError(f"Arquivo de audio nao existe: {audio_path}")
        if not allowed_languages:
            raise TranscriptionError("allowed_languages nao pode ser vazio")

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
                language_hint=language_hint,
            )
        except Exception as exc:
            raise self._map_exception(exc) from exc

        if progress:
            progress(0.50, "Transcrição bruta concluída.")
            progress(0.75, "Alinhando timestamps...")

        try:
            aligned = self._backend.align(raw, audio_path, device=str(device))
        except Exception as exc:
            raise self._map_exception(exc) from exc

        if progress:
            progress(0.90, "Alinhamento concluído.")

        # Restringe idiomas detectados ao subconjunto permitido (pt/en).
        # Se o usuário informou idioma manualmente, tratamos isso como override
        # explícito para reduzir instabilidade em ASR multilíngue.
        chosen_lang = self._enforce_allowed(language_hint or raw.language, allowed_languages)

        segments = tuple(_to_domain_segments(aligned.segments))
        return TranscriptionResult(
            segments=segments,
            detected_language=Language(code=chosen_lang),
            language_confidence=float(raw.language_probability),
        )

    @staticmethod
    def _enforce_allowed(detected: str, allowed: tuple[str, ...]) -> str:
        """Se o idioma detectado nao esta na allowlist, escolhemos o primeiro permitido."""
        detected_norm = detected.split("-")[0].lower()
        if detected_norm in allowed:
            return detected_norm
        return allowed[0]

    @staticmethod
    def _map_exception(exc: Exception) -> TranscriptionError:
        msg = str(exc).lower()
        if "out of memory" in msg or "cuda oom" in msg or "oom" in msg:
            return OutOfMemoryError(str(exc))
        if isinstance(exc, TranscriptionError):
            return exc
        return TranscriptionError(str(exc))


def _to_domain_segments(
    raw_segments: Iterable[dict[str, Any]],
) -> Iterable[TranscribedSegment]:
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
