#!/usr/bin/env python3
"""Read-only PLAN-007 C1 configuration-boundary audit."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path

CREDENTIAL_FIELDS = {
    "telegram_bot_token",
    "hf_token",
    "summary_api_key",
    "youtube_cookies_file",
    "youtube_cookies_browser",
}


@dataclass(frozen=True, slots=True)
class Violation:
    code: str
    path: str
    message: str


def _read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def _class_annotated_fields(path: Path, class_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {
                stmt.target.id
                for stmt in node.body
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
            }
    return set()


def audit(root: Path) -> list[Violation]:
    violations: list[Violation] = []

    app_rel = "src/yt_transcriber_bot/application/config.py"
    app = _read(root, app_rel)
    for forbidden in (
        "find_project_root",
        "resolve_settings_env_file",
        "get_forced_settings_env_file",
        "pyproject.toml",
        "Path.cwd()",
        "SETTINGS_ENV_FILE_ENV_VAR",
    ):
        if forbidden in app:
            violations.append(
                Violation(
                    "GC1-APP-DISCOVERY",
                    app_rel,
                    f"application config still owns runtime discovery marker {forbidden!r}",
                )
            )

    runtime_rel = "src/yt_transcriber_bot/configuration/runtime_settings.py"
    runtime = _read(root, runtime_rel)
    for required in (
        'PRODUCTION_ENV_FILE = Path("/etc/yt-transcriber-bot/env")',
        "RuntimeSettingsSourceKind",
        "EXPLICIT_ENV_FILE",
        "DEVELOPMENT_DOTENV",
        "PROCESS_ENVIRONMENT",
        "find_development_checkout_root",
        "resolve_runtime_settings_source",
        "load_runtime_settings",
    ):
        if required not in runtime:
            violations.append(
                Violation("GC1-RUNTIME-CONTRACT", runtime_rel, f"missing {required!r}")
            )
    if 'Path.cwd() / ".env"' in runtime:
        violations.append(
            Violation(
                "GC1-CWD-DOTENV",
                runtime_rel,
                "installed runtime still has an implicit CWD/.env fallback",
            )
        )

    main_rel = "src/yt_transcriber_bot/__main__.py"
    main_text = _read(root, main_rel)
    if "settings = load_runtime_settings()" not in main_text:
        violations.append(
            Violation(
                "GC1-MAIN-LOADER",
                main_rel,
                "runtime entry point does not use load_runtime_settings()",
            )
        )

    credentials_rel = "src/yt_transcriber_bot/configuration/credentials.py"
    declared = _class_annotated_fields(root / credentials_rel, "ProviderCredentials")
    missing = CREDENTIAL_FIELDS - declared
    if missing:
        violations.append(
            Violation(
                "GC1-CREDENTIAL-OWNER",
                credentials_rel,
                f"ProviderCredentials is missing canonical fields: {sorted(missing)!r}",
            )
        )

    # Declaration ownership is intentionally different from adapter injection
    # parameters such as hf_token.
    for path in sorted((root / "src/yt_transcriber_bot/configuration").glob("*.py")):
        if path.name == "credentials.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for class_node in tree.body:
            if not isinstance(class_node, ast.ClassDef):
                continue
            fields = {
                stmt.target.id
                for stmt in class_node.body
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
            }
            duplicate = fields & CREDENTIAL_FIELDS
            if duplicate:
                violations.append(
                    Violation(
                        "GC1-CREDENTIAL-DUPLICATE-OWNER",
                        path.relative_to(root).as_posix(),
                        f"class {class_node.name} redeclares credential fields {sorted(duplicate)!r}",
                    )
                )

    service_rel = "deploy/yt-transcriber-bot.service"
    service = _read(root, service_rel)
    for required in (
        "EnvironmentFile=/etc/yt-transcriber-bot/env",
        "UMask=0077",
    ):
        if required not in service:
            violations.append(Violation("GC1-PRODUCTION-ENV", service_rel, f"missing {required!r}"))

    host_rel = "scripts/ops/systemd_host_preflight.py"
    host = _read(root, host_rel)
    if "stat.S_IMODE(mode) & 0o077 == 0" not in host:
        violations.append(
            Violation(
                "GC1-PERMISSIONS",
                host_rel,
                "systemd env-file preflight no longer enforces restrictive mode",
            )
        )

    hex_rel = "tests/conformance/test_hexagonal_dependencies.py"
    hex_text = _read(root, hex_rel)
    if '"application/config.py"' in hex_text:
        violations.append(
            Violation(
                "GC1-APPLICATION-IO",
                hex_rel,
                "application/config.py remains a governed direct-I/O hotspot after C1",
            )
        )

    consumers = []
    stale_imports = {
        "find_project_root",
        "resolve_settings_env_file",
        "get_forced_settings_env_file",
        "SETTINGS_ENV_FILE_ENV_VAR",
    }
    for base in ("src", "tests", "scripts"):
        for path in (root / base).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            imported: set[str] = set()
            for ast_node in ast.walk(tree):
                if (
                    isinstance(ast_node, ast.ImportFrom)
                    and ast_node.level == 0
                    and ast_node.module == "yt_transcriber_bot.application.config"
                ):
                    imported.update(alias.name for alias in ast_node.names)
            if imported & stale_imports:
                consumers.append(path.relative_to(root).as_posix())
    if consumers:
        violations.append(
            Violation(
                "GC1-STALE-CONSUMER",
                "src/tests/scripts",
                f"stale application-config discovery consumers: {sorted(consumers)!r}",
            )
        )

    for path in sorted((root / "tests").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        entrypoint_aliases: set[str] = set()
        for ast_node in tree.body:
            if not isinstance(ast_node, ast.Import):
                continue
            for alias in ast_node.names:
                if alias.name == "yt_transcriber_bot.__main__":
                    entrypoint_aliases.add(alias.asname or alias.name)
        if not entrypoint_aliases:
            continue

        for ast_node in ast.walk(tree):
            if not isinstance(ast_node, ast.Call) or len(ast_node.args) < 2:
                continue
            function = ast_node.func
            if not isinstance(function, ast.Attribute) or function.attr != "setattr":
                continue
            target = ast_node.args[0]
            attribute = ast_node.args[1]
            if (
                isinstance(target, ast.Name)
                and target.id in entrypoint_aliases
                and isinstance(attribute, ast.Constant)
                and attribute.value == "AppSettings"
            ):
                violations.append(
                    Violation(
                        "GC1-STALE-ENTRYPOINT-SEAM",
                        path.relative_to(root).as_posix(),
                        "test monkeypatches entrypoint.AppSettings after runtime construction moved to load_runtime_settings",
                    )
                )

    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    args = parser.parse_args()
    root = Path(args.repo).resolve()
    violations = audit(root)
    if violations:
        for item in violations:
            print(f"[FAIL] {item.code} {item.path}: {item.message}")
        print(f"GATE C1 CONFIGURATION VIOLATIONS: {len(violations)}")
        return 1
    print("[PASS] application config owns no runtime discovery")
    print("[PASS] runtime settings source contract")
    print("[PASS] installed runtime has no implicit CWD/.env fallback")
    print("[PASS] ProviderCredentials is the declaration owner")
    print("[PASS] production EnvironmentFile and restrictive mode policy")
    print("[PASS] Gate B application I/O hotspot resolved")
    print("GATE C1 CONFIGURATION VIOLATIONS: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
