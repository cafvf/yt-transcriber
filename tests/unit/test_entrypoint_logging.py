"""Entrypoint logging configuration tests."""

from __future__ import annotations

import logging
from pathlib import Path

from yt_transcriber_bot.__main__ import _configure_logging


def test_configure_logging_suppresses_polling_noise(tmp_path: Path) -> None:
    _configure_logging(tmp_path)

    assert (tmp_path / "bot.log").exists()
    assert logging.getLogger().level == logging.INFO
    for logger_name in ("httpx", "httpcore", "telegram", "telegram.ext", "telegram.request"):
        assert logging.getLogger(logger_name).level >= logging.WARNING
