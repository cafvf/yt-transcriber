"""Controlled PLAN-006 P06-007 upgrade/rollback rehearsal helper."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from scripts.ops.phase4_phase8_rehearsal import (
        _validate_restored_state,
        _validate_standard_backup,
    )
    from scripts.ops.systemd_host_preflight import sanitize_evidence_text
except ModuleNotFoundError as exc:
    if exc.name != "scripts":
        raise
    from phase4_phase8_rehearsal import _validate_restored_state, _validate_standard_backup
    from systemd_host_preflight import sanitize_evidence_text

DEFAULT_APP_DIR = Path.cwd()
DEFAULT_SERVICE = "yt-transcriber-bot"
DEFAULT_OUTPUT_DIR = Path("ops-evidence")


@dataclass(frozen=True, slots=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def _run(command: list[str], *, cwd: Path | None = None) -> CommandResult:
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        check=False,
    )
    return CommandResult(
        command=tuple(command),
        returncode=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )


def _run_ok(command: list[str], *, cwd: Path | None = None) -> CommandResult:
    result = _run(command, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed rc={result.returncode}: {' '.join(result.command)}: "
            f"{result.stderr or result.stdout or '<empty>'}"
        )
    return result


def _resolve_ref(app_dir: Path, ref: str) -> str:
    return _run_ok(["git", "rev-parse", f"{ref}^{{commit}}"], cwd=app_dir).stdout


def _require_clean_worktree(app_dir: Path) -> None:
    status = _run_ok(["git", "status", "--porcelain"], cwd=app_dir).stdout
    if status:
        raise RuntimeError("upgrade/rollback rehearsal requires a clean worktree")


def _backup_revision(backup_dir: Path) -> str:
    _validate_standard_backup(backup_dir)
    revision = (backup_dir / "git-revision.txt").read_text(encoding="utf-8").strip()
    if not revision:
        raise RuntimeError("backup git-revision.txt is empty")
    return revision


def _require_upgrade_relation(app_dir: Path, from_sha: str, to_sha: str) -> None:
    result = _run(["git", "merge-base", "--is-ancestor", from_sha, to_sha], cwd=app_dir)
    if result.returncode != 0:
        raise RuntimeError("target revision is not a descendant of the recorded source revision")


def build_preflight(
    *,
    app_dir: Path,
    backup_dir: Path,
    from_ref: str,
    to_ref: str,
) -> dict[str, object]:
    app_dir = app_dir.resolve()
    backup_dir = backup_dir.resolve()
    _require_clean_worktree(app_dir)

    from_sha = _resolve_ref(app_dir, from_ref)
    to_sha = _resolve_ref(app_dir, to_ref)
    _require_upgrade_relation(app_dir, from_sha, to_sha)

    backup_sha = _backup_revision(backup_dir)
    if backup_sha != from_sha:
        raise RuntimeError(
            f"backup revision {backup_sha} does not match source revision {from_sha}"
        )

    current_sha = _resolve_ref(app_dir, "HEAD")
    return {
        "schema_version": 1,
        "app_dir": str(app_dir),
        "backup_dir": str(backup_dir),
        "current_revision": current_sha,
        "source_revision": from_sha,
        "target_revision": to_sha,
        "backup_revision": backup_sha,
        "worktree_clean": True,
        "upgrade_relation": "source_is_ancestor_of_target",
        "backup_contract_valid": True,
        "production_mutated": False,
    }


def _timestamp() -> str:
    return datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")


def _private_write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    return path


def run_preflight(args: argparse.Namespace) -> Path:
    report = build_preflight(
        app_dir=args.app_dir,
        backup_dir=args.backup_dir,
        from_ref=args.from_ref,
        to_ref=args.to_ref,
    )
    path = args.output_dir.resolve() / f"upgrade-rollback-preflight-{_timestamp()}.json"
    return _private_write(path, json.dumps(report, indent=2, sort_keys=True) + "\n")


def _checkout(app_dir: Path, sha: str) -> CommandResult:
    return _run_ok(["git", "checkout", "--detach", sha], cwd=app_dir)


def _service(app_dir: Path, *args: str) -> CommandResult:
    return _run_ok(["sudo", "systemctl", *args], cwd=app_dir)


def _service_status(app_dir: Path, service: str) -> CommandResult:
    return _run_ok(
        ["sudo", "systemctl", "status", service, "--no-pager"],
        cwd=app_dir,
    )


def _journal(app_dir: Path, service: str) -> CommandResult:
    return _run_ok(
        [
            "sudo",
            "journalctl",
            "-u",
            service,
            "-n",
            "80",
            "--no-pager",
        ],
        cwd=app_dir,
    )


def _format_result(result: CommandResult) -> str:
    command = " ".join(result.command)
    return "\n".join(
        [
            f"### `$ {command}`",
            "",
            f"- rc: `{result.returncode}`",
            "",
            "```text",
            sanitize_evidence_text(result.stdout or result.stderr or "<empty>"),
            "```",
        ]
    )


def run_rehearsal(args: argparse.Namespace) -> Path:
    if not args.execute:
        raise RuntimeError("real rehearsal requires explicit --execute")

    app_dir = args.app_dir.resolve()
    preflight = build_preflight(
        app_dir=app_dir,
        backup_dir=args.backup_dir,
        from_ref=args.from_ref,
        to_ref=args.to_ref,
    )
    source_sha = str(preflight["source_revision"])
    target_sha = str(preflight["target_revision"])
    original_sha = str(preflight["current_revision"])
    if original_sha != target_sha:
        raise RuntimeError("real rehearsal must begin on the target revision intended for closure")

    results: list[CommandResult] = []
    service_stopped = False
    current_revision = original_sha

    try:
        results.append(_service(app_dir, "stop", args.service))
        service_stopped = True

        results.append(_checkout(app_dir, source_sha))
        current_revision = source_sha
        results.append(_service(app_dir, "start", args.service))
        service_stopped = False
        results.append(_service_status(app_dir, args.service))

        results.append(_service(app_dir, "stop", args.service))
        service_stopped = True
        results.append(_checkout(app_dir, target_sha))
        current_revision = target_sha
        results.append(_service(app_dir, "start", args.service))
        service_stopped = False
        results.append(_service_status(app_dir, args.service))
        results.append(_journal(app_dir, args.service))

        results.append(_service(app_dir, "stop", args.service))
        service_stopped = True
        results.append(_checkout(app_dir, source_sha))
        current_revision = source_sha
        results.append(_service(app_dir, "start", args.service))
        service_stopped = False
        results.append(_service_status(app_dir, args.service))
        results.append(_journal(app_dir, args.service))

        # Validate the already-approved backup in isolated staging during rollback proof.
        with TemporaryDirectory(prefix="yt-transcriber-p06-007-") as tmp:
            staging = Path(tmp)
            from scripts.ops.phase4_phase8_rehearsal import run_restore_staging

            restore_args = argparse.Namespace(
                app_dir=app_dir,
                backup_dir=args.backup_dir.resolve(),
                restore_root=staging / "restore",
                output_dir=staging / "evidence",
            )
            run_restore_staging(restore_args)
            restored_validation = _validate_restored_state(staging / "restore")

        # Return production checkout to the closure target after rollback was demonstrated.
        results.append(_service(app_dir, "stop", args.service))
        service_stopped = True
        results.append(_checkout(app_dir, target_sha))
        current_revision = target_sha
        results.append(_service(app_dir, "start", args.service))
        service_stopped = False
        results.append(_service_status(app_dir, args.service))
    finally:
        if current_revision != original_sha:
            if not service_stopped:
                _service(app_dir, "stop", args.service)
                service_stopped = True
            _checkout(app_dir, original_sha)
        if service_stopped:
            _service(app_dir, "start", args.service)

    body = "\n".join(
        [
            "# Versioned Upgrade/Rollback — Captured Evidence",
            "",
            f"- occurred_at: `{datetime.now(tz=UTC).isoformat(timespec='seconds')}`",
            f"- source_revision: `{source_sha}`",
            f"- target_revision: `{target_sha}`",
            f"- backup_revision: `{preflight['backup_revision']}`",
            "- destructive_db_migration_performed: `no`",
            "- rollback_code_revision_exercised: `yes`",
            "- rollback_backup_restore_validated_in_isolated_staging: `yes`",
            "- final_production_revision: `target_revision`",
            "",
            "## Restored data validation",
            "",
            "```json",
            json.dumps(restored_validation, indent=2, sort_keys=True),
            "```",
            "",
            "## Commands",
            "",
            *[_format_result(result) for result in results],
            "",
            "## Operator checkpoints",
            "",
            "- Run `/healthcheck`, `/status`, and inspect sanitized journal evidence after the drill.",
        ]
    )
    path = args.output_dir.resolve() / f"upgrade-rollback-rehearsal-{_timestamp()}.md"
    return _private_write(path, body + "\n")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    def common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--app-dir", type=Path, default=DEFAULT_APP_DIR)
        subparser.add_argument("--backup-dir", type=Path, required=True)
        subparser.add_argument("--from-ref", required=True)
        subparser.add_argument("--to-ref", required=True)
        subparser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)

    preflight = subparsers.add_parser("preflight")
    common(preflight)
    preflight.set_defaults(func=run_preflight)

    rehearsal = subparsers.add_parser("rehearsal")
    common(rehearsal)
    rehearsal.add_argument("--service", default=DEFAULT_SERVICE)
    rehearsal.add_argument("--execute", action="store_true")
    rehearsal.set_defaults(func=run_rehearsal)

    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    path = args.func(args)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
