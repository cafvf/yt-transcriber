# PLAN-003 application-owned port conventions and inventory.

from __future__ import annotations

import ast
import importlib
import inspect
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
    "file_storage",
    "file_system",
    "filesystem",
    "generic_storage",
    "storage",
}

_TRANSPORT_SPECIFIC_OPERATION_TOKENS = {
    "ffmpeg",
    "pyannote",
    "sqlalchemy",
    "telegram",
    "whisperx",
    "yt_dlp",
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


def test_obsolete_generic_file_storage_surface_is_absent() -> None:
    generic_modules = sorted(
        path.name
        for path in PORTS_ROOT.glob("*.py")
        if path.name != "__init__.py" and path.stem.lower() in _GENERIC_STORAGE_STEMS
    )

    assert not generic_modules, (
        f"generic storage ports are forbidden after TASK-P03-011: {generic_modules!r}"
    )

    obsolete_paths = (
        PACKAGE_ROOT / "application" / "ports" / "file_storage.py",
        PACKAGE_ROOT / "infrastructure" / "persistence" / "filesystem" / "local_file_storage.py",
    )
    existing = [str(path.relative_to(REPO_ROOT)) for path in obsolete_paths if path.exists()]
    assert not existing, f"obsolete generic storage files remain: {existing!r}"

    forbidden_symbols = ("FileStorage", "LocalFileStorage")
    violations: list[str] = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for symbol in forbidden_symbols:
            if symbol in text:
                violations.append(f"{path.relative_to(REPO_ROOT)} contains {symbol}")

    assert not violations, f"obsolete generic FileStorage runtime surface remains: {violations!r}"


def test_generic_application_port_operation_names_are_transport_neutral() -> None:
    # REQ-ARC-012 AC-02: generic operations must not name a transport/provider.
    violations: list[str] = []

    for path in sorted(PORTS_ROOT.glob("*.py")):
        if path.name == "__init__.py":
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name.startswith("_"):
                continue

            lowered = node.name.lower()
            for token in sorted(_TRANSPORT_SPECIFIC_OPERATION_TOKENS):
                if token in lowered:
                    violations.append(f"{path.name}:line {node.lineno}:{node.name}:{token}")

    assert not violations, (
        f"transport/provider-specific operation names leaked into application ports: {violations!r}"
    )


def test_application_port_abcs_are_plain_test_double_implementable() -> None:
    # REQ-ARC-012 AC-01: each application-owned ABC can be faked without infrastructure.
    failures: list[str] = []

    def fake_method(*args: object, **kwargs: object) -> None:
        return None

    for filename in sorted(_manifest_modules()):
        module_name = f"yt_transcriber_bot.application.ports.{Path(filename).stem}"
        module = importlib.import_module(module_name)

        abstract_classes = [
            candidate
            for candidate in vars(module).values()
            if inspect.isclass(candidate)
            and candidate.__module__ == module.__name__
            and inspect.isabstract(candidate)
        ]

        for abstract_class in abstract_classes:
            implementations = dict.fromkeys(abstract_class.__abstractmethods__, fake_method)
            fake_type = type(
                f"_P03Fake{abstract_class.__name__}",
                (abstract_class,),
                implementations,
            )
            try:
                fake_type()
            except TypeError as exc:
                failures.append(f"{module_name}.{abstract_class.__name__}: {exc}")

    assert not failures, (
        "application port cannot be implemented by a plain infrastructure-free "
        f"test double: {failures!r}"
    )
