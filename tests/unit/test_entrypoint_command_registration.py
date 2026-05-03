"""Regressões de registro dos comandos no entrypoint real."""

from __future__ import annotations

from pathlib import Path


def test_entrypoint_registers_queue_and_callback_handlers() -> None:
    source = Path("src/yt_transcriber_bot/__main__.py").read_text()
    assert 'CommandHandler(["queue", "fila"], on_queue)' in source
    assert 'CommandHandler(["clearqueue", "cancelqueue", "limparfila"], on_clearqueue)' in source
    assert 'CommandHandler(["cancelall", "cancelartudo"], on_cancelall)' in source
    assert 'CommandHandler("export", on_export)' in source
    assert 'CommandHandler(["json", "srt", "vtt"], on_export_shortcut)' in source
    assert 'CommandHandler(["video_subs", "videosubs"], on_video_subs)' in source
    assert 'CallbackQueryHandler(on_callback, pattern=r"^rename:")' in source
    assert 'MessageHandler(filters.COMMAND, on_text)' in source
