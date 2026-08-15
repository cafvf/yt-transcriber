"""Security regressions for entrypoint logging permissions."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

import yt_transcriber_bot.__main__ as entrypoint


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission contract")
def test_entrypoint_log_file_and_directory_are_private(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    root = logging.getLogger()
    old_handlers = list(root.handlers)
    old_level = root.level

    try:
        entrypoint._configure_logging(logs)
        path = logs / "bot.log"
        assert logs.stat().st_mode & 0o777 == 0o700
        assert path.stat().st_mode & 0o777 == 0o600
    finally:
        for handler in root.handlers:
            if handler not in old_handlers:
                handler.close()
        root.handlers = old_handlers
        root.setLevel(old_level)
