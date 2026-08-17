from __future__ import annotations

from pathlib import Path

import pytest

from yt_transcriber_bot.application.ports.staging_cleanup import StagingCleanupRefusedError
from yt_transcriber_bot.infrastructure.persistence.filesystem.private_staging_cleanup import (
    FilesystemPrivateStagingCleanup,
)


def test_private_staging_cleanup_removes_flat_owned_directory(tmp_path: Path) -> None:
    root = tmp_path / "downloads"
    target = root / "job"
    target.mkdir(parents=True)
    (target / "audio.ogg").write_bytes(b"x")

    FilesystemPrivateStagingCleanup(root).clear(target)

    assert not target.exists()


def test_private_staging_cleanup_refuses_root_and_outside_target(tmp_path: Path) -> None:
    root = tmp_path / "downloads"
    root.mkdir()
    cleanup = FilesystemPrivateStagingCleanup(root)
    with pytest.raises(StagingCleanupRefusedError):
        cleanup.clear(root)
    with pytest.raises(StagingCleanupRefusedError):
        cleanup.clear(tmp_path / "other")
