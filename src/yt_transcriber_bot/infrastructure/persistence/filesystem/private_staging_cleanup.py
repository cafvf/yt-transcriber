from __future__ import annotations

from contextlib import suppress
from pathlib import Path

from yt_transcriber_bot.application.ports.staging_cleanup import (
    PrivateStagingCleanup,
    StagingCleanupRefusedError,
)


class FilesystemPrivateStagingCleanup(PrivateStagingCleanup):
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def clear(self, directory: Path) -> None:
        target = directory.resolve()
        if target == self._root or self._root not in target.parents:
            raise StagingCleanupRefusedError("staging cleanup target is outside owned root")
        if not target.exists():
            return
        for child in target.iterdir():
            if child.is_file() or child.is_symlink():
                with suppress(FileNotFoundError):
                    child.unlink()
        with suppress(FileNotFoundError):
            target.rmdir()
