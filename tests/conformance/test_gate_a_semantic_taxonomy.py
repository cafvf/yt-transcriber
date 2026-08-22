"""Gate A: semantic audit of removed taxonomy consumers."""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_REMOVED_MODULES = {
    "yt_transcriber_bot.domain.entities." + "video_" + "metadata",
    "yt_transcriber_bot.application.services." + "config_" + "signature",
}
_REMOVED_PARENT_IMPORTS = {
    "yt_transcriber_bot.domain.entities": {"video_" + "metadata"},
    "yt_transcriber_bot.application.services": {"config_" + "signature"},
}
_REMOVED_NAMES = {
    "Video" + "Metadata",
    "compute_config_" + "signature",
}
_REMOVED_ATTRIBUTES = {
    "used_" + "alternate_track",
    "audio_track_" + "was_dubbed",
    "transcription_" + "signature",
}


def _semantic_violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module in _REMOVED_MODULES:
                violations.append(
                    f"{path.relative_to(REPO_ROOT)}:{node.lineno}: "
                    f"import from removed module {node.module}"
                )
            parent_names = _REMOVED_PARENT_IMPORTS.get(node.module or "", set())
            for alias in node.names:
                if alias.name in parent_names:
                    violations.append(
                        f"{path.relative_to(REPO_ROOT)}:{node.lineno}: "
                        f"import removed module member {alias.name}"
                    )

        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in _REMOVED_MODULES:
                    violations.append(
                        f"{path.relative_to(REPO_ROOT)}:{node.lineno}: "
                        f"import removed module {alias.name}"
                    )

        if isinstance(node, ast.Name) and node.id in _REMOVED_NAMES:
            violations.append(
                f"{path.relative_to(REPO_ROOT)}:{node.lineno}: removed name {node.id}"
            )

        if isinstance(node, ast.Attribute) and (
            node.attr in _REMOVED_ATTRIBUTES or node.attr in _REMOVED_NAMES
        ):
            violations.append(
                f"{path.relative_to(REPO_ROOT)}:{node.lineno}: removed attribute {node.attr}"
            )

        if isinstance(node, ast.keyword) and node.arg in {
            "used_" + "alternate_track",
            "audio_track_" + "was_dubbed",
        }:
            violations.append(
                f"{path.relative_to(REPO_ROOT)}:{node.value.lineno}: removed keyword {node.arg}"
            )

        if isinstance(node, ast.Call):
            if (
                isinstance(node.func, ast.Name)
                and node.func.id in {"getattr", "hasattr"}
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
                and node.args[1].value in (_REMOVED_ATTRIBUTES | _REMOVED_NAMES)
            ):
                violations.append(
                    f"{path.relative_to(REPO_ROOT)}:{node.lineno}: "
                    f"dynamic access to removed name {node.args[1].value}"
                )

            is_job_new = (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "new"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "Job"
            )
            is_job_ctor = isinstance(node.func, ast.Name) and node.func.id == "Job"
            if is_job_new or is_job_ctor:
                for keyword in node.keywords:
                    if keyword.arg == "config_" + "signature":
                        violations.append(
                            f"{path.relative_to(REPO_ROOT)}:{node.lineno}: "
                            "Job construction uses legacy config_signature"
                        )
                    if (
                        keyword.arg == "requested_language"
                        and isinstance(keyword.value, ast.Constant)
                        and isinstance(keyword.value.value, str)
                    ):
                        violations.append(
                            f"{path.relative_to(REPO_ROOT)}:{node.lineno}: "
                            "Job requested_language is a raw string"
                        )

            called_name = None
            if isinstance(node.func, ast.Name):
                called_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                called_name = node.func.attr
            if called_name == "compute_processing_fingerprint":
                for keyword in node.keywords:
                    if keyword.arg not in {"requested_language", "source_type"}:
                        continue
                    if isinstance(keyword.value, ast.Constant) and isinstance(
                        keyword.value.value, str
                    ):
                        violations.append(
                            f"{path.relative_to(REPO_ROOT)}:{node.lineno}: "
                            f"typed fingerprint input {keyword.arg} is raw string"
                        )

    return violations


def test_removed_taxonomy_has_no_semantic_consumers() -> None:
    violations: list[str] = []

    for root_name in ("src", "tests", "scripts"):
        root = REPO_ROOT / root_name
        for path in root.rglob("*.py"):
            violations.extend(_semantic_violations(path))

    assert not violations, "\n".join(violations)


def test_string_mentions_do_not_count_as_consumers(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture.py"
    fixture.write_text(
        'legacy = "VideoMetadata used_alternate_track transcription_signature"\n',
        encoding="utf-8",
    )

    assert _semantic_violations(fixture) == []
