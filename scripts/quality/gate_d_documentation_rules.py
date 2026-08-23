#!/usr/bin/env python3
"""Documentation-to-implementation conformance for PLAN-007 Gate D."""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = (
    "README.md",
    "docs/01-contrato-funcional.md",
    "docs/02-arquitetura.md",
    "docs/03-manual-de-uso.md",
    "docs/04-manual-de-instalacao.md",
    "docs/06-funcionalidades-futuras.md",
    "docs/07-glossario-e-decisoes.md",
    "docs/08-seguranca-e-segredos.md",
    "docs/09-production-readiness.md",
    "docs/10-recovery-semantics-adr.md",
    "docs/11-operator-runbook.md",
    "docs/12-deprecacoes-e-compatibilidade.md",
)
PRODUCTION_DOCS = (
    "README.md",
    "docs/04-manual-de-instalacao.md",
    "docs/08-seguranca-e-segredos.md",
    "docs/09-production-readiness.md",
    "docs/11-operator-runbook.md",
)
HISTORICAL_PUBLIC_DOCS = (
    "docs/00-auditoria-da-documentacao.md",
    "docs/05-plano-de-execucao.md",
    "docs/gate-reports",
    "docs/patches",
)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def fail(message: str) -> None:
    raise AssertionError(message)


def systemd_contract() -> dict[str, str]:
    text = read("deploy/yt-transcriber-bot.service")
    values: dict[str, str] = {}
    for key in ("WorkingDirectory", "EnvironmentFile", "ExecStart", "StateDirectory"):
        match = re.search(rf"^{key}=(.+)$", text, re.MULTILINE)
        if match is None:
            fail(f"service missing {key}")
        values[key] = match.group(1).strip()
    return values


def check_local_links() -> None:
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    root = ROOT.resolve()
    for doc in CANONICAL:
        source = ROOT / doc
        for raw_target in pattern.findall(source.read_text(encoding="utf-8")):
            target = raw_target.split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (source.parent / target).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                fail(f"link escapes repo: {doc} -> {raw_target}")
            if not resolved.exists():
                fail(f"broken local link: {doc} -> {raw_target}")


def check_layout() -> None:
    for path in CANONICAL:
        if not (ROOT / path).is_file():
            fail(f"missing canonical doc: {path}")
    for path in HISTORICAL_PUBLIC_DOCS:
        if (ROOT / path).exists():
            fail(f"historical public doc remains: {path}")
    for path in (
        "specs/007-production-coherence/REQUIREMENTS.md",
        "specs/007-production-coherence/TASKS.md",
        "specs/001-use-cases/README.md",
    ):
        if not (ROOT / path).is_file():
            fail(f"engineering contract absent: {path}")


def check_systemd_docs() -> None:
    contract = systemd_contract()
    for path in (
        "README.md",
        "docs/04-manual-de-instalacao.md",
        "docs/09-production-readiness.md",
        "docs/11-operator-runbook.md",
    ):
        text = read(path)
        for key, value in contract.items():
            if f"{key}={value}" not in text:
                fail(f"{path} does not mirror {key}")


def check_package_metadata() -> None:
    pyproject = tomllib.loads(read("pyproject.toml"))
    if pyproject["project"]["requires-python"] != ">=3.11,<3.13":
        fail("Python metadata drift")
    script = pyproject["project"]["scripts"].get("yt-transcriber-bot")
    if script != "yt_transcriber_bot.__main__:main":
        fail("console script drift")


def check_current_configuration_names() -> None:
    for path in PRODUCTION_DOCS:
        text = read(path)
        for stale in ("uv run python -m yt_transcriber_bot", "MAX_VIDEO_DURATION_MIN=180"):
            if stale in text:
                fail(f"stale production instruction: {path}: {stale}")

    development_template = read(".env.example")
    if "MAX_VIDEO_DURATION_MIN" in development_template:
        fail("development template teaches legacy duration name")
    if "MAX_MEDIA_DURATION_MIN=180" not in development_template:
        fail("development template missing canonical duration")

    production_template = read("deploy/yt-transcriber-bot.environment.example")
    required_values = (
        "PATH=/opt/yt-transcriber-bot/venv/bin:",
        "BASE_DIR=/var/lib/yt-transcriber-bot/data",
        "MODELS_DIR=/var/lib/yt-transcriber-bot/models",
        "DB_PATH=/var/lib/yt-transcriber-bot/data/jobs.db",
    )
    for required in required_values:
        if required not in production_template:
            fail(f"production env missing {required}")


def check_deprecations() -> None:
    compatibility = read("docs/12-deprecacoes-e-compatibilidade.md")
    for term in ("MAX_VIDEO_DURATION_MIN", "MAX_MEDIA_DURATION_MIN", "uv sync --extra ml"):
        if term not in compatibility:
            fail(f"compatibility doc missing {term}")


def main() -> int:
    check_layout()
    check_systemd_docs()
    check_package_metadata()
    check_current_configuration_names()
    check_deprecations()
    check_local_links()
    print("[PASS] Gate D documentation-to-implementation conformance")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
