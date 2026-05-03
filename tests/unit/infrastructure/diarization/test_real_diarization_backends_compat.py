"""Regressões de compatibilidade com APIs recentes de WhisperX/pyannote."""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from yt_transcriber_bot.infrastructure.diarization.pyannote_real_backend import (
    RealPyannoteBackend,
)
from yt_transcriber_bot.infrastructure.diarization.whisperx_real_diar_backend import (
    RealWhisperXDiarBackend,
)


@dataclass(frozen=True)
class _Turn:
    start: float
    end: float


class _NewPyannoteOutput:
    def __init__(self) -> None:
        self.speaker_diarization = [(_Turn(0.0, 1.5), "SPEAKER_00")]


class _ClassicAnnotation:
    def itertracks(self, *, yield_label: bool) -> Any:
        assert yield_label is True
        yield _Turn(0.0, 2.0), None, "SPEAKER_01"


def _audio(tmp_path: Path) -> Path:
    p = tmp_path / "audio.ogg"
    p.write_bytes(b"\x00")
    return p


def test_real_whisperx_backend_uses_token_keyword(monkeypatch: Any, tmp_path: Path) -> None:
    seen: dict[str, Any] = {}

    class FakeDiarizationPipeline:
        def __init__(self, **kwargs: Any) -> None:
            seen.update(kwargs)
            if "use_auth_token" in kwargs:
                raise TypeError("unexpected keyword argument 'use_auth_token'")

        def __call__(self, audio_path: str, **kwargs: Any) -> _NewPyannoteOutput:
            assert audio_path.endswith("audio.ogg")
            assert kwargs["min_speakers"] == 1
            assert kwargs["max_speakers"] == 2
            return _NewPyannoteOutput()

    whisperx_mod = types.ModuleType("whisperx")
    diarize_mod = types.ModuleType("whisperx.diarize")
    diarize_mod.DiarizationPipeline = FakeDiarizationPipeline
    whisperx_mod.diarize = diarize_mod
    monkeypatch.setitem(sys.modules, "whisperx", whisperx_mod)
    monkeypatch.setitem(sys.modules, "whisperx.diarize", diarize_mod)

    backend = RealWhisperXDiarBackend()
    segs = list(
        backend.diarize(
            _audio(tmp_path),
            device="cpu",
            hf_token="hf_x",
            min_speakers=1,
            max_speakers=2,
        )
    )

    assert seen == {"token": "hf_x", "device": "cpu"}
    assert segs[0].speaker == "SPEAKER_00"


def test_real_pyannote_backend_uses_token_keyword_and_new_output(
    monkeypatch: Any, tmp_path: Path
) -> None:
    seen: dict[str, Any] = {}

    class FakeCuda:
        @staticmethod
        def is_available() -> bool:
            return False

    class FakeTorch(types.ModuleType):
        cuda = FakeCuda()

        @staticmethod
        def device(name: str) -> str:
            return name

    class FakePipeline:
        @staticmethod
        def from_pretrained(model_name: str, **kwargs: Any) -> "FakePipeline":
            seen["model_name"] = model_name
            seen.update(kwargs)
            if "use_auth_token" in kwargs:
                raise TypeError("unexpected keyword argument 'use_auth_token'")
            return FakePipeline()

        def __call__(self, audio_path: str, **kwargs: Any) -> _NewPyannoteOutput:
            assert audio_path.endswith("audio.ogg")
            assert kwargs == {"min_speakers": 1, "max_speakers": 3}
            return _NewPyannoteOutput()

    pyannote_mod = types.ModuleType("pyannote")
    audio_mod = types.ModuleType("pyannote.audio")
    audio_mod.Pipeline = FakePipeline
    pyannote_mod.audio = audio_mod
    monkeypatch.setitem(sys.modules, "torch", FakeTorch("torch"))
    monkeypatch.setitem(sys.modules, "pyannote", pyannote_mod)
    monkeypatch.setitem(sys.modules, "pyannote.audio", audio_mod)

    backend = RealPyannoteBackend()
    segs = list(
        backend.diarize(
            _audio(tmp_path),
            device="cpu",
            hf_token="hf_x",
            min_speakers=1,
            max_speakers=3,
        )
    )

    assert seen == {
        "model_name": "pyannote/speaker-diarization-community-1",
        "token": "hf_x",
    }
    assert segs[0].start == 0.0
    assert segs[0].end == 1.5
    assert segs[0].speaker == "SPEAKER_00"


def test_real_pyannote_backend_still_reads_classic_annotation(
    monkeypatch: Any, tmp_path: Path
) -> None:
    class FakeCuda:
        @staticmethod
        def is_available() -> bool:
            return False

    class FakeTorch(types.ModuleType):
        cuda = FakeCuda()

        @staticmethod
        def device(name: str) -> str:
            return name

    class FakePipeline:
        @staticmethod
        def from_pretrained(model_name: str, **kwargs: Any) -> "FakePipeline":
            return FakePipeline()

        def __call__(self, audio_path: str, **kwargs: Any) -> _ClassicAnnotation:
            return _ClassicAnnotation()

    pyannote_mod = types.ModuleType("pyannote")
    audio_mod = types.ModuleType("pyannote.audio")
    audio_mod.Pipeline = FakePipeline
    pyannote_mod.audio = audio_mod
    monkeypatch.setitem(sys.modules, "torch", FakeTorch("torch"))
    monkeypatch.setitem(sys.modules, "pyannote", pyannote_mod)
    monkeypatch.setitem(sys.modules, "pyannote.audio", audio_mod)

    segs = list(
        RealPyannoteBackend(model_name="legacy").diarize(
            _audio(tmp_path),
            device="cpu",
            hf_token="hf_x",
            min_speakers=None,
            max_speakers=None,
        )
    )

    assert segs[0].speaker == "SPEAKER_01"
