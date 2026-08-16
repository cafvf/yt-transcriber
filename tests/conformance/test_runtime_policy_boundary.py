# PLAN-003 runtime/hardware policy boundary.

from __future__ import annotations

import ast
from pathlib import Path

from tests.unit.application.conftest import FakeTranscriptionEngine
from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.pipeline.context import PipelineContext
from yt_transcriber_bot.application.pipeline.steps import TranscribeStep
from yt_transcriber_bot.application.ports.transcription_engine import (
    TranscribedSegment,
    TranscriptionResult,
)
from yt_transcriber_bot.application.runtime_selection import RuntimePlan
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.compute_type import ComputeKind, ComputeType
from yt_transcriber_bot.domain.value_objects.device import Device
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.model_name import ModelName
from yt_transcriber_bot.domain.value_objects.video_id import VideoId

REPO_ROOT = Path(__file__).resolve().parents[2]
DOMAIN_ROOT = REPO_ROOT / "src" / "yt_transcriber_bot" / "domain"
MODEL_NAME_PATH = DOMAIN_ROOT / "value_objects" / "model_name.py"

_FORBIDDEN_DOMAIN_RUNTIME_IMPORTS = {
    "os",
    "pathlib",
    "shutil",
    "subprocess",
    "torch",
}


def test_domain_does_not_import_filesystem_or_hardware_runtime_modules() -> None:
    violations: list[str] = []

    for path in DOMAIN_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)

            for module in modules:
                root = module.split(".", 1)[0]
                if root in _FORBIDDEN_DOMAIN_RUNTIME_IMPORTS:
                    relative = path.relative_to(DOMAIN_ROOT).as_posix()
                    violations.append(f"{relative}:{node.lineno}:{module}")

    assert not violations, f"runtime/filesystem imports in pure domain: {violations!r}"


def test_model_name_contains_identity_not_runtime_selection_policy() -> None:
    tree = ast.parse(
        MODEL_NAME_PATH.read_text(encoding="utf-8"),
        filename=str(MODEL_NAME_PATH),
    )
    methods = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert "vram_requirement_gb" not in methods
    assert "smaller_alternative" not in methods


def test_selected_runtime_facts_are_available_to_processing_provenance(
    tmp_path: Path,
) -> None:
    settings = AppSettings(
        _env_file=None,
        telegram_bot_token="1:test",
        telegram_allowed_user_id=1,
        hf_token="hf_test",
        allowed_languages=("pt", "en"),
    )
    engine = FakeTranscriptionEngine(
        result=TranscriptionResult(
            segments=(
                TranscribedSegment(
                    start_seconds=0.0,
                    end_seconds=1.0,
                    text="teste",
                ),
            ),
            detected_language=Language("pt"),
            language_confidence=0.9,
            observed_language=Language("pt"),
            observed_language_confidence=0.9,
        )
    )

    job = Job.new(VideoId("dQw4w9WgXcQ"), 1)
    job.transition_to(JobStatus.ACQUIRING)
    job.transition_to(JobStatus.CONVERTING)

    audio_path = tmp_path / "audio.ogg"
    audio_path.write_bytes(b"audio")

    ctx = PipelineContext(job=job)
    ctx.converted_audio_path = audio_path
    ctx.runtime_plan = RuntimePlan(
        device=Device.cpu(),
        compute_type=ComputeType(kind=ComputeKind.INT8),
        model=ModelName("small"),
        reason="test runtime",
    )

    TranscribeStep(engine, settings).execute(ctx)

    provenance = ctx.processing_provenance
    assert provenance.transcription_model == "small"
    assert provenance.device == "cpu"
    assert provenance.compute_type == "int8"
