# PLAN-003 application-owned port conventions and inventory.

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "src" / "yt_transcriber_bot"
PORTS_ROOT = PACKAGE_ROOT / "application" / "ports"
MANIFEST = Path(__file__).with_name("f3_application_port_inventory.txt")

_ALLOWED_INTERNAL_PREFIXES = (
    "yt_transcriber_bot.application",
    "yt_transcriber_bot.domain",
)
_PROVIDER_OR_CONCRETE_ROOTS = {
    "httpx",
    "openai",
    "pyannote",
    "requests",
    "sqlalchemy",
    "telegram",
    "torch",
    "whisperx",
    "yt_dlp",
}
_GENERIC_STORAGE_STEMS = {
    "blob_store",
    "blob_storage",
    "filesystem",
    "file_system",
    "generic_storage",
    "storage",
}


def _manifest_modules() -> set[str]:
    return {
        line.strip()
        for line in MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def _runtime_port_modules() -> set[str]:
    return {path.name for path in PORTS_ROOT.glob("*.py") if path.name != "__init__.py"}


def _imported_roots(path: Path) -> list[tuple[str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, f"line {node.lineno}"))
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.module, f"line {node.lineno}"))
    return imports


def _is_allowed_port_import(module: str) -> bool:
    root = module.split(".", 1)[0]
    if root in sys.stdlib_module_names:
        return True
    return module.startswith(_ALLOWED_INTERNAL_PREFIXES)


def test_application_port_inventory_is_explicit_and_current() -> None:
    expected = _manifest_modules()
    actual = _runtime_port_modules()

    unexpected = sorted(actual - expected)
    stale = sorted(expected - actual)

    assert not unexpected, f"undeclared application port modules: {unexpected!r}"
    assert not stale, f"stale application port inventory entries: {stale!r}"


def test_application_ports_depend_only_on_stdlib_application_or_domain() -> None:
    violations: list[str] = []

    for path in sorted(PORTS_ROOT.glob("*.py")):
        if path.name == "__init__.py":
            continue
        for module, location in _imported_roots(path):
            if not _is_allowed_port_import(module):
                violations.append(f"{path.name}:{location}:{module}")

    assert not violations, f"concrete/provider imports in application ports: {violations!r}"


def test_application_ports_do_not_import_known_provider_sdks() -> None:
    violations: list[str] = []

    for path in sorted(PORTS_ROOT.glob("*.py")):
        for module, location in _imported_roots(path):
            root = module.split(".", 1)[0]
            if root in _PROVIDER_OR_CONCRETE_ROOTS:
                violations.append(f"{path.name}:{location}:{module}")

    assert not violations, f"provider SDK imports in application ports: {violations!r}"


def test_file_storage_is_the_only_temporary_generic_storage_surface() -> None:
    generic_modules: list[str] = []

    for path in PORTS_ROOT.glob("*.py"):
        if path.name in {"__init__.py", "file_storage.py"}:
            continue
        if path.stem.lower() in _GENERIC_STORAGE_STEMS:
            generic_modules.append(path.name)

    assert not generic_modules, (
        "new generic storage ports are forbidden; FileStorage is the only "
        f"temporary PLAN-003 exception: {sorted(generic_modules)!r}"
    )

    file_storage = PORTS_ROOT / "file_storage.py"
    assert file_storage.is_file(), (
        "FileStorage disappeared before TASK-P03-011 could record replacement/no-consumer evidence"
    )

    tree = ast.parse(
        file_storage.read_text(encoding="utf-8"),
        filename=str(file_storage),
    )
    classes = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
    assert "FileStorage" in classes, (
        "temporary FileStorage exception changed shape; update P03-011 "
        "migration evidence deliberately"
    )
