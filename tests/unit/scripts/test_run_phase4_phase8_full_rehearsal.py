"""Tests for the full Phase 4/8 rehearsal orchestrator."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

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


@pytest.mark.parametrize(
    ("failing_recovery_command", "expected_note"),
    [
        (("git", "checkout", "current-rev"), "git checkout current-rev"),
        (("uv", "sync", "--locked"), "uv sync --locked"),
    ],
)
def test_rollback_attempts_service_start_when_a_recovery_step_fails(
    tmp_path: Path, monkeypatch, failing_recovery_command: tuple[str, ...], expected_note: str
) -> None:
    script = _load_script()
    commands: list[tuple[str, ...]] = []

    def fake_run(command: list[str], *, cwd: Path | None = None):
        del cwd
        commands.append(tuple(command))
        return subprocess.CompletedProcess(
            command,
            1
            if tuple(command) in {("git", "checkout", "old-rev"), failing_recovery_command}
            else 0,
            stdout="",
            stderr="checkout failed",
        )

    answers = iter(["current-rev", "old-rev"])
    monkeypatch.setattr(script, "_run", fake_run)
    monkeypatch.setattr(script, "_single_prompt", lambda _prompt: next(answers))

    with pytest.raises(RuntimeError, match="git checkout old-rev") as exc_info:
        script._rollback_section(
            tmp_path / "report.md", session_dir=tmp_path, service="yt-transcriber-bot"
        )

    assert ("git", "checkout", "current-rev") in commands
    assert commands[-2:] == [
        ("sudo", "systemctl", "start", "yt-transcriber-bot"),
        ("sudo", "systemctl", "status", "yt-transcriber-bot", "--no-pager"),
    ]
    assert expected_note in "\n".join(exc_info.value.__notes__)


@pytest.mark.parametrize(
    "oserror_command",
    [
        ("git", "checkout", "current-rev"),
        ("uv", "sync", "--locked"),
    ],
)
def test_rollback_attempts_service_start_after_oserror_during_recovery(
    tmp_path: Path, monkeypatch, oserror_command: tuple[str, ...]
) -> None:
    script = _load_script()
    commands: list[tuple[str, ...]] = []

    def fake_run(command: list[str], *, cwd: Path | None = None):
        del cwd
        commands.append(tuple(command))
        if tuple(command) == oserror_command:
            raise OSError("command unavailable")
        return subprocess.CompletedProcess(
            command,
            1 if tuple(command) == ("git", "checkout", "old-rev") else 0,
            stdout="",
            stderr="checkout failed",
        )

    answers = iter(["current-rev", "old-rev"])
    monkeypatch.setattr(script, "_run", fake_run)
    monkeypatch.setattr(script, "_single_prompt", lambda _prompt: next(answers))

    with pytest.raises(RuntimeError, match="git checkout old-rev"):
        script._rollback_section(
            tmp_path / "report.md", session_dir=tmp_path, service="yt-transcriber-bot"
        )

    assert commands.count(("sudo", "systemctl", "start", "yt-transcriber-bot")) == 1


def test_rollback_resolves_an_empty_current_revision_before_stopping_service(
    tmp_path: Path, monkeypatch
) -> None:
    script = _load_script()
    commands: list[tuple[str, ...]] = []

    def fake_run(command: list[str], *, cwd: Path | None = None):
        del cwd
        commands.append(tuple(command))
        return subprocess.CompletedProcess(
            command,
            1 if command == ["git", "checkout", "old-rev"] else 0,
            stdout="resolved-current-rev\n" if command == ["git", "rev-parse", "HEAD"] else "",
            stderr="checkout failed",
        )

    answers = iter(["", "old-rev"])
    monkeypatch.setattr(script, "_run", fake_run)
    monkeypatch.setattr(script, "_single_prompt", lambda _prompt: next(answers))

    with pytest.raises(RuntimeError, match="git checkout old-rev"):
        script._rollback_section(
            tmp_path / "report.md", session_dir=tmp_path, service="yt-transcriber-bot"
        )

    assert commands[0] == ("git", "rev-parse", "HEAD")
    assert commands.index(("sudo", "systemctl", "stop", "yt-transcriber-bot")) > 0


def test_rollback_reports_all_recovery_failures_without_masking_the_primary_failure(
    tmp_path: Path, monkeypatch
) -> None:
    script = _load_script()

    def fake_run(command: list[str], *, cwd: Path | None = None):
        del cwd
        return subprocess.CompletedProcess(
            command,
            1
            if tuple(command)
            in {
                ("git", "checkout", "old-rev"),
                ("git", "checkout", "current-rev"),
                ("uv", "sync", "--locked"),
            }
            else 0,
            stdout="",
            stderr="command failed",
        )

    answers = iter(["current-rev", "old-rev"])
    monkeypatch.setattr(script, "_run", fake_run)
    monkeypatch.setattr(script, "_single_prompt", lambda _prompt: next(answers))

    with pytest.raises(RuntimeError, match="git checkout old-rev") as exc_info:
        script._rollback_section(
            tmp_path / "report.md", session_dir=tmp_path, service="yt-transcriber-bot"
        )

    notes = "\n".join(exc_info.value.__notes__)
    assert "git checkout current-rev" in notes
    assert "uv sync --locked" in notes


def test_restart_recovery_fails_fast_and_restores_service_after_start_failure(monkeypatch) -> None:
    script = _load_script()
    commands: list[tuple[str, ...]] = []

    def fake_run(command: list[str], *, cwd: Path | None = None):
        del cwd
        commands.append(tuple(command))
        return subprocess.CompletedProcess(
            command,
            1 if command[:3] == ["sudo", "systemctl", "start"] and len(commands) == 2 else 0,
            stdout="",
            stderr="start failed",
        )

    monkeypatch.setattr(script, "_run", fake_run)

    with pytest.raises(RuntimeError, match="Falha ao executar comando mutável"):
        script._restart_recovery_commands("yt-transcriber-bot")

    assert commands == [
        ("sudo", "systemctl", "stop", "yt-transcriber-bot"),
        ("sudo", "systemctl", "start", "yt-transcriber-bot"),
        ("sudo", "systemctl", "start", "yt-transcriber-bot"),
    ]


def _consume_until_dot(iterator: object) -> list[str]:
    collected: list[str] = []
    while True:
        value = next(iterator)
        if value == ".":
            return collected
        collected.append(value)
