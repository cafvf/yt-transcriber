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


class RealWhisperXDiarBackend:
    """Wrapper preguiçoso sobre ``whisperx.diarize.DiarizationPipeline``."""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], Any] = {}

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

        cache_key = (device, hf_token[:8])
        raise_if_cancelled(cancel_event)
        if progress:
            progress(0.25, "Carregando modelo de diarização WhisperX/pyannote...")
        if cache_key not in self._cache:
            self._cache[cache_key] = call_with_hf_token(
                DiarizationPipeline, hf_token=hf_token, device=device
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
        out: list[_RawDiarSegment] = []
        for start, end, speaker in iter_speaker_turns(annotation):
            out.append(_RawDiarSegment(start=start, end=end, speaker=speaker))
        return out
