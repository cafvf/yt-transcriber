"""Tests for the full Phase 4/8 rehearsal orchestrator."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

SCRIPT_PATH = Path("scripts/ops/run_phase4_phase8_full_rehearsal.py")


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_phase4_phase8_full_rehearsal", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_run_full_rehearsal_creates_single_report_with_helper_references(
    tmp_path: Path, monkeypatch
) -> None:
    script = _load_script()

    def fake_run_python_script(
        script_path: Path, args: list[str], *, cwd: Path | None = None
    ) -> Path:
        output_dir = Path(args[args.index("--output-dir") + 1])
        output_dir.mkdir(parents=True, exist_ok=True)
        if script_path.name == "create_phase4_phase8_evidence.py":
            path = output_dir / "template.md"
            path.write_text("# Phase 4/8 Operational Drill Evidence\n", encoding="utf-8")
            return path
        stem = "-".join(args[:1]) if args else "snippet"
        path = output_dir / f"{stem}.md"
        path.write_text(f"snippet for {args[0]}\n", encoding="utf-8")
        return path

    answers = iter(
        [
            "backup ok",
            ".",
            "pass",
            "",
            ".",
            "systemd ok",
            ".",
            "pass",
            "",
            ".",
            "current-rev-123",
            "",  # skip rollback revision
            "no",
            "no",
        ]
    )
    monkeypatch.setattr(script, "_run_python_script", fake_run_python_script)
    monkeypatch.setattr(script, "_single_prompt", lambda _prompt: next(answers))
    monkeypatch.setattr(
        script, "_multiline_prompt", lambda _title: "\n".join(_consume_until_dot(answers))
    )

    report = script.run_full_rehearsal(
        SimpleNamespace(output_dir=tmp_path / "evidence", service="yt-transcriber-bot")
    )

    content = report.read_text(encoding="utf-8")
    assert "Phase 4/8 Operational Drill Evidence" in content
    assert "Backup rehearsal" in content
    assert "Systemd smoke" in content
    assert "Skipped: operador não informou revision de rollback." in content
    assert "Skipped: operador informou que não havia caso controlado disponível." in content
    assert "Skipped: operador optou por não executar o ensaio nesta sessão." in content


def _consume_until_dot(iterator: object) -> list[str]:
    collected: list[str] = []
    while True:
        value = next(iterator)
        if value == ".":
            return collected
        collected.append(value)
