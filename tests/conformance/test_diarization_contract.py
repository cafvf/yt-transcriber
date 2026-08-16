# REQ-ARC-005 provider-neutral diarization capability contract.

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from yt_transcriber_bot.application.ports.diarization_engine import (
    DiarizationEngine,
    DiarizationProvenance,
    DiarizationRequest,
    DiarizationResult,
)
from yt_transcriber_bot.application.ports.transcription_engine import ProcessingTarget

ROOT = Path(__file__).resolve().parents[2]
PORT = ROOT / "src/yt_transcriber_bot/application/ports/diarization_engine.py"
APPLICATION = ROOT / "src/yt_transcriber_bot/application"
COMPOSITION = ROOT / "src/yt_transcriber_bot/composition_root.py"


def test_diarization_port_accepts_one_provider_neutral_request() -> None:
    assert list(inspect.signature(DiarizationEngine.diarize).parameters) == [
        "self",
        "request",
    ]


def test_diarization_port_has_no_provider_credential_or_device_string_surface() -> None:
    source = PORT.read_text(encoding="utf-8")
    for forbidden in (
        "hf_token",
        "use_auth_token",
        "pyannote.audio",
        "whisperx.",
        "device:",
        "device=",
    ):
        assert forbidden not in source


def test_diarization_request_is_application_neutral() -> None:
    assert set(DiarizationRequest.__dataclass_fields__) == {
        "audio_path",
        "processing_target",
        "min_speakers",
        "max_speakers",
        "progress",
        "cancel_event",
    }
    assert ProcessingTarget.CPU.value == "cpu"
    assert ProcessingTarget.GPU.value == "gpu"


def test_result_exposes_actual_backend_model_and_fallback_provenance() -> None:
    result = DiarizationResult(
        speaker_segments=(),
        total_speakers=0,
        provenance=DiarizationProvenance(
            backend="pyannote",
            model="model-id",
            fallback_used=True,
        ),
    )
    assert result.provenance.backend == "pyannote"
    assert result.provenance.model == "model-id"
    assert result.provenance.fallback_used is True


def test_application_does_not_forward_provider_shaped_diarization_keywords() -> None:
    violations: list[str] = []
    for path in APPLICATION.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not ast.unparse(node.func).endswith(".diarize"):
                continue
            keyword_names = {keyword.arg for keyword in node.keywords if keyword.arg}
            forbidden = keyword_names & {"device", "hf_token", "model_name"}
            if forbidden:
                violations.append(f"{path.relative_to(ROOT)}:{node.lineno}:{sorted(forbidden)}")
    assert not violations, violations


def test_composition_uses_one_explicit_model_for_both_diarization_adapters() -> None:
    source = COMPOSITION.read_text(encoding="utf-8")
    assert '_DIARIZATION_MODEL_NAME = "pyannote/speaker-diarization-community-1"' in source
    assert source.count("model_name=_DIARIZATION_MODEL_NAME") >= 2
    assert source.count("model_id=_DIARIZATION_MODEL_NAME") >= 2
