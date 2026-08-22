from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_gate_b_architecture_contract() -> None:
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts" / "quality" / "gate_b_architecture_rules.py"
    completed = subprocess.run(
        [sys.executable, str(script), str(root)],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
