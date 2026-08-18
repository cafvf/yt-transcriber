#!/usr/bin/env python3
"""Private operator helper for manual artifact recovery after delivery failure."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from sqlalchemy import create_engine

from yt_transcriber_bot.application.services.manual_artifact_recovery import (
    ArtifactRecoveryState,
    ManualArtifactRecoveryReport,
    ManualArtifactRecoveryService,
)
from yt_transcriber_bot.infrastructure.persistence.sqlalchemy.job_repository import (
    SqlAlchemyJobRepository,
)


def _repository(db_path: Path) -> SqlAlchemyJobRepository:
    resolved = db_path.expanduser().resolve()
    if not resolved.is_file():
        raise RuntimeError(f"jobs database not found: {resolved}")
    engine = create_engine(f"sqlite:///{resolved}", future=True)
    return SqlAlchemyJobRepository(engine)


def _artifact_exists(path: Path) -> bool:
    try:
        return path.is_file() and not path.is_symlink()
    except OSError:
        return False


def _report_dict(report: ManualArtifactRecoveryReport) -> dict[str, object]:
    return {
        "schema_version": 1,
        "job_id": report.job_id,
        "job_status": report.status.value,
        "eligible_for_manual_recovery": report.eligible,
        "artifacts": [
            {
                "kind": item.kind,
                "state": item.state.value,
                "path": str(item.path) if item.path is not None else None,
            }
            for item in report.artifacts
        ],
        "implicit_resend": False,
        "job_reopened": False,
        "recomputation_triggered": False,
    }


def inspect_job(*, db_path: Path, job_id: str) -> ManualArtifactRecoveryReport:
    service = ManualArtifactRecoveryService(
        _repository(db_path),
        artifact_available=_artifact_exists,
    )
    report = service.inspect(job_id)
    if report is None:
        raise RuntimeError(f"job not found: {job_id}")
    return report


def _selected_artifact(
    report: ManualArtifactRecoveryReport,
    kind: str,
) -> Path:
    if not report.eligible:
        raise RuntimeError(
            f"job {report.job_id} has status {report.status.value}; "
            "manual recovery is restricted to delivery_failed"
        )
    item = next(artifact for artifact in report.artifacts if artifact.kind == kind)
    if item.state is ArtifactRecoveryState.REFERENCE_ABSENT:
        raise RuntimeError(
            f"{kind} artifact has no persisted reference; it is unavailable "
            "(possibly absent or retention-purged)"
        )
    if item.state is ArtifactRecoveryState.REFERENCED_MISSING:
        raise RuntimeError(f"{kind} artifact reference exists but the local file is missing")
    assert item.path is not None
    return item.path


def _require_within(path: Path, root: Path) -> Path:
    resolved = path.expanduser().resolve()
    allowed = root.expanduser().resolve()
    try:
        resolved.relative_to(allowed)
    except ValueError as exc:
        raise RuntimeError(f"artifact path is outside allowed root: {allowed}") from exc
    return resolved


def copy_artifact(
    *,
    report: ManualArtifactRecoveryReport,
    kind: str,
    allowed_root: Path,
    destination: Path,
) -> Path:
    selected = _selected_artifact(report, kind).expanduser()
    if selected.is_symlink():
        raise RuntimeError("artifact is not a regular non-symlink file")
    source = _require_within(selected, allowed_root)
    if not source.is_file():
        raise RuntimeError("artifact is not a regular non-symlink file")
    target = destination.expanduser().resolve()
    if target.exists():
        raise RuntimeError(f"destination already exists: {target}")
    if not target.parent.is_dir():
        raise RuntimeError(f"destination parent does not exist: {target.parent}")
    shutil.copyfile(source, target)
    target.chmod(0o600)
    return target


def _write_private_json(payload: dict[str, object], output: Path) -> None:
    target = output.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.parent.chmod(0o700)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    target.chmod(0o600)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect/copy an existing artifact for a terminal delivery_failed Job."
    )
    parser.add_argument("--db-path", type=Path, default=Path("data/jobs.db"))
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--output", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("inspect")

    copy_parser = subparsers.add_parser("copy")
    copy_parser.add_argument("--artifact", choices=("markdown", "audio"), required=True)
    copy_parser.add_argument("--allowed-root", type=Path, default=Path("data"))
    copy_parser.add_argument("--destination", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = inspect_job(db_path=args.db_path, job_id=args.job_id)
        payload = _report_dict(report)
        if args.command == "copy":
            copied = copy_artifact(
                report=report,
                kind=args.artifact,
                allowed_root=args.allowed_root,
                destination=args.destination,
            )
            payload["copied_artifact"] = args.artifact
            payload["copied_to"] = str(copied)
        if args.output is not None:
            _write_private_json(payload, args.output)
        print(json.dumps(payload, indent=2, sort_keys=True))
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
