"""Run the full Phase 4/8 rehearsal flow and save results in one session folder.

This operator-facing helper sequences the existing evidence/report helpers,
captures command outputs from the automated parts, and prompts the operator for
Telegram/manual observations required by the acceptance criteria.

It does not fabricate evidence: manual checkpoints are collected interactively
from the operator and written to the final Markdown report.
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_OUTPUT_DIR = Path("ops-evidence")
DEFAULT_SERVICE = "yt-transcriber-bot"
CREATE_TEMPLATE_SCRIPT = Path("scripts/ops/create_phase4_phase8_evidence.py")
REHEARSAL_SCRIPT = Path("scripts/ops/phase4_phase8_rehearsal.py")


@dataclass(frozen=True)
class StepArtifact:
    name: str
    path: Path


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _stamp(dt: datetime | None = None) -> str:
    value = dt or _utc_now()
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd is not None else None,
        text=True,
        capture_output=True,
        check=False,
    )


def _run_python_script(script: Path, args: list[str], *, cwd: Path | None = None) -> Path:
    completed = _run([sys.executable, str(script), *args], cwd=cwd)
    if completed.returncode != 0:
        raise RuntimeError(
            f"Falha ao executar {script}: rc={completed.returncode}\n"
            f"stdout:\n{completed.stdout}\n\nstderr:\n{completed.stderr}"
        )
    output = completed.stdout.strip().splitlines()
    if not output:
        raise RuntimeError(f"{script} não retornou caminho de saída em stdout.")
    return Path(output[-1].strip())


def _multiline_prompt(title: str) -> str:
    print(f"\n{title}")
    print("Cole o conteúdo abaixo. Finalize com uma linha contendo apenas '.'")
    lines: list[str] = []
    while True:
        line = input()
        if line == ".":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _single_prompt(prompt: str) -> str:
    return input(f"{prompt} ").strip()


def _copy_into_session(source: Path, session_dir: Path) -> Path:
    target = session_dir / source.name
    if source.resolve() == target.resolve():
        return target
    shutil.copy2(source, target)
    return target


def _append_section(report: Path, heading: str, lines: list[str]) -> None:
    with report.open("a", encoding="utf-8") as file:
        file.write(f"\n## {heading}\n\n")
        for line in lines:
            file.write(line)
            if not line.endswith("\n"):
                file.write("\n")


def _collect_telegram_checks(report: Path, *, commands: list[str], label: str) -> None:
    notes = _multiline_prompt(
        f"[{label}] Cole um resumo sanitizado das saídas Telegram para: {', '.join(commands)}"
    )
    outcome = _single_prompt(f"[{label}] Resultado observado (pass/fail/pass with caveats):")
    blockers = _multiline_prompt(
        f"[{label}] Blockers/ressalvas (ou deixe vazio e finalize com '.')"
    )
    _append_section(
        report,
        f"{label} — Telegram/Operator checks",
        [
            f"- Commands expected: `{', '.join(commands)}`",
            f"- Outcome: {outcome or '<not provided>'}",
            "",
            "### Notes",
            "",
            "```text",
            notes or "<no notes provided>",
            "```",
            "",
            "### Blockers / caveats",
            "",
            "```text",
            blockers or "<none>",
            "```",
        ],
    )


def _rollback_section(report: Path, *, session_dir: Path, service: str) -> None:
    current_rev = _single_prompt(
        "[Rollback] Informe o commit/revision atual a ser restaurado depois do smoke:"
    )
    rollback_rev = _single_prompt(
        "[Rollback] Informe o commit/revision antiga para testar rollback (vazio para pular):"
    )
    if not rollback_rev:
        _append_section(
            report,
            "Rollback smoke",
            ["- Skipped: operador não informou revision de rollback."],
        )
        return

    commands = [
        ["sudo", "systemctl", "stop", service],
        ["git", "checkout", rollback_rev],
        ["uv", "sync", "--locked"],
        ["sudo", "systemctl", "start", service],
        ["sudo", "systemctl", "status", service, "--no-pager"],
        ["journalctl", "-u", service, "-n", "120", "--no-pager"],
        ["sudo", "systemctl", "stop", service],
        ["git", "checkout", current_rev],
        ["uv", "sync", "--locked"],
        ["sudo", "systemctl", "start", service],
        ["sudo", "systemctl", "status", service, "--no-pager"],
    ]
    command_blocks: list[str] = []
    for command in commands:
        completed = _run(command)
        joined = " ".join(command)
        command_blocks.extend(
            [
                f"### `$ {joined}`",
                "",
                f"- Return code: `{completed.returncode}`",
                "",
                "**stdout**",
                "```text",
                completed.stdout.strip() or "<empty>",
                "```",
                "",
                "**stderr**",
                "```text",
                completed.stderr.strip() or "<empty>",
                "```",
                "",
            ]
        )
    snippet = session_dir / f"rollback-smoke-{_stamp()}.md"
    snippet.write_text("\n".join(command_blocks), encoding="utf-8")
    _append_section(
        report,
        "Rollback smoke",
        [
            f"- Current revision restored: `{current_rev}`",
            f"- Rollback revision tested: `{rollback_rev}`",
            f"- Snippet: `{snippet}`",
        ],
    )
    _collect_telegram_checks(report, commands=["/healthcheck", "/status"], label="Rollback smoke")


def run_full_rehearsal(args: argparse.Namespace) -> Path:
    started_at = _utc_now()
    session_dir = args.output_dir.resolve() / f"phase4-phase8-session-{_stamp(started_at)}"
    session_dir.mkdir(parents=True, exist_ok=True)

    template_path = _run_python_script(CREATE_TEMPLATE_SCRIPT, ["--output-dir", str(session_dir)])
    report = session_dir / "phase4-phase8-full-rehearsal.md"
    shutil.copy2(template_path, report)
    _append_section(
        report,
        "Session metadata",
        [
            f"- Session dir: `{session_dir}`",
            f"- Started at: {started_at.astimezone(UTC).isoformat(timespec='seconds')}",
            f"- Host: `{platform.node()}`",
            f"- Service: `{args.service}`",
        ],
    )

    backup_args = [
        "backup",
        "--output-dir",
        str(session_dir),
        "--service",
        args.service,
        "--stop-service",
        "--start-service",
    ]
    backup_snippet = _run_python_script(REHEARSAL_SCRIPT, backup_args)
    backup_snippet = _copy_into_session(backup_snippet, session_dir)
    _append_section(
        report,
        "Backup rehearsal",
        [f"- Automated snippet: `{backup_snippet}`"],
    )
    _collect_telegram_checks(
        report, commands=["/healthcheck", "/status", "/list"], label="Backup rehearsal"
    )

    systemd_snippet = _run_python_script(
        REHEARSAL_SCRIPT,
        ["systemd-smoke", "--output-dir", str(session_dir), "--service", args.service],
    )
    systemd_snippet = _copy_into_session(systemd_snippet, session_dir)
    _append_section(
        report,
        "Systemd smoke",
        [f"- Automated snippet: `{systemd_snippet}`"],
    )
    _collect_telegram_checks(report, commands=["/healthcheck", "/status"], label="Systemd smoke")

    _rollback_section(report, session_dir=session_dir, service=args.service)

    has_delivery_failed = _single_prompt(
        "[delivery_failed] Já existe/foi induzido um caso delivery_failed? (yes/no):"
    ).lower()
    if has_delivery_failed in {"y", "yes", "s", "sim"}:
        delivery_snippet = _run_python_script(
            REHEARSAL_SCRIPT,
            ["inspect-delivery-failed", "--output-dir", str(session_dir)],
        )
        delivery_snippet = _copy_into_session(delivery_snippet, session_dir)
        _append_section(
            report,
            "delivery_failed manual recovery",
            [f"- Automated snippet: `{delivery_snippet}`"],
        )
        _collect_telegram_checks(
            report, commands=["/lasterror", "/list"], label="delivery_failed recovery"
        )
        recovery_method = _multiline_prompt(
            "[delivery_failed] Descreva o método de recuperação manual e paths verificados:"
        )
        _append_section(
            report,
            "delivery_failed manual recovery details",
            ["```text", recovery_method or "<not provided>", "```"],
        )
    else:
        _append_section(
            report,
            "delivery_failed manual recovery",
            ["- Skipped: operador informou que não havia caso controlado disponível."],
        )

    run_restart_drill = _single_prompt(
        "[Restart recovery] Vai executar agora o ensaio de interrupção/restart? (yes/no):"
    ).lower()
    if run_restart_drill in {"y", "yes", "s", "sim"}:
        print(
            "\n[Restart recovery] Inicie um job real no Telegram e aguarde ele entrar em execução.\n"
            "Quando estiver ativo, volte aqui e pressione Enter para continuar com o restante do ensaio."
        )
        input()
        interruption_notes = _multiline_prompt(
            "[Restart recovery] Descreva como você confirmou que o job estava ativo antes da interrupção:"
        )
        _append_section(
            report,
            "Restart recovery pre-interruption notes",
            ["```text", interruption_notes or "<not provided>", "```"],
        )
        restart_commands = [
            ["sudo", "systemctl", "stop", args.service],
            ["sudo", "systemctl", "start", args.service],
            ["sudo", "systemctl", "status", args.service, "--no-pager"],
            ["journalctl", "-u", args.service, "-n", "120", "--no-pager"],
        ]
        command_blocks: list[str] = []
        for command in restart_commands:
            completed = _run(command)
            joined = " ".join(command)
            command_blocks.extend(
                [
                    f"### `$ {joined}`",
                    "",
                    f"- Return code: `{completed.returncode}`",
                    "",
                    "**stdout**",
                    "```text",
                    completed.stdout.strip() or "<empty>",
                    "```",
                    "",
                    "**stderr**",
                    "```text",
                    completed.stderr.strip() or "<empty>",
                    "```",
                    "",
                ]
            )
        restart_cmd_snippet = session_dir / f"restart-recovery-smoke-{_stamp()}.md"
        restart_cmd_snippet.write_text("\n".join(command_blocks), encoding="utf-8")
        restart_inspect = _run_python_script(
            REHEARSAL_SCRIPT,
            ["inspect-restart-recovery", "--output-dir", str(session_dir)],
        )
        restart_inspect = _copy_into_session(restart_inspect, session_dir)
        _append_section(
            report,
            "Interrupted-job restart recovery",
            [
                f"- Restart command snippet: `{restart_cmd_snippet}`",
                f"- Inspection snippet: `{restart_inspect}`",
            ],
        )
        _collect_telegram_checks(
            report,
            commands=["/status", "/list", "/lasterror"],
            label="Interrupted-job restart recovery",
        )
        final_state = _multiline_prompt(
            "[Restart recovery] Descreva o estado final observado do job interrompido:"
        )
        _append_section(
            report,
            "Interrupted-job restart recovery details",
            ["```text", final_state or "<not provided>", "```"],
        )
    else:
        _append_section(
            report,
            "Interrupted-job restart recovery",
            ["- Skipped: operador optou por não executar o ensaio nesta sessão."],
        )

    finished_at = _utc_now()
    _append_section(
        report,
        "Session completion",
        [
            f"- Finished at: {finished_at.astimezone(UTC).isoformat(timespec='seconds')}",
            "- Review the generated snippets and consolidate pass/fail decisions in the top-level evidence template section if needed.",
        ],
    )
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the full Phase 4/8 operational rehearsal flow, save all automated outputs, "
            "and collect Telegram/manual checkpoints into one Markdown report."
        )
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--service", default=DEFAULT_SERVICE)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = run_full_rehearsal(args)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
