# Characterize the frozen Telegram command surface during remediation.

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

import yt_transcriber_bot.__main__ as entrypoint
from yt_transcriber_bot.infrastructure.telegram.bot_adapter import HELP_TEXT

FROZEN_COMMANDS = frozenset(
    {
        "start",
        "help",
        "transcribe",
        "pt",
        "en",
        "redo",
        "status",
        "healthcheck",
        "lasterror",
        "queue",
        "fila",
        "clearqueue",
        "cancelqueue",
        "limparfila",
        "cancel",
        "cancelall",
        "cancelartudo",
        "list",
        "search",
        "last",
        "rename",
        "summary",
        "text",
        "export",
        "json",
        "srt",
        "vtt",
        "video_subs",
        "videosubs",
        "clearcache",
    }
)

ALIAS_GROUPS = (
    frozenset({"queue", "fila"}),
    frozenset({"clearqueue", "cancelqueue", "limparfila"}),
    frozenset({"cancelall", "cancelartudo"}),
    frozenset({"json", "srt", "vtt"}),
    frozenset({"video_subs", "videosubs"}),
)


class _StopAfterRegistrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class _RegisteredCommand:
    commands: tuple[str, ...]
    callback: object


class _FakeApplication:
    bot = object()

    def __init__(self) -> None:
        self.handlers: list[object] = []
        self.updater = SimpleNamespace(stop=self._unexpected_updater_stop)

    def add_handler(self, handler: object) -> None:
        self.handlers.append(handler)

    async def __aenter__(self) -> _FakeApplication:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def start(self) -> None:
        raise AssertionError("application.start must not run in this characterization")

    async def stop(self) -> None:
        raise AssertionError("application.stop must not run in this characterization")

    async def _unexpected_updater_stop(self) -> None:
        raise AssertionError("updater.stop must not run in this characterization")


class _FakeAdapter:
    async def start(self) -> None:
        raise _StopAfterRegistrationError

    async def stop(self) -> None:
        return None


def _fake_command_handler(
    commands: str | list[str],
    callback: object,
) -> _RegisteredCommand:
    normalized = (commands,) if isinstance(commands, str) else tuple(commands)
    return _RegisteredCommand(normalized, callback)


def _ignore_handler(*_args: object, **_kwargs: object) -> object:
    return object()


@pytest.fixture
async def registered_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> list[_RegisteredCommand]:
    application = _FakeApplication()
    settings = SimpleNamespace(
        logs_dir=lambda: Path("/tmp/yt-transcriber-f0/logs"),
        telegram_allowed_user_id=1,
        credentials=SimpleNamespace(telegram_bot_token="characterization-token"),
    )
    runtime = SimpleNamespace(
        application=application,
        adapter=_FakeAdapter(),
        audience=SimpleNamespace(allows=lambda **_kwargs: True),
        denied_audience_filter=object(),
    )

    def fake_build_runtime(_settings: object, *, credentials: object) -> object:
        assert credentials is settings.credentials
        return runtime

    monkeypatch.setattr(entrypoint, "AppSettings", lambda: settings)
    monkeypatch.setattr(entrypoint, "_configure_logging", lambda _logs_dir: None)
    monkeypatch.setattr(entrypoint, "_validate_environment", lambda _settings: None)
    monkeypatch.setattr(entrypoint, "build_runtime", fake_build_runtime)
    monkeypatch.setattr(entrypoint, "CommandHandler", _fake_command_handler)
    monkeypatch.setattr(entrypoint, "CallbackQueryHandler", _ignore_handler)
    monkeypatch.setattr(entrypoint, "MessageHandler", _ignore_handler)

    with pytest.raises(_StopAfterRegistrationError):
        await entrypoint._run()

    return [handler for handler in application.handlers if isinstance(handler, _RegisteredCommand)]


def _registered_command_set(
    handlers: list[_RegisteredCommand],
) -> frozenset[str]:
    return frozenset(command for handler in handlers for command in handler.commands)


def _help_command_set() -> frozenset[str]:
    commands: set[str] = set()
    for line in HELP_TEXT.splitlines():
        match = re.match(r"^• /([a-z_]+)(?:\s|$)", line)
        if match:
            commands.add(match.group(1))
    return frozenset(commands)


@pytest.mark.asyncio
async def test_registered_commands_match_frozen_interface(
    registered_commands: list[_RegisteredCommand],
) -> None:
    assert _registered_command_set(registered_commands) == FROZEN_COMMANDS


def test_help_commands_match_frozen_interface() -> None:
    assert _help_command_set() == FROZEN_COMMANDS


@pytest.mark.asyncio
async def test_registration_and_help_expose_the_same_commands(
    registered_commands: list[_RegisteredCommand],
) -> None:
    assert _registered_command_set(registered_commands) == _help_command_set()


@pytest.mark.asyncio
async def test_frozen_alias_groups_share_one_registered_handler(
    registered_commands: list[_RegisteredCommand],
) -> None:
    callback_by_command: dict[str, object] = {}
    for handler in registered_commands:
        for command in handler.commands:
            callback_by_command[command] = handler.callback

    for aliases in ALIAS_GROUPS:
        callbacks = {callback_by_command[command] for command in aliases}
        assert len(callbacks) == 1, f"aliases diverged: {sorted(aliases)}"
