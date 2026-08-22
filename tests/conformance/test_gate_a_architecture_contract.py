from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_gate_a_architecture_contract() -> None:
    root = Path(__file__).resolve().parents[2]
    auditor = root / "scripts" / "quality" / "gate_a_architecture_rules.py"
    result = subprocess.run(
        [sys.executable, str(auditor), str(root)],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout
