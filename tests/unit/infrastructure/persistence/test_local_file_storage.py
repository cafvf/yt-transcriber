"""Testes do ``LocalFileStorage``."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from yt_transcriber_bot.infrastructure.persistence.filesystem.local_file_storage import (
    LocalFileStorage,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def storage() -> LocalFileStorage:
    return LocalFileStorage()


class TestLocalFileStorage:
    def test_write_and_read_text(self, storage: LocalFileStorage, tmp_path: Path) -> None:
        path = tmp_path / "sub" / "x.txt"
        storage.write_text(path, "hello")
        assert storage.read_text(path) == "hello"

    def test_write_creates_parent_dirs(self, storage: LocalFileStorage, tmp_path: Path) -> None:
        path = tmp_path / "a" / "b" / "c.txt"
        storage.write_text(path, "data")
        assert path.parent.exists()

    def test_exists_true_for_existing(self, storage: LocalFileStorage, tmp_path: Path) -> None:
        path = tmp_path / "x.txt"
        path.write_text("z")
        assert storage.exists(path)

    def test_exists_false_for_missing(self, storage: LocalFileStorage, tmp_path: Path) -> None:
        assert not storage.exists(tmp_path / "missing.txt")

    def test_delete_removes_file(self, storage: LocalFileStorage, tmp_path: Path) -> None:
        path = tmp_path / "x.txt"
        path.write_text("z")
        storage.delete(path)
        assert not path.exists()

    def test_delete_missing_silent(self, storage: LocalFileStorage, tmp_path: Path) -> None:
        storage.delete(tmp_path / "nope.txt")  # não levanta

    def test_ensure_dir_creates_recursively(
        self, storage: LocalFileStorage, tmp_path: Path
    ) -> None:
        path = tmp_path / "a" / "b" / "c"
        storage.ensure_dir(path)
        assert path.exists()
        assert path.is_dir()

    def test_ensure_dir_idempotent(self, storage: LocalFileStorage, tmp_path: Path) -> None:
        path = tmp_path / "x"
        storage.ensure_dir(path)
        storage.ensure_dir(path)  # não levanta

    def test_list_files_oldest_first(self, storage: LocalFileStorage, tmp_path: Path) -> None:
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        c = tmp_path / "c.txt"
        a.write_text("1")
        os.utime(a, (time.time() - 100, time.time() - 100))
        b.write_text("2")
        os.utime(b, (time.time() - 50, time.time() - 50))
        c.write_text("3")
        result = storage.list_files_oldest_first(tmp_path)
        assert [p.name for p in result] == ["a.txt", "b.txt", "c.txt"]

    def test_list_files_excludes_subdirs(self, storage: LocalFileStorage, tmp_path: Path) -> None:
        (tmp_path / "x.txt").write_text("a")
        (tmp_path / "subdir").mkdir()
        result = storage.list_files_oldest_first(tmp_path)
        assert [p.name for p in result] == ["x.txt"]

    def test_list_files_missing_dir_returns_empty(
        self, storage: LocalFileStorage, tmp_path: Path
    ) -> None:
        assert storage.list_files_oldest_first(tmp_path / "nope") == []
