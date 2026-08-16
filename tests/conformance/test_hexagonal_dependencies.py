"""PLAN-003 dependency-direction ratchet.

TASK-P03-001 intentionally starts with the exact brownfield violation set.
Any new domain/application dependency violation fails immediately. Later F3
migration tasks delete entries as their seams replace concrete dependencies;
TASK-P03-012 removes the manifest entirely when the set reaches zero.
"""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_PACKAGE = "yt_transcriber_bot"
REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "src" / PROJECT_PACKAGE
MANIFEST = Path(__file__).with_name("f3_known_dependency_violations.txt")


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module)
    return modules


def _relative_source(path: Path, package_root: Path = PACKAGE_ROOT) -> str:
    return path.relative_to(package_root).as_posix()


def _layer_violations(package_root: Path = PACKAGE_ROOT) -> set[str]:
    violations: set[str] = set()
    domain_root = package_root / "domain"
    application_root = package_root / "application"

    for path in domain_root.rglob("*.py"):
        for module in _imported_modules(path):
            if module.startswith(f"{PROJECT_PACKAGE}.application") or module.startswith(
                f"{PROJECT_PACKAGE}.infrastructure"
            ):
                violations.add(f"{_relative_source(path, package_root)}|{module}")

    for path in application_root.rglob("*.py"):
        for module in _imported_modules(path):
            if module.startswith(f"{PROJECT_PACKAGE}.infrastructure"):
                violations.add(f"{_relative_source(path, package_root)}|{module}")

    return violations


def _known_violations(path: Path = MANIFEST) -> set[str]:
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def test_dependency_violation_manifest_matches_current_brownfield_set() -> None:
    """No new violation may enter and no fixed violation may remain hidden."""

    actual = _layer_violations()
    known = _known_violations()

    unexpected = sorted(actual - known)
    stale = sorted(known - actual)

    assert not unexpected, (
        f"PLAN-003 dependency ratchet found new forbidden dependencies: {unexpected!r}"
    )
    assert not stale, (
        f"PLAN-003 dependency ratchet manifest contains resolved dependencies: {stale!r}"
    )


def test_dependency_scanner_detects_representative_forbidden_import(tmp_path: Path) -> None:
    """Regression: the rule must detect a newly introduced application->infra import."""

    package = tmp_path / PROJECT_PACKAGE
    domain = package / "domain"
    application = package / "application"
    domain.mkdir(parents=True)
    application.mkdir(parents=True)
    (domain / "__init__.py").write_text("", encoding="utf-8")
    (application / "bad.py").write_text(
        "from yt_transcriber_bot.infrastructure.telegram import bot_adapter\n",
        encoding="utf-8",
    )

    assert "application/bad.py|yt_transcriber_bot.infrastructure.telegram" in _layer_violations(
        package
    )
