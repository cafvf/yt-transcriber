"""Security tests for owned-root filesystem containment."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from yt_transcriber_bot.application.services.filesystem_safety import (
    PRIVATE_DIR_MODE,
    PRIVATE_FILE_MODE,
    UnsafeFilesystemTargetError,
    ensure_private_directory,
    ensure_private_file,
    resolve_owned_target,
    unlink_owned_file,
)


def test_owned_target_inside_root_is_accepted(tmp_path: Path) -> None:
    root = tmp_path / "owned"
    root.mkdir()
    target = root / "nested" / "file.txt"

    assert resolve_owned_target(target, (root,)) == target.resolve()


def test_parent_traversal_outside_owned_root_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "owned"
    root.mkdir()
    outside = tmp_path / "outside.txt"

    with pytest.raises(UnsafeFilesystemTargetError):
        resolve_owned_target(root / ".." / outside.name, (root,))


def test_symlink_escape_is_refused_before_unlink(tmp_path: Path) -> None:
    root = tmp_path / "owned"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("keep", encoding="utf-8")
    link = root / "link.txt"
    link.symlink_to(outside)

    with pytest.raises(UnsafeFilesystemTargetError):
        unlink_owned_file(link, (root,))

    assert link.is_symlink()
    assert outside.read_text(encoding="utf-8") == "keep"


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission contract")
def test_sensitive_directory_and_file_modes_are_restrictive(tmp_path: Path) -> None:
    directory = tmp_path / "private"
    ensure_private_directory(directory)
    path = directory / "evidence.txt"
    path.write_text("private", encoding="utf-8")
    ensure_private_file(path)

    assert directory.stat().st_mode & 0o777 == PRIVATE_DIR_MODE
    assert path.stat().st_mode & 0o777 == PRIVATE_FILE_MODE
