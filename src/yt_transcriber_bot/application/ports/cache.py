from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CacheCleanupResult:
    removed_files: int
    removed_directories: int
    failures: int = 0


class ReconstructibleCache(ABC):
    @abstractmethod
    def clear(self) -> CacheCleanupResult: ...
