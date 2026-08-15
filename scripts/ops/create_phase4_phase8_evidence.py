"""Create an auditable Phase 4/8 operational drill evidence template.

The helper intentionally does not run privileged or environment-specific
commands. It creates a timestamped Markdown report so operators can rehearse,
record real commands, and attach evidence without fabricating outcomes.

Usage:

    uv run python scripts/ops/create_phase4_phase8_evidence.py --output-dir ops-evidence
"""

from __future__ import annotations

import argparse
import getpass
import os
import platform
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_OUTPUT_DIR = Path("ops-evidence")
_PRIVATE_DIR_MODE = 0o700
_PRIVATE_FILE_MODE = 0o600


def build_report(*, generated_at: datetime, operator: str, host: str) -> str:
    timestamp = generated_at.astimezone(UTC).isoformat(timespec="seconds")
    return f"""# Phase 4/8 Operational Drill Evidence

- Generated at: {timestamp}
- Operator: {operator or "<fill during rehearsal>"}
- Host: {host or "<fill during rehearsal>"}
- Scope: backup/restore, systemd smoke, and recovery drills
- Evidence policy: record only commands actually run and observed outcomes.

## Environment

- Deployment path:
- Python/uv version:
- Git commit:
- Service name:
- Database path:
- Transcript/artifact paths:
- Relevant environment file:
- Access level available for this rehearsal:
- Systemd available: yes/no
- Root/sudo available: yes/no

## Backup/Restore Rehearsal

- Backup source paths:
- Backup destination:
- Restore target:
- Data integrity check used:
- Commands run:
  - `[fill exact backup command, for example: sqlite3 "$DB_PATH" ".backup '$BACKUP_PATH'"]`
  - `[fill exact artifact backup command, for example: tar -czf "$ARTIFACT_BACKUP" transcripts/ data/]`
  - `[fill exact restore command against a disposable target]`
- Evidence captured:
  - Backup file listing/checksum:
  - Restored database check:
  - Restored transcript/artifact spot check:
- Outcome: pass/fail/not run
- Blockers:
- Follow-ups:

## Systemd Start/Stop/Restart/Rollback Smoke

- Service unit:
- Pre-smoke health/status:
- Commands run:
  - `[fill if available: systemctl status <service>]`
  - `[fill if authorized: systemctl stop <service>]`
  - `[fill if authorized: systemctl start <service>]`
  - `[fill if authorized: systemctl restart <service>]`
  - `[fill rollback command or deployment pointer change]`
  - `[fill evidence command: journalctl -u <service> --since "<timestamp>"]`
- Expected smoke checks:
  - Service reaches active/running or documented safe stopped state:
  - Logs contain no unsanitized secret payloads:
  - Bot startup/config check completed:
  - Rollback target verified:
- Outcome: pass/fail/not run
- Blockers:
- Follow-ups:

## delivery_failed Manual Recovery Rehearsal

- Test job/video identifier:
- Failure state source:
- Manual recovery action:
- Commands run:
  - `[fill exact query/inspection command used to find delivery_failed jobs]`
  - `[fill exact command or admin action used to retry or mark recovery]`
  - `[fill exact command used to verify final job state]`
- Evidence captured:
  - Before state:
  - Recovery action output:
  - After state:
  - User-facing delivery/artifact verification:
- Outcome: pass/fail/not run
- Blockers:
- Follow-ups:

## Interrupted-Job Restart Recovery Rehearsal

- Interruption method used:
- Restart path:
- Commands run:
  - `[fill exact command used to observe an in-progress job before interruption]`
  - `[fill exact stop/interruption command, if authorized]`
  - `[fill exact restart command, if authorized]`
  - `[fill exact command used to verify recovered, failed, or resumable state]`
- Evidence captured:
  - Before interruption:
  - Startup/recovery logs:
  - Final job state:
  - Duplicate work/artifact check:
- Outcome: pass/fail/not run
- Blockers:
- Follow-ups:

## Commands Run

Record every command actually executed during the drill.

```console
# command
# output summary or path to captured output
```

## Outcomes

- Backup/restore rehearsal:
- Systemd smoke:
- delivery_failed recovery:
- Interrupted-job restart recovery:
- Overall result:

## Blockers

-

## Follow-Ups

-
"""


def report_filename(generated_at: datetime) -> str:
    timestamp = generated_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"phase4-phase8-evidence-{timestamp}.md"


def write_report(
    *,
    output_dir: Path,
    generated_at: datetime,
    operator: str,
    host: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True, mode=_PRIVATE_DIR_MODE)
    if os.name == "posix":
        output_dir.chmod(_PRIVATE_DIR_MODE)
    output_path = output_dir / report_filename(generated_at)
    output_path.write_text(
        build_report(generated_at=generated_at, operator=operator, host=host),
        encoding="utf-8",
    )
    if os.name == "posix":
        output_path.chmod(_PRIVATE_FILE_MODE)
    return output_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a timestamped Markdown evidence template for Phase 4/8 "
            "backup, systemd, and recovery rehearsals. No privileged commands are run."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for the generated report (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--operator",
        default=getpass.getuser(),
        help="Operator name to prefill in the report (default: current user)",
    )
    parser.add_argument(
        "--host",
        default=platform.node(),
        help="Host name to prefill in the report (default: current host)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    output_path = write_report(
        output_dir=args.output_dir,
        generated_at=datetime.now(tz=UTC),
        operator=args.operator,
        host=args.host,
    )
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
