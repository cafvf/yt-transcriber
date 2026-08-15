"""Security permissions for generated operational evidence."""

from __future__ import annotations

import importlib.util
import os
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT_PATH = Path("scripts/ops/create_phase4_phase8_evidence.py")


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("create_phase4_phase8_evidence", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission contract")
def test_generated_operational_evidence_uses_private_modes(tmp_path: Path) -> None:
    script = _load_script()
    output_dir = tmp_path / "evidence"

    output_path = script.write_report(
        output_dir=output_dir,
        generated_at=datetime(2026, 8, 15, 12, tzinfo=UTC),
        operator="operator",
        host="host",
    )

    assert output_dir.stat().st_mode & 0o777 == 0o700
    assert output_path.stat().st_mode & 0o777 == 0o600
