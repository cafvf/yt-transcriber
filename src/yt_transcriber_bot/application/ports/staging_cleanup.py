from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class StagingCleanupRefusedError(ValueError):
    pass


class PrivateStagingCleanup(ABC):
    @abstractmethod
    def clear(self, directory: Path) -> None: ...
