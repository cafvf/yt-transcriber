from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class CanonicalMarkdownWriter(ABC):
    @abstractmethod
    def write(self, path: Path, content: str) -> None: ...
