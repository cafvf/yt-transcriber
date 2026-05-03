#!/usr/bin/env python3
"""Run Gitleaks if available; warn and pass otherwise.

This hook is intentionally a complementary layer.  The dependency-free local
scanner blocks project-specific files and token patterns even when Gitleaks is
not installed.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Optional Gitleaks pre-commit wrapper.")
    parser.add_argument("--staged", action="store_true", help="scan staged changes")
    parser.add_argument("--all", action="store_true", help="scan repository history/working tree")
    args = parser.parse_args(argv)

    exe = shutil.which("gitleaks")
    if exe is None:
        print(
            "[security] Aviso: gitleaks não encontrado no PATH; "
            "pulando varredura complementar. O scanner local ainda foi executado. "
            "Instale gitleaks para uma camada adicional.",
            file=sys.stderr,
        )
        return 0

    config = Path(".gitleaks.toml")
    common = [exe]
    if args.staged:
        cmd = common + ["protect", "--staged", "--redact", "--verbose"]
    else:
        cmd = common + ["detect", "--source", ".", "--redact", "--verbose"]
    if config.exists():
        cmd.extend(["--config", str(config)])

    print("[security] Executando Gitleaks:", " ".join(cmd))
    completed = subprocess.run(cmd, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
