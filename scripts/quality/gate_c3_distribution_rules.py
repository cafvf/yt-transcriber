#!/usr/bin/env python3
"""Read-only PLAN-007 Gate C3 installed-distribution audit."""

from __future__ import annotations

import argparse
from pathlib import Path


def audit(root: Path) -> list[str]:
    violations: list[str] = []

    main = (root / "src/yt_transcriber_bot/__main__.py").read_text(encoding="utf-8")
    for marker in (
        "--preflight",
        "collect_runtime_preflight_facts",
        "build_runtime_preflight",
    ):
        if marker not in main:
            violations.append(f"installed CLI preflight marker missing: {marker}")
    for stale in ("uv sync", "uv lock"):
        if stale in main:
            violations.append(f"installed startup still contains dev instruction: {stale}")

    if "yt_transcriber_bot.infrastructure" in main:
        violations.append(
            "entrypoint imports infrastructure directly instead of using composition root"
        )

    composition = (root / "src/yt_transcriber_bot/composition_root.py").read_text(encoding="utf-8")
    for marker in (
        "collect_runtime_preflight_facts",
        "collect_local_runtime_preflight",
    ):
        if marker not in composition:
            violations.append(f"composition-root preflight wiring marker missing: {marker}")

    runtime_preflight = (
        root / "src/yt_transcriber_bot/application/services/runtime_preflight.py"
    ).read_text(encoding="utf-8")
    local_preflight = (
        root / "src/yt_transcriber_bot/infrastructure/operational/local_runtime_preflight.py"
    ).read_text(encoding="utf-8")

    combined = (runtime_preflight + "\n" + local_preflight).lower()
    forbidden_preflight_markers = (
        "urlopen(",
        "requests.",
        "httpx.",
        ".mkdir(",
        ".write_text(",
        "build_runtime(",
    )
    for marker in forbidden_preflight_markers:
        if marker in combined:
            violations.append(
                f"installed preflight must remain offline/read-only; found {marker!r}"
            )

    service = (root / "deploy/yt-transcriber-bot.service").read_text(encoding="utf-8")
    required_service = (
        "WorkingDirectory=/var/lib/yt-transcriber-bot",
        "StateDirectory=yt-transcriber-bot",
        "StateDirectoryMode=0700",
        "ExecStart=/opt/yt-transcriber-bot/venv/bin/yt-transcriber-bot",
        "EnvironmentFile=/etc/yt-transcriber-bot/env",
    )
    for marker in required_service:
        if marker not in service:
            violations.append(f"systemd installed-runtime marker missing: {marker}")
    for stale in (
        "uv run",
        "python -m yt_transcriber_bot",
        "/home/SEU_USUARIO/yt-transcriber-bot",
    ):
        if stale in service:
            violations.append(f"systemd still depends on checkout/dev runtime: {stale}")

    host = (root / "scripts/ops/systemd_host_preflight.py").read_text(encoding="utf-8")
    required_line = host.split("REQUIRED_BINARIES =", 1)[1].split("\n", 1)[0]
    if '"uv"' in required_line:
        violations.append("systemd host preflight still requires uv")
    for marker in (
        "exec-start-installed-console",
        "working-directory-not-source-checkout",
        "_exec_start_path",
    ):
        if marker not in host:
            violations.append(f"systemd host preflight marker missing: {marker}")

    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    if 'yt-transcriber-bot = "yt_transcriber_bot.__main__:main"' not in pyproject:
        violations.append("console script metadata missing from pyproject")

    review = (root / "specs/007-production-coherence/GATE-C-DISTRIBUTION-PROOF.md").read_text(
        encoding="utf-8"
    )
    for marker in ("P07-014", "--preflight", "unrelated CWD", "Python 3.12"):
        if marker not in review:
            violations.append(f"C3 review marker missing: {marker}")

    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    args = parser.parse_args()
    violations = audit(Path(args.repo).resolve())
    for violation in violations:
        print(f"[FAIL] {violation}")
    if violations:
        print(f"GATE C3 DISTRIBUTION VIOLATIONS: {len(violations)}")
        return 1
    print("[PASS] installed CLI exposes offline/read-only --preflight")
    print("[PASS] startup guidance is distribution-oriented")
    print("[PASS] systemd uses installed console script outside source checkout")
    print("[PASS] host preflight rejects checkout/dev execution")
    print("GATE C3 DISTRIBUTION VIOLATIONS: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
