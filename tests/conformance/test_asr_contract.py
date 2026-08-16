# REQ-ARC-013 backend-neutral ASR contract.

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from yt_transcriber_bot.application.ports.transcription_engine import (
    ProcessingPrecision,
    ProcessingTarget,
    TranscriptionEngine,
    TranscriptionProcessingProfile,
    TranscriptionRequest,
)

ROOT = Path(__file__).resolve().parents[2]
PORT = ROOT / "src/yt_transcriber_bot/application/ports/transcription_engine.py"


def test_application_asr_port_accepts_one_backend_neutral_request() -> None:
    parameters = list(inspect.signature(TranscriptionEngine.transcribe).parameters)
    assert parameters == ["self", "request"]


def test_asr_port_does_not_import_provider_shaped_runtime_value_objects() -> None:
    source = PORT.read_text(encoding="utf-8")
    for forbidden in (
        "compute_type",
        "domain.value_objects.compute_type",
        "domain.value_objects.device",
        "domain.value_objects.model_name",
        "WhisperX",
        "CTranslate2",
    ):
        assert forbidden not in source


def test_processing_profile_uses_neutral_target_precision_and_opaque_model_id() -> None:
    profile = TranscriptionProcessingProfile(
        ProcessingTarget.GPU,
        ProcessingPrecision.HALF,
        "opaque-model-id",
    )
    assert profile.target is ProcessingTarget.GPU
    assert profile.precision is ProcessingPrecision.HALF
    assert profile.model_id == "opaque-model-id"
    assert set(TranscriptionRequest.__dataclass_fields__) == {
        "audio_path",
        "processing_profile",
        "allowed_languages",
        "requested_language",
        "progress",
        "cancel_event",
    }


def test_application_runtime_does_not_forward_backend_asr_keywords() -> None:
    application = ROOT / "src/yt_transcriber_bot/application"
    violations: list[str] = []
    for path in application.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            rendered = ast.unparse(node.func)
            if not rendered.endswith(".transcribe"):
                continue
            names = {keyword.arg for keyword in node.keywords if keyword.arg}
            forbidden = names & {"device", "compute_type", "model", "language_hint"}
            if forbidden:
                violations.append(f"{path.relative_to(ROOT)}:{node.lineno}:{sorted(forbidden)}")
    assert not violations, violations
