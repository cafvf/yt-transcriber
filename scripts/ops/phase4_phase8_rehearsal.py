"""Operator-run helpers for Phase 4/8 operational evidence drills.

This script performs real local actions when explicitly invoked by the operator
and writes timestamped Markdown snippets with commands, outputs, and outcomes.
It is intended to complement ``create_phase4_phase8_evidence.py`` rather than
fabricate results.

Examples:

    uv run python scripts/ops/phase4_phase8_rehearsal.py backup
    uv run python scripts/ops/phase4_phase8_rehearsal.py systemd-smoke --service yt-transcriber-bot
    uv run python scripts/ops/phase4_phase8_rehearsal.py inspect-delivery-failed
    uv run python scripts/ops/phase4_phase8_rehearsal.py inspect-restart-recovery
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import tarfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_OUTPUT_DIR = Path("ops-evidence")
DEFAULT_APP_DIR = Path.cwd()
DEFAULT_DB_PATH = Path("data/jobs.db")
DEFAULT_RUNTIME_DIR = Path("data")
DEFAULT_MODELS_DIR = Path("models")
DEFAULT_ERRORS_PATH = Path("data/logs/operational_errors.jsonl")
DEFAULT_AUDIT_PATH = Path("data/logs/execution_audit.jsonl")
DEFAULT_SYSTEMD_ENV = Path("/etc/yt-transcriber-bot/env")
DEFAULT_SERVICE = "yt-transcriber-bot"


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _timestamp(dt: datetime | None = None) -> str:
    value = dt or _utc_now()
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _run(command: Sequence[str], *, cwd: Path | None = None, check: bool = False) -> CommandResult:
    completed = subprocess.run(
        list(command),
        cwd=str(cwd) if cwd is not None else None,
        check=False,
        capture_output=True,
        text=True,
    )
    result = CommandResult(
        command=tuple(command),
        returncode=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            list(command),
            output=completed.stdout,
            stderr=completed.stderr,
        )
    return result


def _run_mutating(command: Sequence[str], *, cwd: Path | None = None) -> CommandResult:
    result = _run(command, cwd=cwd, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"Falha ao executar comando mutável: {' '.join(result.command)} "
            f"(rc={result.returncode}): {result.stderr or result.stdout or '<empty>'}"
        )
    return result


def _make_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(0o700)


def _make_private_file(path: Path) -> None:
    path.chmod(0o600)


def _format_command(result: CommandResult) -> str:
    joined = " ".join(result.command)
    stdout = result.stdout or "<empty>"
    stderr = result.stderr or "<empty>"
    return (
        f"### `$ {joined}`\n\n"
        f"- Return code: `{result.returncode}`\n\n"
        f"**stdout**\n```text\n{stdout}\n```\n\n"
        f"**stderr**\n```text\n{stderr}\n```\n"
    )


def _write_snippet(
    *,
    output_dir: Path,
    section: str,
    body: str,
    occurred_at: datetime | None = None,
) -> Path:
    _make_private_dir(output_dir)
    stem = f"{section}-{_timestamp(occurred_at)}.md"
    path = output_dir / stem
    path.write_text(body, encoding="utf-8")
    _make_private_file(path)
    return path


def _copy_if_exists(source: Path, dest: Path) -> bool:
    if not source.exists():
        return False
    _make_private_dir(dest.parent)
    shutil.copy2(source, dest)
    _make_private_file(dest)
    return True


def _tar_dir(source_dir: Path, target_tgz: Path) -> bool:
    if not source_dir.exists():
        return False
    _make_private_dir(target_tgz.parent)
    with tarfile.open(target_tgz, "w:gz") as tar:
        tar.add(source_dir, arcname=source_dir.name)
    _make_private_file(target_tgz)
    return True


def _sqlite_backup(source: Path, target: Path) -> None:
    _make_private_dir(target.parent)
    with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
        src.backup(dst)
    _make_private_file(target)


def _git_head(app_dir: Path) -> str:
    return _run(["git", "rev-parse", "HEAD"], cwd=app_dir).stdout or "<unknown>"


def run_backup(args: argparse.Namespace) -> Path:
    occurred_at = _utc_now()
    app_dir = args.app_dir.resolve()
    db_path = (app_dir / args.db_path).resolve()
    runtime_dir = (app_dir / args.runtime_dir).resolve()
    models_dir = (app_dir / args.models_dir).resolve()
    output_root = args.output_dir.resolve()
    _make_private_dir(output_root)
    backup_dir = output_root / f"backup-{_timestamp(occurred_at)}"
    _make_private_dir(backup_dir)

    command_results: list[CommandResult] = []
    service_stopped = False
    try:
        if args.stop_service:
            command_results.append(
                _run_mutating(["sudo", "systemctl", "stop", args.service], cwd=app_dir)
            )
            service_stopped = True

        db_backup = backup_dir / "jobs.db"
        _sqlite_backup(db_path, db_backup)
        runtime_tgz = backup_dir / "runtime-data.tgz"
        runtime_copied = _tar_dir(runtime_dir, runtime_tgz)
        models_tgz = backup_dir / "models.tgz"
        models_copied = _tar_dir(models_dir, models_tgz)
        systemd_env_backup = backup_dir / "systemd-env"
        systemd_env_copied = _copy_if_exists(args.systemd_env, systemd_env_backup)
        dotenv_backup = backup_dir / "dotenv"
        dotenv_copied = _copy_if_exists(app_dir / ".env", dotenv_backup)
        git_revision = _git_head(app_dir)
        revision_path = backup_dir / "git-revision.txt"
        revision_path.write_text(git_revision + "\n", encoding="utf-8")
        _make_private_file(revision_path)

        if args.start_service and service_stopped:
            command_results.append(
                _run_mutating(["sudo", "systemctl", "start", args.service], cwd=app_dir)
            )
            service_stopped = False
            command_results.append(
                _run(["sudo", "systemctl", "status", args.service, "--no-pager"], cwd=app_dir)
            )
    finally:
        if service_stopped:
            _run_mutating(["sudo", "systemctl", "start", args.service], cwd=app_dir)

    body = "\n".join(
        [
            "# Backup/Restore Rehearsal — Captured Evidence",
            "",
            f"- Occurred at: {_utc_now().astimezone(UTC).isoformat(timespec='seconds')}",
            f"- App dir: `{app_dir}`",
            f"- Service: `{args.service}`",
            f"- Git commit: `{git_revision}`",
            f"- Backup dir: `{backup_dir}`",
            f"- Database source: `{db_path}`",
            f"- Runtime archived: `{'yes' if runtime_copied else 'no'}`",
            f"- Models archived: `{'yes' if models_copied else 'no'}`",
            f"- systemd env copied: `{'yes' if systemd_env_copied else 'no'}`",
            f"- .env copied: `{'yes' if dotenv_copied else 'no'}`",
            "",
            "## Artifacts",
            "",
            *(f"- `{path.name}`" for path in sorted(backup_dir.iterdir())),
            "",
            "## Commands Run",
            "",
            *[_format_command(result) for result in command_results],
            "## Operator Follow-up",
            "",
            "- Run restore against staging or stopped service and record `/healthcheck`, `/status`, `/list` after start.",
        ]
    )
    return _write_snippet(
        output_dir=output_root,
        section="backup-restore-rehearsal",
        body=body,
        occurred_at=occurred_at,
    )


def run_systemd_smoke(args: argparse.Namespace) -> Path:
    occurred_at = _utc_now()
    app_dir = args.app_dir.resolve()
    output_root = args.output_dir.resolve()

    results = [_run(["sudo", "systemctl", "status", args.service, "--no-pager"], cwd=app_dir)]
    restore_service = False
    try:
        results.append(_run_mutating(["sudo", "systemctl", "stop", args.service], cwd=app_dir))
        restore_service = True
        results.append(
            _run(["sudo", "systemctl", "status", args.service, "--no-pager"], cwd=app_dir)
        )
        results.append(_run_mutating(["sudo", "systemctl", "start", args.service], cwd=app_dir))
        results.append(
            _run(["sudo", "systemctl", "status", args.service, "--no-pager"], cwd=app_dir)
        )
        results.append(_run_mutating(["sudo", "systemctl", "restart", args.service], cwd=app_dir))
        restore_service = False
        results.append(
            _run(["sudo", "systemctl", "status", args.service, "--no-pager"], cwd=app_dir)
        )
        results.append(
            _run(
                ["journalctl", "-u", args.service, "-n", str(args.journal_lines), "--no-pager"],
                cwd=app_dir,
            )
        )
    finally:
        if restore_service:
            results.append(_run_mutating(["sudo", "systemctl", "start", args.service], cwd=app_dir))

    body = "\n".join(
        [
            "# Systemd Start/Stop/Restart Smoke — Captured Evidence",
            "",
            f"- Occurred at: {occurred_at.astimezone(UTC).isoformat(timespec='seconds')}",
            f"- App dir: `{app_dir}`",
            f"- Service: `{args.service}`",
            "",
            "## Commands Run",
            "",
            *[_format_command(result) for result in results],
            "## Operator Follow-up",
            "",
            "- Run `/healthcheck` and `/status` in Telegram after start/restart and paste the sanitized output into the main Phase 4/8 report.",
            "- If rollback smoke is required, run the dedicated rollback procedure separately and attach it to the same report.",
        ]
    )
    return _write_snippet(
        output_dir=output_root,
        section="systemd-smoke",
        body=body,
        occurred_at=occurred_at,
    )


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            loaded = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(loaded, dict):
            rows.append(loaded)
    return rows


def _query_jobs(db_path: Path, *, statuses: Iterable[str], limit: int) -> list[dict[str, object]]:
    query = (
        "SELECT job_id, video_id, status, requested_by_user_id, requested_at, updated_at, "
        "error_message, md_path, audio_path, log_path "
        "FROM jobs WHERE status IN ({placeholders}) "
        "ORDER BY updated_at DESC LIMIT ?"
    )
    status_list = list(statuses)
    placeholders = ",".join("?" for _ in status_list)
    rendered = query.format(placeholders=placeholders)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(rendered, [*status_list, limit]).fetchall()
    return [dict(row) for row in rows]


def _render_json_block(title: str, payload: object) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    return f"## {title}\n\n```json\n{serialized}\n```\n"


def run_inspect_delivery_failed(args: argparse.Namespace) -> Path:
    occurred_at = _utc_now()
    app_dir = args.app_dir.resolve()
    db_path = (app_dir / args.db_path).resolve()
    errors_path = (app_dir / args.errors_path).resolve()
    output_root = args.output_dir.resolve()

    jobs = _query_jobs(db_path, statuses=["delivery_failed"], limit=args.limit)
    errors = [
        row
        for row in _read_jsonl(errors_path)
        if str(row.get("operation", "")) == "transcribe_delivery"
    ][: args.limit]

    body = "\n".join(
        [
            "# delivery_failed Manual Recovery — Inspection Evidence",
            "",
            f"- Occurred at: {occurred_at.astimezone(UTC).isoformat(timespec='seconds')}",
            f"- Database: `{db_path}`",
            f"- Operational errors: `{errors_path}`",
            "",
            _render_json_block("Recent delivery_failed jobs", jobs),
            _render_json_block("Recent transcribe_delivery errors", errors),
            "## Operator Follow-up",
            "",
            "- Verify the paths shown above with `ls -lh <path>` and document the manual recovery method used.",
            "- Paste sanitized `/lasterror` output into the main report.",
        ]
    )
    return _write_snippet(
        output_dir=output_root,
        section="delivery-failed-inspection",
        body=body,
        occurred_at=occurred_at,
    )


def run_inspect_restart_recovery(args: argparse.Namespace) -> Path:
    occurred_at = _utc_now()
    app_dir = args.app_dir.resolve()
    db_path = (app_dir / args.db_path).resolve()
    audit_path = (app_dir / args.audit_path).resolve()
    output_root = args.output_dir.resolve()

    jobs = _query_jobs(
        db_path,
        statuses=["pending", "failed", "delivery_failed", "delivering"],
        limit=args.limit,
    )
    interesting_events = {
        "job_recovered_requeued",
        "job_failed",
        "job_delivery_failed",
        "job_started",
    }
    audit_rows = [
        row for row in _read_jsonl(audit_path) if str(row.get("event", "")) in interesting_events
    ][-args.limit :]

    body = "\n".join(
        [
            "# Interrupted-Job Restart Recovery — Inspection Evidence",
            "",
            f"- Occurred at: {occurred_at.astimezone(UTC).isoformat(timespec='seconds')}",
            f"- Database: `{db_path}`",
            f"- Execution audit: `{audit_path}`",
            "",
            _render_json_block("Recent jobs related to recovery states", jobs),
            _render_json_block("Recent audit events related to recovery", audit_rows),
            "## Operator Follow-up",
            "",
            "- Correlate these rows with `/status`, `/list`, `/lasterror`, and `journalctl` after an intentional interruption/restart drill.",
            "- Record whether the job was requeued, failed, or marked delivery_failed.",
        ]
    )
    return _write_snippet(
        output_dir=output_root,
        section="restart-recovery-inspection",
        body=body,
        occurred_at=occurred_at,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run operator-side Phase 4/8 evidence helpers. Commands may change real local state; "
            "use only on the intended host/staging environment."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup = subparsers.add_parser(
        "backup", help="Create a real runtime backup and capture evidence."
    )
    backup.add_argument("--app-dir", type=Path, default=DEFAULT_APP_DIR)
    backup.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    backup.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME_DIR)
    backup.add_argument("--models-dir", type=Path, default=DEFAULT_MODELS_DIR)
    backup.add_argument("--systemd-env", type=Path, default=DEFAULT_SYSTEMD_ENV)
    backup.add_argument("--service", default=DEFAULT_SERVICE)
    backup.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    backup.add_argument("--stop-service", action="store_true")
    backup.add_argument("--start-service", action="store_true")
    backup.set_defaults(func=run_backup)

    systemd = subparsers.add_parser(
        "systemd-smoke",
        help="Run stop/start/restart/status/journal systemd smoke and capture evidence.",
    )
    systemd.add_argument("--app-dir", type=Path, default=DEFAULT_APP_DIR)
    systemd.add_argument("--service", default=DEFAULT_SERVICE)
    systemd.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    systemd.add_argument("--journal-lines", type=int, default=120)
    systemd.set_defaults(func=run_systemd_smoke)

    delivery = subparsers.add_parser(
        "inspect-delivery-failed",
        help="Capture recent delivery_failed jobs and transcribe_delivery errors.",
    )
    delivery.add_argument("--app-dir", type=Path, default=DEFAULT_APP_DIR)
    delivery.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    delivery.add_argument("--errors-path", type=Path, default=DEFAULT_ERRORS_PATH)
    delivery.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    delivery.add_argument("--limit", type=int, default=5)
    delivery.set_defaults(func=run_inspect_delivery_failed)

    recovery = subparsers.add_parser(
        "inspect-restart-recovery",
        help="Capture recent jobs and audit rows relevant to restart recovery.",
    )
    recovery.add_argument("--app-dir", type=Path, default=DEFAULT_APP_DIR)
    recovery.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    recovery.add_argument("--audit-path", type=Path, default=DEFAULT_AUDIT_PATH)
    recovery.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    recovery.add_argument("--limit", type=int, default=10)
    recovery.set_defaults(func=run_inspect_restart_recovery)

    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    output_path = args.func(args)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
