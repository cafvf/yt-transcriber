"""Porta ``FileStorage`` — abstrai I/O de arquivos."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class FileStorage(ABC):
    """Operações de filesystem isoláveis para teste."""

    @abstractmethod
    def write_text(self, path: Path, content: str) -> None: ...

    @abstractmethod
    def read_text(self, path: Path) -> str: ...

    @abstractmethod
    def exists(self, path: Path) -> bool: ...

    @abstractmethod
    def delete(self, path: Path) -> None: ...

    @abstractmethod
    def ensure_dir(self, path: Path) -> None: ...

    @abstractmethod
    def list_files_oldest_first(self, directory: Path) -> list[Path]: ...
