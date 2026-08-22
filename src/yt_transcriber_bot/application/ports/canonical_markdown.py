from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class CanonicalMarkdownWriter(ABC):
    @abstractmethod
    def write(self, path: Path, content: str) -> None:
        """Atomically replace a known canonical Markdown path."""

    @abstractmethod
    def write_new(self, preferred_path: Path, content: str, *, collision_key: str) -> Path:
        """Create a new Markdown artifact without overwriting an existing artifact."""
