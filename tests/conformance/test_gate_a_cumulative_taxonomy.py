"""PLAN-007 Gate A cumulative canonical-taxonomy conformance."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.pipeline.context import PipelineContext
from yt_transcriber_bot.application.services.processing_fingerprint import (
    compute_processing_fingerprint,
)
from yt_transcriber_bot.domain.entities.job import Job
from yt_transcriber_bot.domain.value_objects.language import Language, LanguageSource

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "src" / "yt_transcriber_bot"
APPLICATION_ROOT = PACKAGE_ROOT / "application"
DOMAIN_ROOT = PACKAGE_ROOT / "domain"

_LEGACY_VIDEO_METADATA = "Video" + "Metadata"
_LEGACY_CONFIG_SIGNATURE = "config_" + "signature"
_LEGACY_TRANSCRIPTION_SIGNATURE = "transcription_" + "signature"
_LEGACY_ARTIFACT_POLICY = "artifact_" + "policy"


def test_pipeline_context_language_state_is_typed() -> None:
    annotations = inspect.get_annotations(PipelineContext, eval_str=True)
    assert annotations["requested_language"] == Language | None
    assert annotations["transcription_language"] == Language | None
    assert annotations["observed_language"] == Language | None
    assert annotations["language_source"] is LanguageSource

    ctx = PipelineContext(job=Job.new(None, 1, media_source=_telegram_source()))
    assert ctx.requested_language is None
    assert ctx.transcription_language is None
    assert ctx.observed_language is None
    assert ctx.language_source is LanguageSource.UNKNOWN


def _telegram_source():
    from yt_transcriber_bot.domain.value_objects.media_source import MediaSource

    return MediaSource.telegram_audio("fixture")


def test_job_uses_canonical_fingerprint_and_typed_requested_language() -> None:
    annotations = inspect.get_annotations(Job, eval_str=True)
    assert annotations["processing_fingerprint"] is str
    assert annotations["requested_language"] == Language | None
    assert _LEGACY_CONFIG_SIGNATURE not in Job.__dataclass_fields__
    assert _LEGACY_ARTIFACT_POLICY not in Job.__dataclass_fields__


def test_legacy_internal_taxonomy_is_absent_from_application_and_domain() -> None:
    forbidden = (
        _LEGACY_VIDEO_METADATA,
        _LEGACY_CONFIG_SIGNATURE,
        _LEGACY_TRANSCRIPTION_SIGNATURE,
        _LEGACY_ARTIFACT_POLICY,
        "audio_track_" + "was_dubbed",
        "used_" + "alternate_track",
    )
    violations: list[str] = []
    for root in (APPLICATION_ROOT, DOMAIN_ROOT):
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if any(token in text for token in forbidden):
                violations.append(path.relative_to(REPO_ROOT).as_posix())
    assert not violations, f"legacy core taxonomy remains: {violations!r}"


def test_processing_fingerprint_api_is_typed() -> None:
    signature = inspect.signature(compute_processing_fingerprint)
    annotations = inspect.get_annotations(
        compute_processing_fingerprint,
        eval_str=True,
    )
    assert annotations["requested_language"] == Language | None
    assert "source_type" in signature.parameters


def test_configuration_has_canonical_media_duration_field() -> None:
    assert "max_media_duration_min" in AppSettings.model_fields
    assert "max_video_duration_min" not in AppSettings.model_fields


def test_compatibility_signature_functions_are_gone() -> None:
    config_source = (APPLICATION_ROOT / "config.py").read_text(encoding="utf-8")
    fingerprint_source = (APPLICATION_ROOT / "services" / "processing_fingerprint.py").read_text(
        encoding="utf-8"
    )
    assert _LEGACY_TRANSCRIPTION_SIGNATURE not in config_source
    assert "compute_" + _LEGACY_CONFIG_SIGNATURE not in fingerprint_source


def test_fingerprint_field_selection_has_single_authority() -> None:
    owners: list[str] = []
    for path in APPLICATION_ROOT.rglob("*.py"):
        tree = ast.parse(
            path.read_text(encoding="utf-8"),
            filename=str(path),
        )
        for node in tree.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                names: list[str] = []
                if isinstance(node, ast.Assign):
                    names.extend(
                        target.id for target in node.targets if isinstance(target, ast.Name)
                    )
                elif isinstance(node.target, ast.Name):
                    names.append(node.target.id)
                if "SIGNIFICANT_FIELDS" in names:
                    owners.append(path.relative_to(PACKAGE_ROOT).as_posix())
    assert owners == ["application/services/processing_fingerprint.py"]
