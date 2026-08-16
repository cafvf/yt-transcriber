"""Runtime logging mechanism tests after REQ-ARC-009 ownership split."""

from __future__ import annotations

import logging
from pathlib import Path

from yt_transcriber_bot.infrastructure.logging.runtime_logging import (
    configure_runtime_logging,
)


def test_configure_logging_suppresses_polling_noise(tmp_path: Path) -> None:
    configure_runtime_logging(tmp_path, max_bytes=1_000_000, backup_count=2)

    assert (tmp_path / "bot.log").exists()
    assert logging.getLogger().level == logging.INFO
    for logger_name in (
        "httpx",
        "httpcore",
        "telegram",
        "telegram.ext",
        "telegram.request",
    ):
        assert logging.getLogger(logger_name).level >= logging.WARNING
