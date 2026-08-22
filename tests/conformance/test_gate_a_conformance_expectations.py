"""Gate A: conformance expectations must follow canonical architecture."""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFORMANCE_ROOT = REPO_ROOT / "tests" / "conformance"

_REMOVED_EXPECTATIONS = {
    "application/services/" + "config_" + "signature.py",
    "config_" + "signature.py",
    "transcription_" + "signature",
    "compute_config_" + "signature",
}


def _strings(node: ast.AST) -> set[str]:
    return {
        child.value
        for child in ast.walk(node)
        if isinstance(child, ast.Constant) and isinstance(child.value, str)
    }


def _path_assignment_target(node: ast.Assign | ast.AnnAssign) -> str | None:
    if isinstance(node, ast.Assign):
        targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
        return targets[0] if len(targets) == 1 else None
    if isinstance(node.target, ast.Name):
        return node.target.id
    return None


def _violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    rel = path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            for value in sorted(_strings(node) & _REMOVED_EXPECTATIONS):
                violations.append(f"{rel}:{node.lineno}: stale assertion expects {value!r}")

        if isinstance(node, ast.Compare):
            for value in sorted(_strings(node) & _REMOVED_EXPECTATIONS):
                violations.append(f"{rel}:{node.lineno}: stale comparison expects {value!r}")

        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            target = _path_assignment_target(node)
            if target is None or "PATH" not in target:
                continue
            for value in sorted(_strings(node) & _REMOVED_EXPECTATIONS):
                violations.append(f"{rel}:{node.lineno}: stale path expectation {value!r}")

    return violations


def test_conformance_does_not_require_removed_gate_a_surfaces() -> None:
    violations: list[str] = []

    for path in CONFORMANCE_ROOT.rglob("*.py"):
        violations.extend(_violations(path))

    assert not violations, "\n".join(violations)


def test_inert_documentation_text_is_not_an_architectural_expectation(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "fixture.py"
    fixture.write_text(
        'note = "config_signature.py transcription_signature"\n',
        encoding="utf-8",
    )

    assert _violations(fixture) == []
