"""Diarization contract, adapters, fallback policy and assignment tests."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from yt_transcriber_bot.application.cancellation import OperationCanceledError
from yt_transcriber_bot.application.ports.diarization_engine import (
    DiarizationEngine,
    DiarizationError,
    DiarizationProvenance,
    DiarizationRequest,
    DiarizationResult,
    DiarizationUnavailableError,
    DiarizedSpeakerSegment,
    assign_speakers_to_segments,
)
from yt_transcriber_bot.application.ports.transcription_engine import (
    ProcessingTarget,
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

MODEL = "pyannote/speaker-diarization-community-1"


def _audio(tmp_path: Path) -> Path:
    path = tmp_path / "audio.ogg"
    path.write_bytes(b"\x00")
    return path


def _request(
    audio_path: Path,
    *,
    target: ProcessingTarget = ProcessingTarget.CPU,
    min_speakers: int | None = None,
    max_speakers: int | None = None,
    cancel_event: threading.Event | None = None,
) -> DiarizationRequest:
    return DiarizationRequest(
        audio_path=audio_path,
        processing_target=target,
        min_speakers=min_speakers,
        max_speakers=max_speakers,
        cancel_event=cancel_event,
    )


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


class TestWhisperXDiarizationEngine:
    def test_missing_audio_raises(self, tmp_path: Path) -> None:
        with pytest.raises(DiarizationError, match="nao existe"):
            WhisperXDiarizationEngine(FakeWxBackend()).diarize(_request(tmp_path / "x.ogg"))

    def test_no_token_raises_unavailable(self, tmp_path: Path) -> None:
        with pytest.raises(DiarizationUnavailableError):
            WhisperXDiarizationEngine(FakeWxBackend()).diarize(_request(_audio(tmp_path)))

    def test_happy_path_translates_target_and_reports_provenance(self, tmp_path: Path) -> None:
        backend = FakeWxBackend(
            segs=(
                WxSeg(0.0, 2.5, "SPEAKER_00"),
                WxSeg(2.5, 5.0, "SPEAKER_01"),
                WxSeg(5.0, 7.0, "SPEAKER_00"),
            )
        )
        result = WhisperXDiarizationEngine(backend, hf_token="hf", model_id=MODEL).diarize(
            _request(_audio(tmp_path), target=ProcessingTarget.GPU)
        )
        assert result.total_speakers == 2
        assert len(result.speaker_segments) == 3
        assert result.provenance == DiarizationProvenance(
            backend="whisperx", model=MODEL, fallback_used=False
        )
        assert backend.calls is not None
        assert backend.calls[0]["device"] == "cuda"
        assert backend.calls[0]["hf_token"] == "hf"

    def test_empty_segments_triggers_fallback(self, tmp_path: Path) -> None:
        with pytest.raises(DiarizationUnavailableError, match="no usable"):
            WhisperXDiarizationEngine(FakeWxBackend(), hf_token="hf").diarize(
                _request(_audio(tmp_path))
            )

    def test_invalid_segments_filtered(self, tmp_path: Path) -> None:
        backend = FakeWxBackend(
            segs=(
                WxSeg(0.0, 2.0, "A"),
                WxSeg(2.0, 2.0, "B"),
                WxSeg(4.0, 3.0, "C"),
                WxSeg(5.0, 7.0, ""),
                WxSeg(8.0, 10.0, "A"),
            )
        )
        result = WhisperXDiarizationEngine(backend, hf_token="hf").diarize(
            _request(_audio(tmp_path))
        )
        assert len(result.speaker_segments) == 2
        assert result.total_speakers == 1

    def test_all_invalid_segments_are_unavailable(self, tmp_path: Path) -> None:
        backend = FakeWxBackend(segs=(WxSeg(2.0, 2.0, "A"), WxSeg(4.0, 3.0, "B")))
        with pytest.raises(DiarizationUnavailableError, match="no usable"):
            WhisperXDiarizationEngine(backend, hf_token="hf").diarize(_request(_audio(tmp_path)))

    def test_backend_exception_becomes_safe_unavailable(self, tmp_path: Path) -> None:
        engine = WhisperXDiarizationEngine(
            FakeWxBackend(exc=RuntimeError("private provider detail")),
            hf_token="hf",
        )
        with pytest.raises(DiarizationUnavailableError) as exc_info:
            engine.diarize(_request(_audio(tmp_path)))
        assert "private provider detail" not in str(exc_info.value)

    def test_passes_speaker_bounds(self, tmp_path: Path) -> None:
        backend = FakeWxBackend(segs=(WxSeg(0.0, 2.0, "A"),))
        WhisperXDiarizationEngine(backend, hf_token="hf").diarize(
            _request(_audio(tmp_path), min_speakers=2, max_speakers=4)
        )
        assert backend.calls is not None
        assert backend.calls[0]["min_speakers"] == 2
        assert backend.calls[0]["max_speakers"] == 4

    def test_backend_cancellation_is_not_converted_to_fallback(self, tmp_path: Path) -> None:
        engine = WhisperXDiarizationEngine(
            FakeWxBackend(exc=OperationCanceledError("cancel")),
            hf_token="hf",
        )
        with pytest.raises(OperationCanceledError):
            engine.diarize(_request(_audio(tmp_path)))


class TestPyannoteDiarizationEngine:
    def test_missing_audio(self, tmp_path: Path) -> None:
        with pytest.raises(DiarizationError):
            PyannoteDiarizationEngine(FakePyannoteBackend()).diarize(_request(tmp_path / "x.ogg"))

    def test_no_token_is_explicitly_unavailable(self, tmp_path: Path) -> None:
        with pytest.raises(DiarizationUnavailableError):
            PyannoteDiarizationEngine(FakePyannoteBackend()).diarize(_request(_audio(tmp_path)))

    def test_happy_path_reports_actual_provenance(self, tmp_path: Path) -> None:
        backend = FakePyannoteBackend(
            segs=(
                PyannoteSeg(0.0, 3.0, "SPEAKER_00"),
                PyannoteSeg(3.0, 6.0, "SPEAKER_01"),
            )
        )
        result = PyannoteDiarizationEngine(backend, hf_token="hf", model_id=MODEL).diarize(
            _request(_audio(tmp_path))
        )
        assert result.total_speakers == 2
        assert result.provenance == DiarizationProvenance(
            backend="pyannote", model=MODEL, fallback_used=False
        )

    def test_empty_segments_are_unavailable(self, tmp_path: Path) -> None:
        with pytest.raises(DiarizationUnavailableError, match="no usable"):
            PyannoteDiarizationEngine(FakePyannoteBackend(), hf_token="hf").diarize(
                _request(_audio(tmp_path))
            )

    def test_all_invalid_segments_are_unavailable(self, tmp_path: Path) -> None:
        backend = FakePyannoteBackend(segs=(PyannoteSeg(2.0, 2.0, "A"),))
        with pytest.raises(DiarizationUnavailableError, match="no usable"):
            PyannoteDiarizationEngine(backend, hf_token="hf").diarize(_request(_audio(tmp_path)))

    def test_backend_exception_is_safe_unavailable(self, tmp_path: Path) -> None:
        engine = PyannoteDiarizationEngine(
            FakePyannoteBackend(exc=RuntimeError("private provider detail")),
            hf_token="hf",
        )
        with pytest.raises(DiarizationUnavailableError) as exc_info:
            engine.diarize(_request(_audio(tmp_path)))
        assert "private provider detail" not in str(exc_info.value)

    def test_backend_cancellation_is_not_wrapped(self, tmp_path: Path) -> None:
        engine = PyannoteDiarizationEngine(
            FakePyannoteBackend(exc=OperationCanceledError("cancel")),
            hf_token="hf",
        )
        with pytest.raises(OperationCanceledError):
            engine.diarize(_request(_audio(tmp_path)))


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

    def diarize(self, request: DiarizationRequest) -> DiarizationResult:
        self.called += 1
        if self.exc is not None:
            raise self.exc
        assert self.result is not None
        return self.result


def _ok_result(backend: str = "whisperx") -> DiarizationResult:
    return DiarizationResult(
        speaker_segments=(DiarizedSpeakerSegment(0.0, 2.0, "SPEAKER_00"),),
        total_speakers=1,
        provenance=DiarizationProvenance(backend=backend, model=MODEL, fallback_used=False),
    )


class TestCompositeDiarization:
    def test_empty_engines_raises(self) -> None:
        with pytest.raises(ValueError, match="ao menos um"):
            CompositeDiarizationEngine(())

    def test_first_engine_succeeds_short_circuits(self, tmp_path: Path) -> None:
        first = _FakeEngine(result=_ok_result())
        second = _FakeEngine(result=_ok_result("pyannote"))
        result = CompositeDiarizationEngine((first, second)).diarize(_request(_audio(tmp_path)))
        assert first.called == 1
        assert second.called == 0
        assert result.provenance.backend == "whisperx"
        assert result.provenance.fallback_used is False

    def test_explicit_unavailability_falls_back_and_records_it(self, tmp_path: Path) -> None:
        first = _FakeEngine(exc=DiarizationUnavailableError("primary down"))
        second = _FakeEngine(result=_ok_result("pyannote"))
        result = CompositeDiarizationEngine((first, second)).diarize(_request(_audio(tmp_path)))
        assert first.called == 1
        assert second.called == 1
        assert result.provenance.backend == "pyannote"
        assert result.provenance.fallback_used is True

    def test_all_unavailable_raises_canonical_hard_error(self, tmp_path: Path) -> None:
        first = _FakeEngine(exc=DiarizationUnavailableError("private primary"))
        second = _FakeEngine(exc=DiarizationUnavailableError("private fallback"))
        with pytest.raises(DiarizationError, match="Nenhum backend") as exc_info:
            CompositeDiarizationEngine((first, second)).diarize(_request(_audio(tmp_path)))
        assert "private primary" not in str(exc_info.value)
        assert "private fallback" not in str(exc_info.value)

    def test_hard_diarization_error_does_not_fallback(self, tmp_path: Path) -> None:
        first = _FakeEngine(exc=DiarizationError("invalid local input"))
        second = _FakeEngine(result=_ok_result("pyannote"))
        with pytest.raises(DiarizationError, match="invalid local input"):
            CompositeDiarizationEngine((first, second)).diarize(_request(_audio(tmp_path)))
        assert second.called == 0

    def test_cancellation_does_not_fallback(self, tmp_path: Path) -> None:
        first = _FakeEngine(exc=OperationCanceledError("cancel"))
        second = _FakeEngine(result=_ok_result("pyannote"))
        with pytest.raises(OperationCanceledError):
            CompositeDiarizationEngine((first, second)).diarize(_request(_audio(tmp_path)))
        assert second.called == 0


class TestAssignSpeakers:
    def test_simple_overlap_assignment(self) -> None:
        transcript = (
            TranscribedSegment(0.0, 2.5, "A"),
            TranscribedSegment(2.5, 5.0, "B"),
        )
        diarization = DiarizationResult(
            speaker_segments=(
                DiarizedSpeakerSegment(0.0, 2.4, "SPEAKER_00"),
                DiarizedSpeakerSegment(2.6, 5.0, "SPEAKER_01"),
            ),
            total_speakers=2,
        )
        assigned = assign_speakers_to_segments(transcript, diarization)
        assert assigned[0][1] == "SPEAKER_00"
        assert assigned[1][1] == "SPEAKER_01"

    def test_unknown_when_no_overlap(self) -> None:
        assigned = assign_speakers_to_segments(
            (TranscribedSegment(0.0, 2.0, "A"),),
            DiarizationResult(
                speaker_segments=(DiarizedSpeakerSegment(10.0, 12.0, "SPEAKER_00"),),
                total_speakers=1,
            ),
        )
        assert assigned[0][1] == "UNKNOWN"

    def test_multiple_overlap_picks_largest(self) -> None:
        assigned = assign_speakers_to_segments(
            (TranscribedSegment(0.0, 10.0, "A"),),
            DiarizationResult(
                speaker_segments=(
                    DiarizedSpeakerSegment(0.0, 2.0, "SPEAKER_00"),
                    DiarizedSpeakerSegment(2.0, 9.0, "SPEAKER_01"),
                ),
                total_speakers=2,
            ),
        )
        assert assigned[0][1] == "SPEAKER_01"

    def test_empty_diarization_assigns_unknown(self) -> None:
        assigned = assign_speakers_to_segments(
            (TranscribedSegment(0.0, 2.0, "A"),),
            DiarizationResult(speaker_segments=(), total_speakers=0),
        )
        assert assigned[0][1] == "UNKNOWN"

    def test_empty_segments_returns_empty(self) -> None:
        assert (
            assign_speakers_to_segments(
                (),
                DiarizationResult(speaker_segments=(), total_speakers=0),
            )
            == ()
        )
