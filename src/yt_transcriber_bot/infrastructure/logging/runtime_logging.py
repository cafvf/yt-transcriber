from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from yt_transcriber_bot.infrastructure.filesystem_safety import (
    ensure_private_directory,
    ensure_private_file,
)


def configure_runtime_logging(logs_dir: Path, *, max_bytes: int, backup_count: int) -> None:
    ensure_private_directory(logs_dir)
    path = logs_dir / "bot.log"
    file_handler = RotatingFileHandler(
        path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    ensure_private_file(path)
    console = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    file_handler.setFormatter(formatter)
    console.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [file_handler, console]
    for noisy in (
        "httpx",
        "httpcore",
        "telegram",
        "telegram.ext",
        "telegram.request",
        "apscheduler",
        "urllib3",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)
