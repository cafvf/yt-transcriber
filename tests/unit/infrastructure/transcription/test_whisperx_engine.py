"""Testes do WhisperXTranscriptionEngine com backend falso."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import pytest

from yt_transcriber_bot.application.ports.transcription_engine import (
    OutOfMemoryError,
    TranscriptionError,
)
from yt_transcriber_bot.domain.value_objects.compute_type import ComputeType
from yt_transcriber_bot.domain.value_objects.device import Device
from yt_transcriber_bot.domain.value_objects.model_name import ModelName
from yt_transcriber_bot.infrastructure.transcription.whisperx_engine import (
    WhisperXBackend,
    WhisperXTranscriptionEngine,
    _AlignedTranscription,
    _RawTranscription,
)


class FakeBackend(WhisperXBackend):
    def __init__(
        self,
        *,
        raw: _RawTranscription | None = None,
        aligned: _AlignedTranscription | None = None,
        transcribe_exc: Exception | None = None,
        align_exc: Exception | None = None,
    ) -> None:
        self.transcribe_calls: list[dict[str, Any]] = []
        self.align_calls: list[dict[str, Any]] = []
        self._raw = raw
        self._aligned = aligned
        self._transcribe_exc = transcribe_exc
        self._align_exc = align_exc

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
    ) -> _RawTranscription:
        self.transcribe_calls.append(
            {
                "audio_path": audio_path,
                "device": device,
                "compute_type": compute_type,
                "model": model,
                "allowed_languages": allowed_languages,
                "language_hint": language_hint,
            }
        )
        if self._transcribe_exc is not None:
            raise self._transcribe_exc
        assert self._raw is not None
        return self._raw

    def align(
        self,
        raw: _RawTranscription,
        audio_path: Path,
        *,
        device: str,
        cancel_event: threading.Event | None = None,
    ) -> _AlignedTranscription:
        self.align_calls.append({"raw": raw, "audio_path": audio_path, "device": device})
        if self._align_exc is not None:
            raise self._align_exc
        assert self._aligned is not None
        return self._aligned


def _make_audio(tmp_path: Path) -> Path:
    p = tmp_path / "audio.ogg"
    p.write_bytes(b"\x00" * 16)
    return p


def _ok_aligned() -> _AlignedTranscription:
    return _AlignedTranscription(
        segments=(
            {"start": 0.0, "end": 2.5, "text": "Hello world"},
            {"start": 2.5, "end": 5.0, "text": "How are you"},
        )
    )


def _ok_raw(lang: str = "en", prob: float = 0.97) -> _RawTranscription:
    return _RawTranscription(
        segments=(),  # ignorados — usamos os do aligned
        language=lang,
        language_probability=prob,
    )


class TestInputValidation:
    def test_missing_audio_raises(self, tmp_path: Path) -> None:
        engine = WhisperXTranscriptionEngine(backend=FakeBackend())
        with pytest.raises(TranscriptionError, match="nao existe"):
            engine.transcribe(
                tmp_path / "missing.ogg",
                device=Device.cpu(),
                compute_type=ComputeType.from_string("int8"),
                model=ModelName(name="small"),
                allowed_languages=("pt", "en"),
            )

    def test_empty_allowed_languages_raises(self, tmp_path: Path) -> None:
        engine = WhisperXTranscriptionEngine(backend=FakeBackend())
        with pytest.raises(TranscriptionError, match="allowed_languages"):
            engine.transcribe(
                _make_audio(tmp_path),
                device=Device.cpu(),
                compute_type=ComputeType.from_string("int8"),
                model=ModelName(name="small"),
                allowed_languages=(),
            )


class TestHappyPath:
    def test_basic_transcription(self, tmp_path: Path) -> None:
        backend = FakeBackend(raw=_ok_raw("en", 0.97), aligned=_ok_aligned())
        engine = WhisperXTranscriptionEngine(backend=backend)

        result = engine.transcribe(
            _make_audio(tmp_path),
            device=Device.cpu(),
            compute_type=ComputeType.from_string("int8"),
            model=ModelName(name="small"),
            allowed_languages=("pt", "en"),
        )

        assert result.detected_language.code == "en"
        assert result.language_confidence == pytest.approx(0.97)
        assert len(result.segments) == 2
        assert result.segments[0].text == "Hello world"
        assert result.segments[0].start_seconds == 0.0
        assert result.segments[0].end_seconds == 2.5

    def test_passes_correct_args_to_backend(self, tmp_path: Path) -> None:
        backend = FakeBackend(raw=_ok_raw("pt"), aligned=_ok_aligned())
        engine = WhisperXTranscriptionEngine(backend=backend)
        audio = _make_audio(tmp_path)

        engine.transcribe(
            audio,
            device=Device.cuda(),
            compute_type=ComputeType.from_string("float16"),
            model=ModelName(name="medium"),
            allowed_languages=("pt", "en"),
        )

        call = backend.transcribe_calls[0]
        assert call["audio_path"] == audio
        assert call["device"] == "cuda"
        assert call["compute_type"] == "float16"
        assert call["model"] == "medium"
        assert call["allowed_languages"] == ("pt", "en")

    def test_progress_callback_called(self, tmp_path: Path) -> None:
        events: list[tuple[float, str]] = []
        backend = FakeBackend(raw=_ok_raw("pt"), aligned=_ok_aligned())
        engine = WhisperXTranscriptionEngine(backend=backend)

        engine.transcribe(
            _make_audio(tmp_path),
            device=Device.cpu(),
            compute_type=ComputeType.from_string("int8"),
            model=ModelName(name="small"),
            allowed_languages=("pt", "en"),
            progress=lambda p, m: events.append((p, m)),
        )

        # Esperamos pelo menos 3 callbacks: 0.10, 0.50, 0.90
        percents = [p for p, _ in events]
        assert 0.10 in percents
        assert 0.50 in percents
        assert 0.90 in percents


class TestLanguageEnforcement:
    @pytest.mark.parametrize(
        ("detected", "allowed", "expected"),
        [
            ("pt", ("pt", "en"), "pt"),
            ("en", ("pt", "en"), "en"),
            ("PT", ("pt", "en"), "pt"),
            ("pt-BR", ("pt", "en"), "pt"),
            ("en-US", ("pt", "en"), "en"),
            ("es", ("pt", "en"), "pt"),  # fallback para o primeiro
            ("fr", ("pt", "en"), "pt"),  # fallback
            ("ja", ("en", "pt"), "en"),  # fallback respeita ordem
        ],
    )
    def test_enforcement(
        self,
        tmp_path: Path,
        detected: str,
        allowed: tuple[str, ...],
        expected: str,
    ) -> None:
        backend = FakeBackend(raw=_ok_raw(detected), aligned=_ok_aligned())
        engine = WhisperXTranscriptionEngine(backend=backend)
        result = engine.transcribe(
            _make_audio(tmp_path),
            device=Device.cpu(),
            compute_type=ComputeType.from_string("int8"),
            model=ModelName(name="small"),
            allowed_languages=allowed,
        )
        assert result.detected_language.code == expected


class TestErrorMapping:
    def test_oom_during_transcribe_mapped(self, tmp_path: Path) -> None:
        backend = FakeBackend(transcribe_exc=RuntimeError("CUDA out of memory"))
        engine = WhisperXTranscriptionEngine(backend=backend)
        with pytest.raises(OutOfMemoryError):
            engine.transcribe(
                _make_audio(tmp_path),
                device=Device.cuda(),
                compute_type=ComputeType.from_string("float16"),
                model=ModelName(name="large-v3"),
                allowed_languages=("pt", "en"),
            )

    def test_oom_during_align_mapped(self, tmp_path: Path) -> None:
        backend = FakeBackend(
            raw=_ok_raw("pt"),
            align_exc=RuntimeError("OOM at alignment"),
        )
        engine = WhisperXTranscriptionEngine(backend=backend)
        with pytest.raises(OutOfMemoryError):
            engine.transcribe(
                _make_audio(tmp_path),
                device=Device.cuda(),
                compute_type=ComputeType.from_string("float16"),
                model=ModelName(name="medium"),
                allowed_languages=("pt", "en"),
            )

    def test_generic_error_mapped(self, tmp_path: Path) -> None:
        backend = FakeBackend(transcribe_exc=ValueError("model not found"))
        engine = WhisperXTranscriptionEngine(backend=backend)
        with pytest.raises(TranscriptionError, match="model not found"):
            engine.transcribe(
                _make_audio(tmp_path),
                device=Device.cpu(),
                compute_type=ComputeType.from_string("int8"),
                model=ModelName(name="small"),
                allowed_languages=("pt", "en"),
            )


class TestSegmentFiltering:
    def test_invalid_segments_skipped(self, tmp_path: Path) -> None:
        aligned = _AlignedTranscription(
            segments=(
                {"start": 0.0, "end": 2.0, "text": "Valid"},
                {"start": 2.0, "end": 2.0, "text": "zero duration"},  # invalido
                {"start": 5.0, "end": 4.0, "text": "negative duration"},  # invalido
                {"start": 6.0, "end": 8.0, "text": ""},  # texto vazio
                {"start": 9.0, "end": 11.0, "text": "  "},  # texto whitespace
                {"start": 12.0, "end": 14.0, "text": "Also valid"},
            )
        )
        backend = FakeBackend(raw=_ok_raw("en"), aligned=aligned)
        engine = WhisperXTranscriptionEngine(backend=backend)
        result = engine.transcribe(
            _make_audio(tmp_path),
            device=Device.cpu(),
            compute_type=ComputeType.from_string("int8"),
            model=ModelName(name="small"),
            allowed_languages=("pt", "en"),
        )
        assert len(result.segments) == 2
        assert result.segments[0].text == "Valid"
        assert result.segments[1].text == "Also valid"

    def test_segments_text_is_stripped(self, tmp_path: Path) -> None:
        aligned = _AlignedTranscription(
            segments=({"start": 0.0, "end": 2.0, "text": "  Hello world  "},)
        )
        backend = FakeBackend(raw=_ok_raw("en"), aligned=aligned)
        engine = WhisperXTranscriptionEngine(backend=backend)
        result = engine.transcribe(
            _make_audio(tmp_path),
            device=Device.cpu(),
            compute_type=ComputeType.from_string("int8"),
            model=ModelName(name="small"),
            allowed_languages=("pt", "en"),
        )
        assert result.segments[0].text == "Hello world"
