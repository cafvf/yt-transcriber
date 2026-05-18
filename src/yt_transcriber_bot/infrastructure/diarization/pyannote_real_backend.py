"""Backend real do ``pyannote.audio.Pipeline`` (fallback de diarização)."""

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
    from yt_transcriber_bot.infrastructure.diarization.pyannote_diarization import (
        _RawDiarSegment,
    )


class RealPyannoteBackend:
    """Wrapper preguiçoso sobre ``pyannote.audio.Pipeline``."""

    def __init__(
        self,
        model_name: str = "pyannote/speaker-diarization-community-1",
    ) -> None:
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
        import torch
        from pyannote.audio import Pipeline

        from yt_transcriber_bot.infrastructure.diarization.pyannote_diarization import (
            _RawDiarSegment,
        )

        cache_key = (self._model_name, device, hf_token[:8])
        raise_if_cancelled(cancel_event)
        if progress:
            progress(0.25, "Carregando modelo de diarização pyannote...")
        if cache_key not in self._cache:
            pipeline = call_with_hf_token(
                Pipeline.from_pretrained, self._model_name, hf_token=hf_token
            )
            if device == "cuda" and torch.cuda.is_available():
                pipeline.to(torch.device("cuda"))
            self._cache[cache_key] = pipeline

        pipeline = self._cache[cache_key]
        if progress:
            progress(0.50, "Executando diarização no áudio...")
        kwargs: dict[str, int] = {}
        if min_speakers is not None:
            kwargs["min_speakers"] = min_speakers
        if max_speakers is not None:
            kwargs["max_speakers"] = max_speakers

        raise_if_cancelled(cancel_event)
        annotation = pipeline(str(audio_path), **kwargs)

        raise_if_cancelled(cancel_event)
        if progress:
            progress(0.75, "Coletando trechos por falante...")
        out: list[_RawDiarSegment] = []
        for start, end, speaker in iter_speaker_turns(annotation):
            out.append(_RawDiarSegment(start=start, end=end, speaker=speaker))
        return out
