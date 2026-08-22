"""Gate A conformance: no raw primitives in typed value contracts."""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_TYPED_KEYWORDS: dict[str, set[str]] = {
    "ProcessingProvenance": {"language_source"},
    "Transcript": {
        "language",
        "requested_language",
        "observed_language",
        "language_source",
    },
    "PipelineContext": {
        "requested_language",
        "transcription_language",
        "observed_language",
        "language_source",
    },
    "Job": {"requested_language"},
    "QueuedSubmission": {"requested_language"},
    "MediaMetadata": {"original_language"},
    "DownloadedAudio": {"track_selection"},
}


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _is_raw_string(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    rel = path.relative_to(REPO_ROOT)
    violations: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        name = _call_name(node)
        if name in _TYPED_KEYWORDS:
            typed = _TYPED_KEYWORDS[name]
            for keyword in node.keywords:
                if keyword.arg in typed and _is_raw_string(keyword.value):
                    violations.append(
                        f"{rel}:{node.lineno}: {name}.{keyword.arg} receives raw string"
                    )

        is_job_new = (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "new"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "Job"
        )
        if is_job_new:
            for keyword in node.keywords:
                if keyword.arg == "requested_language" and _is_raw_string(keyword.value):
                    violations.append(
                        f"{rel}:{node.lineno}: Job.new.requested_language receives raw string"
                    )

        if name == "compute_processing_fingerprint":
            for keyword in node.keywords:
                if keyword.arg in {"requested_language", "source_type"} and _is_raw_string(
                    keyword.value
                ):
                    violations.append(
                        f"{rel}:{node.lineno}: fingerprint {keyword.arg} receives raw string"
                    )

    return violations


def test_no_raw_strings_at_typed_constructor_boundaries() -> None:
    violations: list[str] = []

    for root_name in ("src", "tests", "scripts"):
        for path in (REPO_ROOT / root_name).rglob("*.py"):
            violations.extend(_violations(path))

    assert not violations, "\n".join(violations)
