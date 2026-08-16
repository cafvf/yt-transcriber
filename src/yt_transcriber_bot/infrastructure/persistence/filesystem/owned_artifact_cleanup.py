from __future__ import annotations

from pathlib import Path

from yt_transcriber_bot.application.ports.artifact_cleanup import (
    ArtifactCleanupRefusedError,
    OwnedArtifactCleanup,
)
from yt_transcriber_bot.infrastructure.filesystem_safety import (
    UnsafeFilesystemTargetError,
    remove_empty_owned_dir,
    unlink_owned_file,
)


class FilesystemOwnedArtifactCleanup(OwnedArtifactCleanup):
    def __init__(self, owned_roots: tuple[Path, ...]) -> None:
        if not owned_roots:
            raise ValueError("owned_roots deve conter ao menos um diretório volátil")
        self._roots = owned_roots

    def remove_file(self, path: Path) -> bool:
        try:
            return unlink_owned_file(path, self._roots)
        except UnsafeFilesystemTargetError as exc:
            raise ArtifactCleanupRefusedError(str(exc)) from exc

    def remove_empty_directory(self, path: Path) -> bool:
        try:
            return remove_empty_owned_dir(path, self._roots)
        except UnsafeFilesystemTargetError as exc:
            raise ArtifactCleanupRefusedError(str(exc)) from exc
