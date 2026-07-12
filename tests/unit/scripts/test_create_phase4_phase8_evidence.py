"""Tests for the Phase 4/8 operational evidence helper."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

SCRIPT_PATH = Path("scripts/ops/create_phase4_phase8_evidence.py")


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("create_phase4_phase8_evidence", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_report_includes_required_drill_sections_and_fields() -> None:
    script = _load_script()

    report = script.build_report(
        generated_at=datetime(2026, 7, 9, 12, 34, 56, tzinfo=UTC),
        operator="Operator One",
        host="test-host",
    )

    assert "# Phase 4/8 Operational Drill Evidence" in report
    assert "Generated at: 2026-07-09T12:34:56+00:00" in report
    assert "Operator: Operator One" in report
    assert "Host: test-host" in report
    assert "## Environment" in report
    assert "## Backup/Restore Rehearsal" in report
    assert "## Systemd Start/Stop/Restart/Rollback Smoke" in report
    assert "## delivery_failed Manual Recovery Rehearsal" in report
    assert "## Interrupted-Job Restart Recovery Rehearsal" in report
    assert "## Commands Run" in report
    assert "## Outcomes" in report
    assert "## Blockers" in report
    assert "## Follow-Ups" in report


def test_report_includes_command_prompts_without_claiming_execution() -> None:
    script = _load_script()

    report = script.build_report(
        generated_at=datetime(2026, 7, 9, 12, 34, 56, tzinfo=UTC),
        operator="",
        host="",
    )

    assert "record only commands actually run and observed outcomes" in report
    assert 'sqlite3 "$DB_PATH" ".backup' in report
    assert "tar -czf" in report
    assert "systemctl status <service>" in report
    assert "systemctl stop <service>" in report
    assert "systemctl start <service>" in report
    assert "systemctl restart <service>" in report
    assert "journalctl -u <service>" in report
    assert "delivery_failed jobs" in report
    assert "Outcome: pass/fail/not run" in report


def test_write_report_creates_timestamped_markdown_file(tmp_path: Path) -> None:
    script = _load_script()
    generated_at = datetime(2026, 7, 9, 12, 34, 56, tzinfo=UTC)

    output_path = script.write_report(
        output_dir=tmp_path,
        generated_at=generated_at,
        operator="Operator One",
        host="test-host",
    )

    assert output_path == tmp_path / "phase4-phase8-evidence-20260709T123456Z.md"
    assert output_path.exists()
    assert "Systemd Start/Stop/Restart/Rollback Smoke" in output_path.read_text(encoding="utf-8")


def test_cli_writes_report_and_prints_path(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--output-dir",
            str(tmp_path),
            "--operator",
            "CLI Operator",
            "--host",
            "cli-host",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    output_path = Path(completed.stdout.strip())
    assert output_path.parent == tmp_path
    report = output_path.read_text(encoding="utf-8")
    assert "Operator: CLI Operator" in report
    assert "Host: cli-host" in report
