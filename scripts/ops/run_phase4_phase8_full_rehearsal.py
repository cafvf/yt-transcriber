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


def _run_mutating(
    command: list[str], *, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    completed = _run(command, cwd=cwd)
    _raise_for_mutating_failure(command, completed)
    return completed


def _raise_for_mutating_failure(
    command: list[str], completed: subprocess.CompletedProcess[str]
) -> None:
    if completed.returncode == 0:
        return
    raise RuntimeError(
        f"Falha ao executar comando mutável: {' '.join(command)} "
        f"(rc={completed.returncode}): {completed.stderr.strip() or completed.stdout.strip() or '<empty>'}"
    )


def _make_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(0o700)


def _make_private_file(path: Path) -> None:
    path.chmod(0o600)


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
    _make_private_file(target)
    return target


def _restart_recovery_commands(
    service: str,
) -> list[tuple[list[str], subprocess.CompletedProcess[str]]]:
    commands: list[tuple[list[str], subprocess.CompletedProcess[str]]] = []
    service_stopped = False
    try:
        stop = ["sudo", "systemctl", "stop", service]
        commands.append((stop, _run_mutating(stop)))
        service_stopped = True
        start = ["sudo", "systemctl", "start", service]
        commands.append((start, _run_mutating(start)))
        service_stopped = False
        for command in (
            ["sudo", "systemctl", "status", service, "--no-pager"],
            ["journalctl", "-u", service, "-n", "120", "--no-pager"],
        ):
            commands.append((command, _run(command)))
    finally:
        if service_stopped:
            start = ["sudo", "systemctl", "start", service]
            commands.append((start, _run_mutating(start)))
    return commands


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

    command_blocks: list[str] = []

    def run_and_record(command: list[str], *, mutating: bool) -> None:
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
        if mutating:
            _raise_for_mutating_failure(command, completed)

    if not current_rev:
        current_rev = _run_mutating(["git", "rev-parse", "HEAD"]).stdout.strip()
        if not current_rev:
            raise RuntimeError("git rev-parse HEAD não retornou uma revision para recuperação.")

    primary_error: RuntimeError | None = None
    try:
        run_and_record(["sudo", "systemctl", "stop", service], mutating=True)
        run_and_record(["git", "checkout", rollback_rev], mutating=True)
        run_and_record(["uv", "sync", "--locked"], mutating=True)
        run_and_record(["sudo", "systemctl", "start", service], mutating=True)
        run_and_record(["sudo", "systemctl", "status", service, "--no-pager"], mutating=False)
        run_and_record(["journalctl", "-u", service, "-n", "120", "--no-pager"], mutating=False)
    except RuntimeError as error:
        primary_error = error

    recovery_errors: list[RuntimeError | OSError] = []
    try:
        for command, mutating in (
            (["sudo", "systemctl", "stop", service], True),
            (["git", "checkout", current_rev], True),
            (["uv", "sync", "--locked"], True),
        ):
            try:
                run_and_record(command, mutating=mutating)
            except (RuntimeError, OSError) as error:
                recovery_errors.append(error)
    finally:
        try:
            run_and_record(["sudo", "systemctl", "start", service], mutating=True)
        except (RuntimeError, OSError) as error:
            recovery_errors.append(error)
    try:
        run_and_record(["sudo", "systemctl", "status", service, "--no-pager"], mutating=False)
    except OSError as error:
        recovery_errors.append(error)

    snippet = session_dir / f"rollback-smoke-{_stamp()}.md"
    snippet.write_text("\n".join(command_blocks), encoding="utf-8")
    _make_private_file(snippet)
    if primary_error is not None:
        if recovery_errors:
            primary_error.add_note(
                "Falhas durante a recuperação (serviço reiniciado em best effort):\n"
                + "\n".join(f"- {error}" for error in recovery_errors)
            )
        raise primary_error
    if recovery_errors:
        raise RuntimeError(
            "Falhas durante a recuperação de rollback:\n"
            + "\n".join(f"- {error}" for error in recovery_errors)
        ) from recovery_errors[0]

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
    _make_private_dir(session_dir)

    template_path = _run_python_script(CREATE_TEMPLATE_SCRIPT, ["--output-dir", str(session_dir)])
    report = session_dir / "phase4-phase8-full-rehearsal.md"
    shutil.copy2(template_path, report)
    _make_private_file(report)
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
        command_blocks: list[str] = []
        for command, completed in _restart_recovery_commands(args.service):
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
        _make_private_file(restart_cmd_snippet)
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
