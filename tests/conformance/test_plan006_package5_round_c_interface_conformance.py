"""P06-009 command/help/documentation conformance evidence."""

from __future__ import annotations

import re
from pathlib import Path

from yt_transcriber_bot.infrastructure.telegram.bot_adapter import HELP_TEXT

README = Path("README.md")
PYPROJECT = Path("pyproject.toml")
MANUAL = Path("docs/03-manual-de-uso.md")
ROADMAP = Path("docs/06-funcionalidades-futuras.md")
CI = Path(".github/workflows/ci.yml")
CURRENT_INTERFACE = Path("specs/001-use-cases/interface-conformance/IC-001-CURRENT-INTERFACE.md")
REQ = Path("specs/003-atomic-requirements/REQ-FUNC-012.md")


def _entrypoint_commands() -> set[str]:
    source = Path("src/yt_transcriber_bot/__main__.py").read_text(encoding="utf-8")
    commands = set(re.findall(r'CommandHandler\("([^"]+)"', source))
    for list_literal in re.findall(r"CommandHandler\(\[([^\]]+)\]", source):
        commands.update(re.findall(r'"([^"]+)"', list_literal))
    return commands


def _help_commands() -> set[str]:
    commands: set[str] = set()
    for line in HELP_TEXT.splitlines():
        match = re.match(r"^• /([a-z_]+)(?:\s|$)", line)
        if match:
            commands.add(match.group(1))
    return commands


def _manual_current_section() -> str:
    text = MANUAL.read_text(encoding="utf-8")
    return text.split("## Funcionalidades planejadas", maxsplit=1)[0]


def _manual_future_section() -> str:
    text = MANUAL.read_text(encoding="utf-8")
    return text.split("## Funcionalidades planejadas", maxsplit=1)[1]


def test_p06_009_frozen_sources_are_traceable() -> None:
    requirement = REQ.read_text(encoding="utf-8")
    interface = CURRENT_INTERFACE.read_text(encoding="utf-8")
    assert "Command, help and documentation conformance" in requirement
    assert "Registered primary commands and aliases match help text" in interface


def test_p06_009_registered_help_and_manual_current_surface_agree() -> None:
    registered = _entrypoint_commands()
    helped = _help_commands()
    manual_current = _manual_current_section()

    assert registered == helped
    for command in registered:
        assert re.search(rf"/{re.escape(command)}\b", manual_current), command


def test_p06_009_future_features_are_not_advertised_as_current() -> None:
    registered = _entrypoint_commands()
    manual_current = _manual_current_section()
    manual_future = _manual_future_section()
    roadmap = ROADMAP.read_text(encoding="utf-8")

    assert "translate" not in registered
    assert "/translate" not in HELP_TEXT
    assert "/translate" not in manual_current
    assert "/translate" in manual_future
    assert "/translate" in roadmap

    assert "semantic" not in registered
    assert "/search semantic <texto>" not in HELP_TEXT
    assert "/search semantic <texto>" not in manual_current
    assert "/search semantic <texto>" in manual_future
    assert "/search semantic <texto>" in roadmap


def test_p06_009_package_and_readme_describe_youtube_plus_telegram_media() -> None:
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")

    description = re.search(r'^description = "([^"]+)"$', pyproject, re.MULTILINE)
    assert description is not None
    package_description = description.group(1)
    assert "Telegram" in package_description
    assert "YouTube" in package_description
    assert "áudio" in package_description

    assert "transcrever links do YouTube e mídia de áudio enviada pelo próprio usuário" in readme
    assert "Aceita links do YouTube, áudio, mensagens de voz e documentos de áudio" in readme


def test_p06_009_shipped_ci_is_not_listed_as_future() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    ci = CI.read_text(encoding="utf-8")

    assert "name: CI" in ci
    assert "pull_request:" in ci
    assert "GitHub Actions CI (`baixa`, `pequeno`)" not in roadmap
    assert "Rodar testes unitários e linters em PRs" not in roadmap


def test_current_public_docs_do_not_keep_historical_gate_report_tree() -> None:
    for path in (
        Path("docs/05-plano-de-execucao.md"),
        Path("docs/gate-reports"),
        Path("docs/patches"),
    ):
        assert not path.exists(), path

    assert Path("specs/005-tasks/PLAN-006-TASKS.md").is_file()
    assert Path("specs/006-execution/PLAN-006-CLOSURE.md").is_file()
    assert "permanecem em `specs/` como contratos de engenharia" in README.read_text(
        encoding="utf-8"
    )
