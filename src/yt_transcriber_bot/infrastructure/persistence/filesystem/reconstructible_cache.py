from __future__ import annotations

import shutil
from pathlib import Path

from yt_transcriber_bot.application.ports.cache import CacheCleanupResult, ReconstructibleCache


class FilesystemReconstructibleCache(ReconstructibleCache):
    def __init__(
        self,
        roots: tuple[Path, ...],
        *,
        protected_paths: tuple[Path, ...] = (),
    ) -> None:
        if not roots:
            raise ValueError("at least one reconstructible cache root is required")
        expanded = tuple(root.expanduser() for root in roots)
        if any(root.is_symlink() for root in expanded if root.exists()):
            raise ValueError("unsafe reconstructible cache root")
        resolved = tuple(root.resolve(strict=False) for root in expanded)
        protected = tuple(path.expanduser().resolve(strict=False) for path in protected_paths)
        unsafe = {Path("/"), Path.home().resolve(strict=False)}
        if any(root in unsafe or len(root.parts) < 2 for root in resolved):
            raise ValueError("unsafe reconstructible cache root")
        if any(_paths_overlap(root, item) for root in resolved for item in protected):
            raise ValueError("reconstructible cache overlaps protected application data")
        for index, root in enumerate(resolved):
            if any(_paths_overlap(root, other) for other in resolved[index + 1 :]):
                raise ValueError("ambiguous reconstructible cache roots")
        self._roots = resolved

    def clear(self) -> CacheCleanupResult:
        files = dirs = failures = 0
        for root in self._roots:
            if not root.exists():
                continue
            if not root.is_dir() or root.is_symlink():
                failures += 1
                continue
            for child in tuple(root.iterdir()):
                try:
                    if child.is_symlink() or child.is_file():
                        child.unlink()
                        files += 1
                    elif child.is_dir():
                        files += sum(1 for item in child.rglob("*") if item.is_file())
                        shutil.rmtree(child)
                        dirs += 1
                except OSError:
                    failures += 1
        return CacheCleanupResult(files, dirs, failures)


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents
