"""PLAN-003 final dependency-direction enforcement.

TASK-P03-012 closes REQ-ARC-001 after the preceding seam migrations reduce the
known forbidden domain/application dependency set to zero. No legacy exception
manifest remains.

REQ-ARC-001 AC-04 is enforced separately from the import-direction invariant:
direct stdlib I/O in application code is not silently accepted as a workaround.
Every current hotspot must be explicitly routed to a frozen purpose-specific
requirement/task owner, and any new ungoverned hotspot fails this default-gate
test.
"""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_PACKAGE = "yt_transcriber_bot"
REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "src" / PROJECT_PACKAGE

# AC-04 routing metadata, not a dependency-violation allowlist.
_GOVERNED_APPLICATION_IO_HOTSPOTS = {
    "application/config.py": "REQ-ARC-010",
    "application/pipeline/steps.py": "REQ-ARC-012 / TASK-P03-013",
    "application/services/filesystem_safety.py": ("REQ-SEC-007 / REQ-ARC-009 / TASK-P04-012"),
    "application/services/healthcheck.py": "REQ-ARC-009 / TASK-P04-012",
    "application/services/last_error.py": (
        "REQ-DATA-006 / REQ-ARC-009 / TASK-P04-010 / TASK-P04-012"
    ),
    "application/services/rename_speakers.py": "REQ-ARC-012 / TASK-P03-013",
}

_DIRECT_IO_MODULE_ROOTS = {
    "ftplib",
    "http",
    "os",
    "shutil",
    "smtplib",
    "socket",
    "sqlite3",
    "subprocess",
    "tempfile",
    "urllib",
}

# Restricted to methods that are strong direct-filesystem signals. ``Path``
# itself remains valid as an application/domain data type.
_DIRECT_FILESYSTEM_METHODS = {
    "chmod",
    "mkdir",
    "open",
    "read_bytes",
    "read_text",
    "rmdir",
    "symlink_to",
    "touch",
    "unlink",
    "write_bytes",
    "write_text",
}


def _parse(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imported_modules(path: Path) -> set[str]:
    tree = _parse(path)
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


def _has_direct_stdlib_io(path: Path) -> bool:
    tree = _parse(path)

    for module in _imported_modules(path):
        if module.split(".", 1)[0] in _DIRECT_IO_MODULE_ROOTS:
            return True

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _DIRECT_FILESYSTEM_METHODS
        ):
            return True

    return False


def _application_io_hotspots(package_root: Path = PACKAGE_ROOT) -> set[str]:
    application_root = package_root / "application"
    return {
        _relative_source(path, package_root)
        for path in application_root.rglob("*.py")
        if _has_direct_stdlib_io(path)
    }


def test_dependency_direction_has_zero_forbidden_imports() -> None:
    """REQ-ARC-001 AC-01/02: no domain/application forbidden dependency remains."""

    actual = _layer_violations()
    assert not actual, (
        f"REQ-ARC-001 forbidden domain/application dependencies detected: {sorted(actual)!r}"
    )


def test_dependency_scanner_detects_representative_forbidden_import(tmp_path: Path) -> None:
    """Regression: a new application->infrastructure import must be detected."""

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


def test_application_direct_io_hotspots_have_frozen_boundary_owners() -> None:
    """REQ-ARC-001 AC-04: stdlib I/O cannot become an ungoverned boundary bypass."""

    actual = _application_io_hotspots()
    governed = set(_GOVERNED_APPLICATION_IO_HOTSPOTS)

    unexpected = sorted(actual - governed)
    stale = sorted(governed - actual)

    assert not unexpected, (
        "ungoverned direct stdlib I/O appeared in application code; route it to "
        f"the owning frozen boundary requirement/task: {unexpected!r}"
    )
    assert not stale, (
        "application direct-I/O governance contains resolved/stale hotspots; "
        f"converge the routing metadata deliberately: {stale!r}"
    )


def test_application_io_scanner_detects_representative_filesystem_access(
    tmp_path: Path,
) -> None:
    """Regression: representative direct application filesystem I/O must be detected."""

    package = tmp_path / PROJECT_PACKAGE
    application = package / "application"
    application.mkdir(parents=True)
    (application / "bad_io.py").write_text(
        "from pathlib import Path\n"
        "def write(path: Path) -> None:\n"
        "    path.write_text('x', encoding='utf-8')\n",
        encoding="utf-8",
    )

    assert "application/bad_io.py" in _application_io_hotspots(package)
