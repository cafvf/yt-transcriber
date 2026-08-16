"""REQ-ARC-010 structural configuration/fingerprint conformance."""

from __future__ import annotations

import ast
from pathlib import Path

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.configuration.credentials import ProviderCredentials

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "src" / "yt_transcriber_bot"
APPLICATION_ROOT = PACKAGE_ROOT / "application"
CONFIG_PATH = APPLICATION_ROOT / "config.py"
FINGERPRINT_PATH = APPLICATION_ROOT / "services" / "config_signature.py"

_CREDENTIAL_FIELDS = {
    "telegram_bot_token",
    "hf_token",
    "summary_api_key",
    "youtube_cookies_file",
    "youtube_cookies_browser",
}


def test_raw_provider_credentials_have_one_configuration_owner() -> None:
    assert _CREDENTIAL_FIELDS.isdisjoint(AppSettings.model_fields)
    assert set(ProviderCredentials.model_fields) == _CREDENTIAL_FIELDS


def test_generic_application_code_does_not_use_legacy_video_duration_name() -> None:
    violations: list[str] = []
    for path in APPLICATION_ROOT.rglob("*.py"):
        if path == CONFIG_PATH:
            continue
        text = path.read_text(encoding="utf-8")
        if ".max_video_duration_min" in text:
            violations.append(path.relative_to(PACKAGE_ROOT).as_posix())
    assert not violations, (
        f"generic application code must use source-neutral max_media_duration_min: {violations!r}"
    )


def test_processing_fingerprint_field_selection_has_single_authority() -> None:
    owners: list[str] = []
    for path in APPLICATION_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
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
    assert owners == ["application/services/config_signature.py"]


def test_compatibility_signature_delegates_to_canonical_fingerprint() -> None:
    config_tree = ast.parse(CONFIG_PATH.read_text(encoding="utf-8"), filename=str(CONFIG_PATH))
    methods = [
        node
        for node in ast.walk(config_tree)
        if isinstance(node, ast.FunctionDef) and node.name == "transcription_signature"
    ]
    assert len(methods) == 1
    calls = {
        node.func.id
        for node in ast.walk(methods[0])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "compute_processing_fingerprint" in calls

    fingerprint_tree = ast.parse(
        FINGERPRINT_PATH.read_text(encoding="utf-8"), filename=str(FINGERPRINT_PATH)
    )
    compatibility = [
        node
        for node in ast.walk(fingerprint_tree)
        if isinstance(node, ast.FunctionDef) and node.name == "compute_config_signature"
    ]
    assert len(compatibility) == 1
    compatibility_calls = {
        node.func.id
        for node in ast.walk(compatibility[0])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "compute_processing_fingerprint" in compatibility_calls
