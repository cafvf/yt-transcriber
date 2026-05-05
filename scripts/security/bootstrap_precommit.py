#!/usr/bin/env python3
"""Bootstrap local pre-commit security hooks.

This helper exists because copying a patch with shell globs such as
`cp -r yt-transcriber-bot/* .` skips dotfiles.  In that case pre-commit is
installed, but `.pre-commit-config.yaml` is missing and `pre-commit run` fails
with `InvalidConfigError: .pre-commit-config.yaml is not a file`.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True)
        return Path(out.strip())
    except Exception:
        return Path(__file__).resolve().parents[2]


def main() -> int:
    root = repo_root()
    config = root / ".pre-commit-config.yaml"
    fallback = root / "config" / "pre-commit-config.yaml"

    if not config.exists():
        if not fallback.exists():
            print(
                "[pre-commit] ERRO: não encontrei .pre-commit-config.yaml nem "
                "config/pre-commit-config.yaml.",
                file=sys.stderr,
            )
            return 1
        shutil.copy2(fallback, config)
        print(
            f"[pre-commit] Criado {config.relative_to(root)} a partir de config/pre-commit-config.yaml"
        )
    elif not config.is_file():
        print(f"[pre-commit] ERRO: {config} existe, mas não é arquivo.", file=sys.stderr)
        return 1
    else:
        print("[pre-commit] .pre-commit-config.yaml já existe.")

    try:
        import pre_commit  # noqa: F401
    except Exception:
        print(
            "[pre-commit] Aviso: módulo pre_commit não está instalado neste ambiente.\n"
            "Instale com: uv sync   ou   uv pip install -r requirements-dev.txt",
            file=sys.stderr,
        )
        return 0

    cmd = [sys.executable, "-m", "pre_commit", "install"]
    print("[pre-commit] Executando:", " ".join(cmd))
    return subprocess.run(cmd, cwd=root, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
