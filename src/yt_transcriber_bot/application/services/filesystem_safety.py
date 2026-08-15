"""Narrow filesystem safety primitives used by brownfield security guardrails.

This module owns containment *policy* only. It intentionally stays small while
later architecture plans move filesystem mechanisms behind application ports.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


class UnsafeFilesystemTargetError(ValueError):
    """A destructive target is outside the explicitly owned filesystem roots."""


def resolve_owned_target(path: Path, owned_roots: Iterable[Path]) -> Path:
    """Resolve ``path`` and prove it is contained by one of ``owned_roots``.

    Existing symlinks are resolved before the containment check. Therefore a
    symlink inside an owned directory that points outside it is rejected.
    """

    candidate = path.expanduser().resolve(strict=False)
    roots = tuple(root.expanduser().resolve(strict=False) for root in owned_roots)
    if not roots:
        raise UnsafeFilesystemTargetError("no owned filesystem roots configured")
    for root in roots:
        if candidate == root or candidate.is_relative_to(root):
            return candidate
    raise UnsafeFilesystemTargetError(f"target escapes owned roots: {path}")


def unlink_owned_file(path: Path, owned_roots: Iterable[Path]) -> bool:
    """Unlink one owned regular file without following an escaping symlink."""

    roots = tuple(owned_roots)
    resolved = resolve_owned_target(path, roots)
    if path.is_symlink():
        # The resolved target has already been proven owned; unlink only the link.
        path.unlink()
        return True
    if not resolved.is_file():
        return False
    resolved.unlink()
    return True


def remove_empty_owned_dir(path: Path, owned_roots: Iterable[Path]) -> bool:
    """Remove an empty owned directory, refusing escaping symlinks."""

    roots = tuple(owned_roots)
    resolved = resolve_owned_target(path, roots)
    if path.is_symlink():
        raise UnsafeFilesystemTargetError(f"refusing symlink directory removal: {path}")
    if not resolved.is_dir():
        return False
    resolved.rmdir()
    return True


def ensure_private_directory(path: Path) -> None:
    """Create a private directory and enforce ``0700`` on POSIX hosts."""

    path.mkdir(parents=True, exist_ok=True, mode=PRIVATE_DIR_MODE)
    if os.name == "posix":
        path.chmod(PRIVATE_DIR_MODE)


def ensure_private_file(path: Path) -> None:
    """Enforce ``0600`` on an existing sensitive file on POSIX hosts."""

    if os.name == "posix" and path.exists():
        path.chmod(PRIVATE_FILE_MODE)
