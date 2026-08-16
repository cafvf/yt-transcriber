"""Testes dos engines de diarização e do composto."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from yt_transcriber_bot.application.ports.diarization_engine import (
    DiarizationEngine,
    DiarizationError,
    DiarizationResult,
    DiarizationUnavailableError,
    DiarizedSpeakerSegment,
    assign_speakers_to_segments,
)
from yt_transcriber_bot.application.ports.transcription_engine import (
    TranscribedSegment,
)
from yt_transcriber_bot.infrastructure.diarization.composite_engine import (
    CompositeDiarizationEngine,
)
from yt_transcriber_bot.infrastructure.diarization.pyannote_diarization import (
    PyannoteBackend,
    PyannoteDiarizationEngine,
)
from yt_transcriber_bot.infrastructure.diarization.pyannote_diarization import (
    _RawDiarSegment as PyannoteSeg,
)
from yt_transcriber_bot.infrastructure.diarization.whisperx_diarization import (
    WhisperXDiarizationEngine,
    WhisperXDiarizeBackend,
)
from yt_transcriber_bot.infrastructure.diarization.whisperx_diarization import (
    _RawDiarSegment as WxSeg,
)


def _audio(tmp_path: Path) -> Path:
    p = tmp_path / "audio.ogg"
    p.write_bytes(b"\x00")
    return p


@dataclass
class FakeWxBackend(WhisperXDiarizeBackend):
    segs: tuple[WxSeg, ...] = ()
    exc: Exception | None = None
    calls: list[dict[str, Any]] | None = None

    def __post_init__(self) -> None:
        self.calls = []

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
    ) -> Iterable[WxSeg]:
        assert self.calls is not None
        self.calls.append(
            {
                "audio_path": audio_path,
                "device": device,
                "hf_token": hf_token,
                "min_speakers": min_speakers,
                "max_speakers": max_speakers,
            }
        )
        if self.exc is not None:
            raise self.exc
        return self.segs


@dataclass
class FakePyannoteBackend(PyannoteBackend):
    segs: tuple[PyannoteSeg, ...] = ()
    exc: Exception | None = None
    calls: list[dict[str, Any]] | None = None

    def __post_init__(self) -> None:
        self.calls = []

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
    ) -> Iterable[PyannoteSeg]:
        assert self.calls is not None
        self.calls.append(
            {
                "audio_path": audio_path,
                "device": device,
                "hf_token": hf_token,
                "min_speakers": min_speakers,
                "max_speakers": max_speakers,
            }
        )
        if self.exc is not None:
            raise self.exc
        return self.segs


# ======================================================================
# WhisperXDiarizationEngine
# ======================================================================


class TestWhisperXDiarizationEngine:
    def test_missing_audio_raises(self, tmp_path: Path) -> None:
        eng = WhisperXDiarizationEngine(backend=FakeWxBackend())
        with pytest.raises(DiarizationError, match="nao existe"):
            eng.diarize(tmp_path / "x.ogg", device="cpu")

    def test_no_token_raises_unavailable(self, tmp_path: Path) -> None:
        eng = WhisperXDiarizationEngine(backend=FakeWxBackend())
        with pytest.raises(DiarizationUnavailableError):
            eng.diarize(_audio(tmp_path), device="cpu")

    def test_happy_path(self, tmp_path: Path) -> None:
        backend = FakeWxBackend(
            segs=(
                WxSeg(start=0.0, end=2.5, speaker="SPEAKER_00"),
                WxSeg(start=2.5, end=5.0, speaker="SPEAKER_01"),
                WxSeg(start=5.0, end=7.0, speaker="SPEAKER_00"),
            )
        )
        eng = WhisperXDiarizationEngine(backend=backend, hf_token="hf")
        result = eng.diarize(_audio(tmp_path), device="cuda")
        assert result.total_speakers == 2
        assert len(result.speaker_segments) == 3
        assert backend.calls is not None
        assert backend.calls[0]["hf_token"] == "hf"

    def test_empty_segments_triggers_fallback(self, tmp_path: Path) -> None:
        backend = FakeWxBackend(segs=())
        eng = WhisperXDiarizationEngine(backend=backend, hf_token="hf")
        with pytest.raises(DiarizationUnavailableError, match="zero"):
            eng.diarize(_audio(tmp_path), device="cpu")

    def test_invalid_segments_filtered(self, tmp_path: Path) -> None:
        backend = FakeWxBackend(
            segs=(
                WxSeg(start=0.0, end=2.0, speaker="A"),
                WxSeg(start=2.0, end=2.0, speaker="B"),  # zero-duration
                WxSeg(start=4.0, end=3.0, speaker="C"),  # negativo
                WxSeg(start=5.0, end=7.0, speaker=""),  # vazio
                WxSeg(start=8.0, end=10.0, speaker="A"),
            )
        )
        eng = WhisperXDiarizationEngine(backend=backend, hf_token="hf")
        result = eng.diarize(_audio(tmp_path), device="cpu")
        assert len(result.speaker_segments) == 2
        assert result.total_speakers == 1

    def test_backend_exception_becomes_unavailable(self, tmp_path: Path) -> None:
        backend = FakeWxBackend(exc=RuntimeError("model load failed"))
        eng = WhisperXDiarizationEngine(backend=backend, hf_token="hf")
        with pytest.raises(DiarizationUnavailableError, match="acionando fallback"):
            eng.diarize(_audio(tmp_path), device="cpu")

    def test_passes_speaker_bounds(self, tmp_path: Path) -> None:
        backend = FakeWxBackend(segs=(WxSeg(start=0.0, end=2.0, speaker="A"),))
        eng = WhisperXDiarizationEngine(backend=backend, hf_token="hf")
        eng.diarize(
            _audio(tmp_path),
            device="cpu",
            min_speakers=2,
            max_speakers=4,
        )
        assert backend.calls is not None
        call = backend.calls[0]
        assert call["min_speakers"] == 2
        assert call["max_speakers"] == 4


# ======================================================================
# PyannoteDiarizationEngine
# ======================================================================


class TestPyannoteDiarizationEngine:
    def test_missing_audio(self, tmp_path: Path) -> None:
        eng = PyannoteDiarizationEngine(backend=FakePyannoteBackend())
        with pytest.raises(DiarizationError):
            eng.diarize(tmp_path / "x.ogg", device="cpu")

    def test_no_token_hard_fails(self, tmp_path: Path) -> None:
        eng = PyannoteDiarizationEngine(backend=FakePyannoteBackend())
        # Pyannote exige token; sem ele é erro hard, não fallback
        with pytest.raises(DiarizationError, match="HF_TOKEN"):
            eng.diarize(_audio(tmp_path), device="cpu")

    def test_happy_path(self, tmp_path: Path) -> None:
        backend = FakePyannoteBackend(
            segs=(
                PyannoteSeg(start=0.0, end=3.0, speaker="SPEAKER_00"),
                PyannoteSeg(start=3.0, end=6.0, speaker="SPEAKER_01"),
            )
        )
        eng = PyannoteDiarizationEngine(backend=backend, hf_token="hf")
        result = eng.diarize(_audio(tmp_path), device="cpu")
        assert result.total_speakers == 2

    def test_empty_segments_hard_error(self, tmp_path: Path) -> None:
        backend = FakePyannoteBackend(segs=())
        eng = PyannoteDiarizationEngine(backend=backend, hf_token="hf")
        with pytest.raises(DiarizationError, match="zero"):
            eng.diarize(_audio(tmp_path), device="cpu")

    def test_backend_exception_propagates(self, tmp_path: Path) -> None:
        backend = FakePyannoteBackend(exc=RuntimeError("connection error"))
        eng = PyannoteDiarizationEngine(backend=backend, hf_token="hf")
        with pytest.raises(DiarizationError, match="pyannote diar falhou"):
            eng.diarize(_audio(tmp_path), device="cpu")


# ======================================================================
# CompositeDiarizationEngine (Chain of Responsibility)
# ======================================================================


class _FakeEngine(DiarizationEngine):
    def __init__(
        self,
        *,
        result: DiarizationResult | None = None,
        exc: Exception | None = None,
    ) -> None:
        self.result = result
        self.exc = exc
        self.called = 0

    def diarize(
        self,
        audio_path: Path,
        *,
        device: str,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
        progress: Callable[[float, str], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> DiarizationResult:
        self.called += 1
        if self.exc is not None:
            raise self.exc
        assert self.result is not None
        return self.result


def _ok_result() -> DiarizationResult:
    return DiarizationResult(
        speaker_segments=(
            DiarizedSpeakerSegment(start_seconds=0.0, end_seconds=2.0, speaker_label="SPEAKER_00"),
        ),
        total_speakers=1,
    )


class TestCompositeDiarization:
    def test_empty_engines_raises(self) -> None:
        with pytest.raises(ValueError, match="ao menos um"):
            CompositeDiarizationEngine(engines=())

    def test_first_engine_succeeds_short_circuits(self, tmp_path: Path) -> None:
        e1 = _FakeEngine(result=_ok_result())
        e2 = _FakeEngine(result=_ok_result())
        comp = CompositeDiarizationEngine(engines=(e1, e2))
        comp.diarize(_audio(tmp_path), device="cpu")
        assert e1.called == 1
        assert e2.called == 0

    def test_first_unavailable_falls_back(self, tmp_path: Path) -> None:
        e1 = _FakeEngine(exc=DiarizationUnavailableError("primary down"))
        e2 = _FakeEngine(result=_ok_result())
        comp = CompositeDiarizationEngine(engines=(e1, e2))
        comp.diarize(_audio(tmp_path), device="cpu")
        assert e1.called == 1
        assert e2.called == 1

    def test_both_fail_raises_last_error(self, tmp_path: Path) -> None:
        e1 = _FakeEngine(exc=DiarizationUnavailableError("primary down"))
        e2 = _FakeEngine(exc=DiarizationError("secondary boom"))
        comp = CompositeDiarizationEngine(engines=(e1, e2))
        with pytest.raises(DiarizationError, match="secondary boom"):
            comp.diarize(_audio(tmp_path), device="cpu")

    def test_diarization_error_in_first_falls_back(self, tmp_path: Path) -> None:
        # Não só DiarizationUnavailableError aciona fallback, qualquer DiarizationError
        e1 = _FakeEngine(exc=DiarizationError("primary boom"))
        e2 = _FakeEngine(result=_ok_result())
        comp = CompositeDiarizationEngine(engines=(e1, e2))
        comp.diarize(_audio(tmp_path), device="cpu")
        assert e2.called == 1


# ======================================================================
# assign_speakers_to_segments
# ======================================================================


class TestAssignSpeakers:
    def test_simple_overlap_assignment(self) -> None:
        ts = (
            TranscribedSegment(start_seconds=0.0, end_seconds=2.5, text="A"),
            TranscribedSegment(start_seconds=2.5, end_seconds=5.0, text="B"),
        )
        diar = DiarizationResult(
            speaker_segments=(
                DiarizedSpeakerSegment(
                    start_seconds=0.0, end_seconds=2.4, speaker_label="SPEAKER_00"
                ),
                DiarizedSpeakerSegment(
                    start_seconds=2.6, end_seconds=5.0, speaker_label="SPEAKER_01"
                ),
            ),
            total_speakers=2,
        )
        assigned = assign_speakers_to_segments(ts, diar)
        assert assigned[0][1] == "SPEAKER_00"
        assert assigned[1][1] == "SPEAKER_01"

    def test_unknown_when_no_overlap(self) -> None:
        ts = (TranscribedSegment(start_seconds=0.0, end_seconds=2.0, text="A"),)
        diar = DiarizationResult(
            speaker_segments=(
                DiarizedSpeakerSegment(
                    start_seconds=10.0, end_seconds=12.0, speaker_label="SPEAKER_00"
                ),
            ),
            total_speakers=1,
        )
        assigned = assign_speakers_to_segments(ts, diar)
        assert assigned[0][1] == "UNKNOWN"

    def test_multiple_overlap_picks_largest(self) -> None:
        ts = (TranscribedSegment(start_seconds=0.0, end_seconds=10.0, text="A"),)
        diar = DiarizationResult(
            speaker_segments=(
                DiarizedSpeakerSegment(
                    start_seconds=0.0, end_seconds=2.0, speaker_label="SPEAKER_00"
                ),
                DiarizedSpeakerSegment(
                    start_seconds=2.0, end_seconds=9.0, speaker_label="SPEAKER_01"
                ),
            ),
            total_speakers=2,
        )
        assigned = assign_speakers_to_segments(ts, diar)
        assert assigned[0][1] == "SPEAKER_01"  # 7s vs 2s

    def test_empty_diarization_assigns_unknown(self) -> None:
        ts = (TranscribedSegment(start_seconds=0.0, end_seconds=2.0, text="A"),)
        diar = DiarizationResult(speaker_segments=(), total_speakers=0)
        assigned = assign_speakers_to_segments(ts, diar)
        assert assigned[0][1] == "UNKNOWN"

    def test_empty_segments_returns_empty(self) -> None:
        diar = DiarizationResult(speaker_segments=(), total_speakers=0)
        assert assign_speakers_to_segments((), diar) == ()
