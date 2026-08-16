"""Backend real do ``whisperx.diarize.DiarizationPipeline``."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from yt_transcriber_bot.application.cancellation import raise_if_cancelled
from yt_transcriber_bot.infrastructure.diarization._compat import (
    call_with_hf_token,
    iter_speaker_turns,
)

if TYPE_CHECKING:
    from yt_transcriber_bot.infrastructure.diarization.whisperx_diarization import (
        _RawDiarSegment,
    )

DEFAULT_DIARIZATION_MODEL = "pyannote/speaker-diarization-community-1"


class RealWhisperXDiarBackend:
    def __init__(self, model_name: str = DEFAULT_DIARIZATION_MODEL) -> None:
        if not model_name.strip():
            raise ValueError("model_name cannot be empty")
        self._model_name = model_name
        self._cache: dict[tuple[str, str, str], Any] = {}

    def diarize(
        self,
        audio_path: Path,
        *,
        device: str,
        hf_token: str,
        min_speakers: int | None,
        max_speakers: int | None,
        progress: Callable[[float, str], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> Iterable[_RawDiarSegment]:
        from whisperx.diarize import DiarizationPipeline

        from yt_transcriber_bot.infrastructure.diarization.whisperx_diarization import (
            _RawDiarSegment,
        )

        cache_key = (self._model_name, device, hf_token[:8])
        raise_if_cancelled(cancel_event)
        if progress:
            progress(0.25, "Carregando modelo de diarização WhisperX/pyannote...")
        if cache_key not in self._cache:
            self._cache[cache_key] = call_with_hf_token(
                DiarizationPipeline,
                model_name=self._model_name,
                hf_token=hf_token,
                device=device,
            )
        pipeline = self._cache[cache_key]
        if progress:
            progress(0.50, "Executando diarização no áudio...")
        raise_if_cancelled(cancel_event)
        annotation = pipeline(
            str(audio_path),
            min_speakers=min_speakers,
            max_speakers=max_speakers,
        )
        raise_if_cancelled(cancel_event)
        if progress:
            progress(0.75, "Coletando trechos por falante...")
        return [
            _RawDiarSegment(start=start, end=end, speaker=speaker)
            for start, end, speaker in iter_speaker_turns(annotation)
        ]
