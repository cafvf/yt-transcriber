#!/usr/bin/env python3
"""Local secret guard for pre-commit.

This script is intentionally dependency-free.  It catches project-specific leaks
before Gitleaks/TruffleHog are available, especially `.env`, YouTube cookies,
local databases, logs and common token formats.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

MAX_TEXT_BYTES = 2_000_000
DEFAULT_MAX_KB = 2048

ALLOWLIST_PATHS = {
    ".env.example",
}

BLOCKED_PATH_GLOBS = [
    ".env",
    ".env.*",
    "*.env",
    "*.env.*",
    "cookies.txt",
    "*cookies*.txt",
    "*.cookies",
    "*.db",
    "*.db-shm",
    "*.db-wal",
    "*.sqlite",
    "*.sqlite3",
    "*.log",
    "data/**",
    "downloads/**",
    "processed/**",
    "transcripts/**",
    "logs/**",
    "models/**",
]

SECRET_REGEXES: list[tuple[str, re.Pattern[str]]] = [
    (
        "telegram-bot-token",
        re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b"),
    ),
    (
        "huggingface-token",
        re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),
    ),
    (
        "openai-api-key",
        re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    ),
    (
        "github-token",
        re.compile(
            r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b"
        ),
    ),
    (
        "google-api-key",
        re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    ),
    (
        "netscape-cookie-file",
        re.compile(r"(?i)#\s*Netscape\s+HTTP\s+Cookie\s+File|\.youtube\.com\s+TRUE\s+/"),
    ),
]

SENSITIVE_ASSIGNMENT = re.compile(
    r"(?m)^\s*"
    r"(?P<key>TELEGRAM_BOT_TOKEN|TELEGRAM_ALLOWED_USER_ID|HF_TOKEN|OPENAI_API_KEY|"
    r"ANTHROPIC_API_KEY|GOOGLE_API_KEY|DEEPGRAM_API_KEY|ASSEMBLYAI_API_KEY|"
    r"YOUTUBE_COOKIES_FILE|YOUTUBE_COOKIES_BROWSER)"
    r"\s*=\s*['\"]?(?P<value>[^'\"\s#]+)"
)

PLACEHOLDER_MARKERS = (
    "REPLACE",
    "CHANGE",
    "EXAMPLE",
    "DUMMY",
    "FAKE",
    "PLACEHOLDER",
    "COLE_AQUI",
    "SEU_",
    "SUA_",
    "USUARIO",
    "USUÁRIO",
    "CAMINHO",
    "TOKEN_DO_BOTFATHER",
    "HF_SEU_TOKEN",
)

SAFE_EXAMPLE_VALUES = {
    "",
    "0",
    "123456789",
    "true",
    "false",
    "auto",
    "medium",
    "large-v3",
    "inesc-id/WhisperLv3-X-PT-All",
}


def _repo_root() -> Path:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True)
        return Path(out.strip())
    except Exception:
        return Path.cwd()


def _staged_files() -> list[str]:
    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            text=True,
        )
        return [line.strip() for line in out.splitlines() if line.strip()]
    except Exception:
        return []


def _normalize(path: str | Path) -> str:
    return Path(path).as_posix().lstrip("./")


def _is_allowlisted(path: str) -> bool:
    return path in ALLOWLIST_PATHS


def _is_blocked_path(path: str) -> bool:
    if _is_allowlisted(path):
        return False
    return any(fnmatch.fnmatch(path, pattern) for pattern in BLOCKED_PATH_GLOBS)


def _is_binary(raw: bytes) -> bool:
    if b"\x00" in raw:
        return True
    # Conservative heuristic: if decoding fails badly, treat as binary.
    try:
        raw.decode("utf-8")
        return False
    except UnicodeDecodeError:
        return True


def _is_placeholder(value: str) -> bool:
    v = value.strip().strip("'\"")
    if v in SAFE_EXAMPLE_VALUES:
        return True
    upper = v.upper()
    return any(marker in upper for marker in PLACEHOLDER_MARKERS)


def _scan_text(path: str, text: str) -> list[str]:
    problems: list[str] = []

    for name, regex in SECRET_REGEXES:
        if regex.search(text):
            problems.append(f"{path}: possível segredo detectado por padrão '{name}'")

    for match in SENSITIVE_ASSIGNMENT.finditer(text):
        key = match.group("key")
        value = match.group("value")
        if _is_placeholder(value):
            continue
        if path == ".env.example":
            # `.env.example` may document keys, but never real values.
            problems.append(
                f"{path}: valor não-placeholder para {key}; use REPLACE_ME/123456789/etc."
            )
        elif _is_allowlisted(path):
            continue
        else:
            problems.append(
                f"{path}: possível valor real para {key}. Use .env local, não versionado."
            )

    return problems


def _git_visible_files() -> list[str]:
    try:
        out = subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            text=True,
        )
        return [line.strip() for line in out.splitlines() if line.strip()]
    except Exception:
        files: list[str] = []
        for root, dirs, names in os.walk("."):
            dirs[:] = [d for d in dirs if d not in {".git", ".venv", "venv", "__pycache__"}]
            files.extend(_normalize(Path(root) / name) for name in names)
        return files


def _iter_paths(args: argparse.Namespace, filenames: list[str]) -> Iterable[str]:
    if args.all:
        for name in _git_visible_files():
            yield _normalize(name)
        return
    if filenames:
        for name in filenames:
            yield _normalize(name)
        return
    for name in _staged_files():
        yield _normalize(name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Block project-specific secrets before commit.")
    parser.add_argument(
        "--all", action="store_true", help="scan the working tree instead of staged files"
    )
    parser.add_argument("--max-kb", type=int, default=DEFAULT_MAX_KB)
    parser.add_argument("filenames", nargs="*")
    args = parser.parse_args(argv)

    root = _repo_root()
    os.chdir(root)

    problems: list[str] = []
    seen: set[str] = set()

    for rel in _iter_paths(args, args.filenames):
        if rel in seen:
            continue
        seen.add(rel)
        path = Path(rel)
        if not path.exists() or not path.is_file():
            continue

        if _is_blocked_path(rel):
            problems.append(f"{rel}: arquivo/diretório sensível não deve ser versionado")
            continue

        size = path.stat().st_size
        if size > args.max_kb * 1024:
            problems.append(
                f"{rel}: arquivo grande demais para commit ({size // 1024} KB > {args.max_kb} KB)"
            )
            continue

        raw = path.read_bytes()[:MAX_TEXT_BYTES]
        if _is_binary(raw):
            continue
        text = raw.decode("utf-8", errors="ignore")
        problems.extend(_scan_text(rel, text))

    if problems:
        print("\n[security] Commit bloqueado por possíveis dados sensíveis:\n", file=sys.stderr)
        for item in problems:
            print(f"- {item}", file=sys.stderr)
        print(
            "\nCorrija removendo o arquivo/valor do stage. Use .env local e .env.example com placeholders.",
            file=sys.stderr,
        )
        return 1

    print("[security] Scanner local: nenhum segredo óbvio encontrado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
