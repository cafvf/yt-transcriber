"""PLAN-007 Gate A: preserve affected failure semantics."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from yt_transcriber_bot.application.pipeline.context import PipelineContext
from yt_transcriber_bot.application.pipeline.runner import PipelineCanceledError
from yt_transcriber_bot.application.pipeline.steps import (
    LanguageNotAllowedError,
    PipelineRejectionError,
    VideoTooLongError,
)
from yt_transcriber_bot.application.ports.audio_converter import AudioConversionError
from yt_transcriber_bot.application.ports.diarization_engine import (
    DiarizationError,
    DiarizationUnavailableError,
)
from yt_transcriber_bot.application.ports.transcription_engine import (
    OutOfMemoryError,
    TranscriptionError,
)
from yt_transcriber_bot.application.ports.youtube_downloader import (
    AgeRestrictedError,
    MembersOnlyError,
    NoAudioStreamError,
    VideoUnavailableError,
    YouTubeError,
)
from yt_transcriber_bot.domain.entities.job import Job
from yt_transcriber_bot.domain.value_objects.language import Language, LanguageSource

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "yt_transcriber_bot"


def test_error_hierarchies_affected_by_gate_a_remain_distinct() -> None:
    assert issubclass(VideoUnavailableError, YouTubeError)
    assert issubclass(MembersOnlyError, YouTubeError)
    assert issubclass(AgeRestrictedError, YouTubeError)
    assert issubclass(NoAudioStreamError, YouTubeError)
    assert issubclass(OutOfMemoryError, TranscriptionError)
    assert issubclass(DiarizationUnavailableError, DiarizationError)
    assert issubclass(VideoTooLongError, PipelineRejectionError)
    assert issubclass(LanguageNotAllowedError, PipelineRejectionError)
    assert issubclass(AudioConversionError, Exception)
    assert issubclass(PipelineCanceledError, Exception)


def test_typed_language_contract_rejects_raw_core_state() -> None:
    job_annotations = inspect.get_annotations(Job, eval_str=True)
    context_annotations = inspect.get_annotations(PipelineContext, eval_str=True)

    assert job_annotations["requested_language"] == Language | None
    assert context_annotations["requested_language"] == Language | None
    assert context_annotations["transcription_language"] == Language | None
    assert context_annotations["observed_language"] == Language | None
    assert context_annotations["language_source"] is LanguageSource


def test_use_case_keeps_separate_cancel_rejection_and_unexpected_failure_paths() -> None:
    path = SRC_ROOT / "application" / "use_cases" / "transcribe_video.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    execute = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "execute"
    )

    caught: list[str] = []
    for node in ast.walk(execute):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is None:
            caught.append("<bare>")
        elif isinstance(node.type, ast.Name):
            caught.append(node.type.id)

    assert "PipelineCanceledError" in caught
    assert "PipelineRejectionError" in caught
    assert "Exception" in caught
    assert "<bare>" not in caught


def test_use_case_still_sanitizes_persisted_failure_text() -> None:
    path = SRC_ROOT / "application" / "use_cases" / "transcribe_video.py"
    source = path.read_text(encoding="utf-8")

    assert "sanitize_text(str(exc), deps.settings)" in source
    assert 'f"{type(exc).__name__}: {exc}"' in source
    assert "canonical=False" in source
    assert "Evidência canônica da transcrição não foi persistida." in source


def test_artifact_policy_is_not_a_recovery_precondition_anymore() -> None:
    path = SRC_ROOT / "application" / "services" / "startup_recovery.py"
    source = path.read_text(encoding="utf-8")
    assert "artifact_" + "policy" not in source


def test_legacy_sql_names_are_isolated_from_application_domain() -> None:
    forbidden = (
        "config_" + "signature",
        "artifact_" + "policy",
    )
    violations: list[str] = []
    for root in (SRC_ROOT / "application", SRC_ROOT / "domain"):
        for path in root.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            if any(token in source for token in forbidden):
                violations.append(path.relative_to(REPO_ROOT).as_posix())
    assert not violations, f"legacy SQL vocabulary leaked into core: {violations!r}"
