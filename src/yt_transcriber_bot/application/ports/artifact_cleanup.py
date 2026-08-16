from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class ArtifactCleanupRefusedError(ValueError):
    pass


class OwnedArtifactCleanup(ABC):
    @abstractmethod
    def remove_file(self, path: Path) -> bool: ...

    @abstractmethod
    def remove_empty_directory(self, path: Path) -> bool: ...
