"""Security regressions for runtime logging permissions."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

from yt_transcriber_bot.infrastructure.logging.runtime_logging import (
    configure_runtime_logging,
)


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission contract")
def test_runtime_log_file_and_directory_are_private(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    root = logging.getLogger()
    old_handlers = list(root.handlers)
    old_level = root.level

    try:
        configure_runtime_logging(logs, max_bytes=1_000_000, backup_count=2)
        path = logs / "bot.log"
        assert logs.stat().st_mode & 0o777 == 0o700
        assert path.stat().st_mode & 0o777 == 0o600
    finally:
        for handler in root.handlers:
            if handler not in old_handlers:
                handler.close()
        root.handlers = old_handlers
        root.setLevel(old_level)
