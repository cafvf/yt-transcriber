"""Regressões para garantir que /help documenta todos os comandos públicos."""

from __future__ import annotations

from yt_transcriber_bot.infrastructure.telegram.bot_adapter import HELP_TEXT


PUBLIC_COMMANDS = [
    "/start",
    "/help",
    "/transcribe",
    "/pt",
    "/en",
    "/redo",
    "/status",
    "/healthcheck",
    "/lasterror",
    "/queue",
    "/fila",
    "/clearqueue",
    "/cancelqueue",
    "/limparfila",
    "/cancel",
    "/cancelall",
    "/cancelartudo",
    "/list",
    "/last",
    "/rename",
    "/summary",
    "/export",
    "/json",
    "/srt",
    "/vtt",
    "/video_subs",
    "/videosubs",
    "/clearcache",
]


def _line_for(command: str) -> str:
    for line in HELP_TEXT.splitlines():
        if command in line:
            return line
    return ""


def test_help_text_mentions_every_public_command() -> None:
    missing = [command for command in PUBLIC_COMMANDS if command not in HELP_TEXT]
    assert missing == []


def test_each_public_command_has_a_description_line() -> None:
    without_description = []
    for command in PUBLIC_COMMANDS:
        line = _line_for(command)
        if "→" not in line:
            without_description.append((command, line))
    assert without_description == []


def test_help_text_groups_commands_by_user_intent() -> None:
    for section in [
        "Entrada e idioma",
        "Estado, fila e cancelamento",
        "Histórico e revisão",
        "Resumos e artefatos derivados",
        "Exportações",
        "Manutenção e ajuda",
    ]:
        assert section in HELP_TEXT
