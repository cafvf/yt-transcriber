#!/usr/bin/env python3
from __future__ import annotations

import argparse
import tomllib
from pathlib import Path


def _name(value: str) -> str:
    return re_split(value).lower()


def re_split(value: str) -> str:
    for marker in ("[", "<", ">", "=", "!", "~", ";"):
        value = value.split(marker, 1)[0]
    return value.strip()


def audit(root: Path) -> list[str]:
    problems: list[str] = []
    with (root / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)
    runtime = list(project["project"].get("dependencies", []))
    dev = list(project.get("dependency-groups", {}).get("dev", []))
    runtime_names = {_name(item) for item in runtime}
    dev_names = {_name(item) for item in dev}
    leaked = sorted({"pre-commit", "pytest", "ruff", "mypy"} & runtime_names)
    if leaked:
        problems.append(f"development tools leaked into runtime: {leaked!r}")
    if "pre-commit" not in dev_names:
        problems.append("pre-commit missing from dev group")
    if not any(item.startswith("yt-dlp[default]") for item in runtime):
        problems.append("runtime must keep yt-dlp[default]")
    readiness = (
        root / "src/yt_transcriber_bot/application/services/youtube_runtime_readiness.py"
    ).read_text(encoding="utf-8")
    for marker in (
        "DENO_MINIMUM_VERSION = (2, 3, 0)",
        "NODE_MINIMUM_VERSION = (22, 0, 0)",
        "yt_dlp_ejs",
        "assess_youtube_runtime",
    ):
        if marker not in readiness:
            problems.append(f"readiness contract missing {marker!r}")
    health = (root / "src/yt_transcriber_bot/application/services/healthcheck.py").read_text(
        encoding="utf-8"
    )
    if "assess_youtube_runtime(facts)" not in health:
        problems.append("healthcheck does not use readiness")
    if 'module == "yt_dlp_ejs" and module not in facts.module_available' in health:
        problems.append("healthcheck still skips EJS")
    probe = (
        root / "src/yt_transcriber_bot/infrastructure/operational/health_environment_probe.py"
    ).read_text(encoding="utf-8")
    if "probe_executable_version" not in probe or "executable_versions=" not in probe:
        problems.append("probe does not capture executable versions")
    runtime_health_test = (
        root / "tests/unit/application/services/test_youtube_runtime_healthcheck.py"
    ).read_text(encoding="utf-8")
    if "executable_versions" not in runtime_health_test:
        problems.append("YouTube runtime healthcheck fake lacks executable versions")
    if '"v22.0.0" if self._node else None' not in runtime_health_test:
        problems.append("YouTube runtime healthcheck fake lacks Node version evidence")
    if '"deno 2.3.0" if self._deno else None' not in runtime_health_test:
        problems.append("YouTube runtime healthcheck fake lacks Deno version evidence")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    args = parser.parse_args()
    problems = audit(Path(args.repo).resolve())
    for item in problems:
        print(f"[FAIL] {item}")
    if problems:
        print(f"GATE C2 RUNTIME VIOLATIONS: {len(problems)}")
        return 1
    print("[PASS] dev tooling separated from runtime dependencies")
    print("[PASS] yt-dlp[default] owns yt-dlp-ejs installation")
    print("[PASS] Deno >= 2.3.0 / Node >= 22.0.0 readiness contract")
    print("GATE C2 RUNTIME VIOLATIONS: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
