"""Backend real do WhisperX (carrega bibliotecas pesadas só sob demanda).

Implementa ``WhisperXBackend`` definido em ``whisperx_engine``. Importações
ficam dentro dos métodos para que módulos de teste possam continuar
importando sem ter ``whisperx`` instalado.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from yt_transcriber_bot.infrastructure.transcription.whisperx_engine import (
        _AlignedTranscription,
        _RawTranscription,
    )


class RealWhisperXBackend:
    """Backend que invoca ``whisperx`` de verdade."""

    def __init__(self, batch_size: int = 16) -> None:
        self._batch_size = batch_size
        self._cache: dict[tuple[str, str, str], Any] = {}

    def transcribe(
        self,
        audio_path: Path,
        *,
        device: str,
        compute_type: str,
        model: str,
        allowed_languages: tuple[str, ...],
        language_hint: str | None = None,
    ) -> _RawTranscription:
        import whisperx  # type: ignore[import-untyped]

        from yt_transcriber_bot.infrastructure.transcription.whisperx_engine import (
            _RawTranscription,
        )

        normalized_hint = (language_hint or "").strip().lower() or None
        cache_key = (model, device, compute_type, normalized_hint or "auto")
        if cache_key not in self._cache:
            self._cache[cache_key] = whisperx.load_model(
                model,
                device,
                compute_type=compute_type,
                language=normalized_hint,
            )
        loaded = self._cache[cache_key]

        audio = whisperx.load_audio(str(audio_path))
        result = loaded.transcribe(
            audio,
            batch_size=self._batch_size,
        )
        # whisperx devolve dict com "segments" e "language"
        segments = tuple(result.get("segments", ()))
        language = str(result.get("language") or normalized_hint or "en")
        # alguns modelos não devolvem probabilidade explícita; assumimos 1.0
        prob = float(result.get("language_probability", 1.0))
        return _RawTranscription(
            segments=segments, language=language, language_probability=prob
        )

    def align(
        self,
        raw: _RawTranscription,
        audio_path: Path,
        *,
        device: str,
    ) -> _AlignedTranscription:
        import whisperx  # type: ignore[import-untyped]

        from yt_transcriber_bot.infrastructure.transcription.whisperx_engine import (
            _AlignedTranscription,
        )

        align_model, metadata = whisperx.load_align_model(
            language_code=raw.language, device=device
        )
        audio = whisperx.load_audio(str(audio_path))
        aligned = whisperx.align(
            list(raw.segments),
            align_model,
            metadata,
            audio,
            device,
            return_char_alignments=False,
        )
        return _AlignedTranscription(segments=tuple(aligned.get("segments", ())))
