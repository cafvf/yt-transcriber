# Regressions for command registration and PTB lifecycle.

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import yt_transcriber_bot.__main__ as entrypoint


def test_entrypoint_registers_queue_and_callback_handlers() -> None:
    source = Path("src/yt_transcriber_bot/__main__.py").read_text()
    assert 'CommandHandler(["queue", "fila"], on_queue)' in source
    assert 'CommandHandler(["clearqueue", "cancelqueue", "limparfila"], on_clearqueue)' in source
    assert 'CommandHandler(["cancelall", "cancelartudo"], on_cancelall)' in source
    assert 'CommandHandler("healthcheck", on_healthcheck)' in source
    assert 'CommandHandler("lasterror", on_lasterror)' in source
    assert 'CommandHandler("summary", on_summary)' in source
    assert 'CommandHandler("text", on_text_export)' in source
    assert 'CommandHandler("search", on_search)' in source
    assert 'CommandHandler("export", on_export)' in source
    assert 'CommandHandler(["json", "srt", "vtt"], on_export_shortcut)' in source
    assert 'CommandHandler(["video_subs", "videosubs"], on_video_subs)' in source
    assert 'CallbackQueryHandler(on_callback, pattern=r"^rename:")' in source
    assert "MessageHandler(filters.COMMAND, on_text)" in source


def test_help_text_lists_summary_command() -> None:
    source = Path("src/yt_transcriber_bot/infrastructure/telegram/bot_adapter.py").read_text()
    assert "• /healthcheck" in source
    assert "• /lasterror" in source
    assert "• /summary [n]" in source
    assert "gera um resumo estruturado" in source
    assert "• /search <texto>" in source


def test_recovery_starts_inside_ptb_context() -> None:
    source = Path("src/yt_transcriber_bot/__main__.py").read_text()
    assert source.index("async with application:") < source.index("await adapter.start()")
    assert "await application.initialize()" not in source


def test_adapter_stops_before_ptb_shutdown() -> None:
    source = Path("src/yt_transcriber_bot/__main__.py").read_text()
    assert source.index("await adapter.stop()") < source.index("await application.updater.stop()")
    assert source.index("await adapter.stop()") < source.index("await application.stop()")


def _runtime(
    *,
    application: object,
    adapter: object,
) -> SimpleNamespace:
    return SimpleNamespace(
        application=application,
        adapter=adapter,
        audience=SimpleNamespace(allows=lambda **_kwargs: True),
        denied_audience_filter=entrypoint.filters.ALL,
    )


@pytest.mark.asyncio
async def test_adapter_stops_before_ptb_context_exits_when_startup_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class FakeApplication:
        bot = object()

        def __init__(self) -> None:
            self.updater = SimpleNamespace(stop=self.stop_updater)

        def add_handler(self, _handler: object) -> None:
            pass

        async def __aenter__(self) -> FakeApplication:
            events.append("ptb-enter")
            return self

        async def __aexit__(self, *_args: object) -> None:
            events.append("ptb-exit")

        async def stop_updater(self) -> None:
            raise AssertionError("updater was never started")

        async def stop(self) -> None:
            raise AssertionError("application was never started")

        async def start(self) -> None:
            events.append("application-start")
            raise RuntimeError("startup failed")

    class FakeAdapter:
        async def start(self) -> None:
            events.append("adapter-start")

        async def stop(self) -> None:
            events.append("adapter-stop")

    application = FakeApplication()
    adapter = FakeAdapter()
    settings = SimpleNamespace(
        logs_dir=lambda: Path("/tmp/logs"),
        telegram_allowed_user_id=1,
        credentials=SimpleNamespace(telegram_bot_token="token"),
    )
    runtime = _runtime(application=application, adapter=adapter)

    def fake_build_runtime(_settings: object, *, credentials: object) -> object:
        assert credentials is settings.credentials
        return runtime

    monkeypatch.setattr(entrypoint, "load_runtime_settings", lambda: settings)
    monkeypatch.setattr(entrypoint, "configure_runtime_logging", lambda _settings: None)
    monkeypatch.setattr(entrypoint, "_validate_environment", lambda _settings: None)
    monkeypatch.setattr(entrypoint, "build_runtime", fake_build_runtime)

    with pytest.raises(RuntimeError, match="startup failed"):
        await entrypoint._run()

    assert events.index("adapter-start") < events.index("application-start")
    assert events.index("adapter-stop") < events.index("ptb-exit")
    assert "updater-stop" not in events
    assert "application-stop" not in events


@pytest.mark.asyncio
async def test_unstarted_ptb_resources_are_not_stopped_when_adapter_start_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class FakeApplication:
        bot = object()

        def __init__(self) -> None:
            self.updater = SimpleNamespace(stop=self.stop_updater)

        def add_handler(self, _handler: object) -> None:
            pass

        async def __aenter__(self) -> FakeApplication:
            events.append("ptb-enter")
            events.append("initialize")
            return self

        async def __aexit__(self, *_args: object) -> None:
            events.append("ptb-exit")

        async def start(self) -> None:
            events.append("application-start")

        async def stop_updater(self) -> None:
            events.append("updater-stop")

        async def stop(self) -> None:
            events.append("application-stop")

    class FakeAdapter:
        async def start(self) -> None:
            events.append("adapter-start")
            raise RuntimeError("recovery failed")

        async def stop(self) -> None:
            events.append("adapter-stop")

    application = FakeApplication()
    adapter = FakeAdapter()
    settings = SimpleNamespace(
        logs_dir=lambda: Path("/tmp/logs"),
        telegram_allowed_user_id=1,
        credentials=SimpleNamespace(telegram_bot_token="token"),
    )
    runtime = _runtime(application=application, adapter=adapter)

    def fake_build_runtime(_settings: object, *, credentials: object) -> object:
        assert credentials is settings.credentials
        return runtime

    monkeypatch.setattr(entrypoint, "load_runtime_settings", lambda: settings)
    monkeypatch.setattr(entrypoint, "configure_runtime_logging", lambda _settings: None)
    monkeypatch.setattr(entrypoint, "_validate_environment", lambda _settings: None)
    monkeypatch.setattr(entrypoint, "build_runtime", fake_build_runtime)

    with pytest.raises(RuntimeError, match="recovery failed"):
        await entrypoint._run()

    assert events == [
        "ptb-enter",
        "initialize",
        "adapter-start",
        "adapter-stop",
        "ptb-exit",
    ]
