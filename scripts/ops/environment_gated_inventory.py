"""Reconcile the frozen 46-test environment-gated inventory with current HEAD.

The 46-test baseline belongs to the approved SDD baseline revision recorded by
F0.  This module reconstructs that historical inventory from Git, validates the
five frozen groups independently, and maps each historical slot to a preserved,
replaced, or explicitly retired evidence role.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

FROZEN_INVENTORY_REVISION = "5266d01b660398d0ff25c1bff01eb287114f0d7d"
FROZEN_TOTAL = 46
EXPECTED_CURRENT_TOTAL = 35
EXPECTED_PRESERVED = 30
EXPECTED_REPLACED_HISTORY = 4
EXPECTED_REPLACED_PORTABILITY = 1
EXPECTED_RETIRED = 11

JOB_REPOSITORY = "tests/unit/infrastructure/persistence/test_job_repository.py"
HISTORY_SEARCH = "tests/unit/infrastructure/persistence/test_history_search_repository.py"
LOCAL_FILE_STORAGE = "tests/unit/infrastructure/persistence/test_local_file_storage.py"
FFPROBE_TEST = "tests/unit/infrastructure/telegram/test_ffprobe_duration_inspector.py"
FFPROBE_REPLACEMENT_NODEID = (
    f"{FFPROBE_TEST}::test_real_ffprobe_duration_inspector"
)
FROZEN_FFPROBE_NODEID = (
    "tests/unit/infrastructure/audio/test_ffmpeg_converter.py::"
    "TestFfmpegRealIntegration::test_real_probe_duration"
)
FFMPEG = "tests/unit/infrastructure/audio/test_ffmpeg_converter.py"
BOT_ADAPTER = "tests/unit/infrastructure/telegram/test_bot_adapter.py"

FROZEN_GROUP_COUNTS = {
    JOB_REPOSITORY: 25,
    HISTORY_SEARCH: 4,
    LOCAL_FILE_STORAGE: 11,
    f"{FFMPEG}::TestFfmpegRealIntegration": 3,
    f"{BOT_ADAPTER}::startup_recovery": 3,
}

STARTUP_RECOVERY_TESTS = (
    "test_start_recovers_pending_job_from_sqlite_file",
    "test_start_marks_interrupted_jobs_from_sqlite_file_and_notifies",
    "test_startup_recovery_runs_only_once_per_adapter_instance",
)

HISTORY_REPLACEMENT_EVIDENCE = (
    "tests/unit/infrastructure/persistence/test_history_search_repository.py",
    "tests/unit/application/workflows/test_text_search_workflow.py::"
    "test_search_workflow_owns_rebuild_and_current_history_index",
)

LOCAL_STORAGE_REPLACEMENT_EVIDENCE = (
    "tests/conformance/test_application_port_conventions.py::"
    "test_obsolete_generic_file_storage_surface_is_absent",
    "tests/unit/infrastructure/persistence/test_transcript_snapshot.py",
    "tests/unit/infrastructure/persistence/test_private_staging_cleanup.py",
    "tests/unit/infrastructure/persistence/test_reconstructible_cache.py",
)

MARKER_ROLES = {
    "integration": "integration contract",
    "slow": "slow/model-runtime contract",
    "e2e": "end-to-end contract",
}


@dataclass(frozen=True)
class CollectionResult:
    marker: str
    returncode: int
    stdout: str
    stderr: str


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )


def _git_show(cwd: Path, revision: str, path: str) -> str:
    completed = _run(["git", "show", f"{revision}:{path}"], cwd=cwd)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "<empty>"
        raise RuntimeError(f"git show failed for {revision}:{path}: {detail}")
    return completed.stdout


def _git_head(cwd: Path) -> str:
    completed = _run(["git", "rev-parse", "HEAD"], cwd=cwd)
    if completed.returncode != 0:
        return "<unknown>"
    return completed.stdout.strip()


def _run_pytest_collect(marker: str, *, cwd: Path) -> CollectionResult:
    completed = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "--disable-warnings",
            "-m",
            marker,
        ],
        cwd=cwd,
    )
    return CollectionResult(marker, completed.returncode, completed.stdout, completed.stderr)


def _nodeids(stdout: str) -> tuple[str, ...]:
    # pytest -q --collect-only emits canonical nodeids one-per-line. Restrict the
    # parser to repository test paths so warnings/summaries containing "::" can
    # never inflate the inventory.
    return tuple(
        line.strip()
        for line in stdout.splitlines()
        if line.startswith("tests/") and "::" in line
    )


def _ast_nodeids(path: str, source: str) -> list[str]:
    tree = ast.parse(source, filename=path)
    result: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            result.append(f"{path}::{node.name}")
            continue
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for child in node.body:
                if (
                    isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and child.name.startswith("test_")
                ):
                    result.append(f"{path}::{node.name}::{child.name}")
    return result


def reconstruct_frozen_inventory(cwd: Path) -> tuple[tuple[str, ...], dict[str, int]]:
    groups: dict[str, list[str]] = {}

    for path in (JOB_REPOSITORY, HISTORY_SEARCH, LOCAL_FILE_STORAGE):
        source = _git_show(cwd, FROZEN_INVENTORY_REVISION, path)
        groups[path] = _ast_nodeids(path, source)

    ffmpeg_source = _git_show(cwd, FROZEN_INVENTORY_REVISION, FFMPEG)
    groups[f"{FFMPEG}::TestFfmpegRealIntegration"] = [
        nodeid
        for nodeid in _ast_nodeids(FFMPEG, ffmpeg_source)
        if "::TestFfmpegRealIntegration::" in nodeid
    ]

    adapter_source = _git_show(cwd, FROZEN_INVENTORY_REVISION, BOT_ADAPTER)
    adapter_ids = set(_ast_nodeids(BOT_ADAPTER, adapter_source))
    startup_ids: list[str] = []
    for name in STARTUP_RECOVERY_TESTS:
        nodeid = f"{BOT_ADAPTER}::{name}"
        if nodeid not in adapter_ids:
            raise RuntimeError(f"frozen startup recovery nodeid missing: {nodeid}")
        startup_ids.append(nodeid)
    groups[f"{BOT_ADAPTER}::startup_recovery"] = startup_ids

    observed_counts = {group: len(nodeids) for group, nodeids in groups.items()}
    if observed_counts != FROZEN_GROUP_COUNTS:
        raise RuntimeError(
            "frozen group-count drift at "
            f"{FROZEN_INVENTORY_REVISION}: expected={FROZEN_GROUP_COUNTS!r} "
            f"observed={observed_counts!r}"
        )

    all_nodeids = tuple(sorted(nodeid for nodeids in groups.values() for nodeid in nodeids))
    if len(all_nodeids) != FROZEN_TOTAL:
        raise RuntimeError(
            f"frozen inventory drift: expected {FROZEN_TOTAL}, reconstructed {len(all_nodeids)}"
        )
    if len(set(all_nodeids)) != FROZEN_TOTAL:
        raise RuntimeError("frozen inventory contains duplicate nodeids")
    return all_nodeids, observed_counts


def _current_marker_inventory(cwd: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    merged: dict[str, set[str]] = {}
    collection: dict[str, object] = {}

    for marker, role in MARKER_ROLES.items():
        result = _run_pytest_collect(marker, cwd=cwd)
        if result.returncode not in {0, 5}:
            detail = result.stderr.strip() or result.stdout.strip() or "<empty>"
            raise RuntimeError(
                f"pytest collection failed for {marker} with rc={result.returncode}: {detail}"
            )
        ids = _nodeids(result.stdout)
        collection[marker] = {
            "role": role,
            "returncode": result.returncode,
            "count": len(ids),
        }
        for nodeid in ids:
            merged.setdefault(nodeid, set()).add(marker)

    records = [
        {
            "nodeid": nodeid,
            "markers": sorted(markers),
            "evidence_roles": sorted(MARKER_ROLES[marker] for marker in markers),
        }
        for nodeid, markers in sorted(merged.items())
    ]
    return collection, records


def _execution_state(*, integration_outcome: str, markers: list[str]) -> tuple[str, str]:
    if "integration" in markers and integration_outcome == "executed_pass":
        return "EXECUTED_PASS", "selected by the successful pytest -m integration gate"
    return (
        "NOT_EXECUTED",
        "no successful executing gate was supplied for this marker combination",
    )


def build_lineage(
    *,
    cwd: Path,
    integration_outcome: str = "not_executed",
    replacement_evidence_outcome: str = "not_executed",
) -> dict[str, object]:
    frozen, frozen_group_counts = reconstruct_frozen_inventory(cwd)
    collection, current = _current_marker_inventory(cwd)
    current_by_id = {str(record["nodeid"]): record for record in current}
    current_ids = set(current_by_id)

    integration_count = int(collection["integration"]["count"])
    slow_count = int(collection["slow"]["count"])
    e2e_count = int(collection["e2e"]["count"])
    if integration_count != EXPECTED_CURRENT_TOTAL:
        raise RuntimeError(
            f"current integration inventory drift: expected {EXPECTED_CURRENT_TOTAL}, "
            f"observed {integration_count}"
        )
    if len(current) != EXPECTED_CURRENT_TOTAL:
        raise RuntimeError(
            "current marker-union drift: expected exactly "
            f"{EXPECTED_CURRENT_TOTAL}, observed {len(current)} "
            f"(integration={integration_count}, slow={slow_count}, e2e={e2e_count})"
        )

    current_history = sorted(
        nodeid for nodeid in current_ids if nodeid.startswith(HISTORY_SEARCH + "::")
    )
    if len(current_history) != 3:
        raise RuntimeError(
            f"history-search decomposition drift: expected 3 current integration contracts, "
            f"observed {len(current_history)}"
        )

    baseline_records: list[dict[str, object]] = []
    for nodeid in frozen:
        path = nodeid.split("::", 1)[0]

        if nodeid in current_ids:
            current_record = current_by_id[nodeid]
            execution_state, reason = _execution_state(
                integration_outcome=integration_outcome,
                markers=list(current_record["markers"]),
            )
            baseline_records.append(
                {
                    "baseline_nodeid": nodeid,
                    "lineage_state": "PRESERVED",
                    "current_nodeids": [nodeid],
                    "execution_state": execution_state,
                    "reason": reason,
                    "replacement_evidence": [],
                    "replacement_evidence_outcome": "NOT_APPLICABLE",
                }
            )
            continue

        if nodeid == FROZEN_FFPROBE_NODEID:
            if FFPROBE_REPLACEMENT_NODEID not in current_ids:
                baseline_records.append(
                    {
                        "baseline_nodeid": nodeid,
                        "lineage_state": "MISSING",
                        "current_nodeids": [],
                        "execution_state": "NOT_EXECUTED",
                        "reason": (
                            "the durable real ffmpeg/ffprobe evidence has no current "
                            "replacement integration test"
                        ),
                        "replacement_evidence": [],
                        "replacement_evidence_outcome": "MISSING",
                    }
                )
                continue
            baseline_records.append(
                {
                    "baseline_nodeid": nodeid,
                    "lineage_state": "REPLACED_BY_PORTABILITY_CONTRACT",
                    "current_nodeids": [FFPROBE_REPLACEMENT_NODEID],
                    "execution_state": "NOT_EXECUTED",
                    "reason": (
                        "The historical converter-level duration/split test disappeared "
                        "when split_for_telegram left FfmpegAudioConverter. The durable "
                        "real ffmpeg/ffprobe portability role is now exercised directly "
                        "through FfprobeAudioDurationInspector."
                    ),
                    "replacement_evidence": [FFPROBE_REPLACEMENT_NODEID],
                    "replacement_evidence_outcome": replacement_evidence_outcome.upper(),
                }
            )
            continue

        if path == LOCAL_FILE_STORAGE:
            baseline_records.append(
                {
                    "baseline_nodeid": nodeid,
                    "lineage_state": "RETIRED_WITH_ABSTRACTION",
                    "current_nodeids": [],
                    "execution_state": "NOT_EXECUTED",
                    "reason": (
                        "LocalFileStorage was intentionally removed with the obsolete generic "
                        "FileStorage surface at c666305. Its historical test does not execute "
                        "because the product abstraction no longer exists."
                    ),
                    "replacement_evidence": list(LOCAL_STORAGE_REPLACEMENT_EVIDENCE),
                    "replacement_evidence_outcome": replacement_evidence_outcome.upper(),
                }
            )
            continue

        if path == HISTORY_SEARCH:
            baseline_records.append(
                {
                    "baseline_nodeid": nodeid,
                    "lineage_state": "REPLACED_BY_DECOMPOSITION",
                    "current_nodeids": current_history,
                    "execution_state": "NOT_EXECUTED",
                    "reason": (
                        "The mixed history-search persistence/index/workflow contract was "
                        "decomposed at 0e2bb0a. Three SQLite contracts remain integration-gated "
                        "and rebuild/current-history ownership moved to TextSearchWorkflow."
                    ),
                    "replacement_evidence": [
                        *current_history,
                        *HISTORY_REPLACEMENT_EVIDENCE,
                    ],
                    "replacement_evidence_outcome": replacement_evidence_outcome.upper(),
                }
            )
            continue

        baseline_records.append(
            {
                "baseline_nodeid": nodeid,
                "lineage_state": "MISSING",
                "current_nodeids": [],
                "execution_state": "NOT_EXECUTED",
                "reason": "no preserved nodeid or approved replacement mapping was found",
                "replacement_evidence": [],
                "replacement_evidence_outcome": "MISSING",
            }
        )

    lineage_counts: dict[str, int] = {}
    execution_counts: dict[str, int] = {}
    for record in baseline_records:
        lineage = str(record["lineage_state"])
        execution = str(record["execution_state"])
        lineage_counts[lineage] = lineage_counts.get(lineage, 0) + 1
        execution_counts[execution] = execution_counts.get(execution, 0) + 1

    expected_lineage = {
        "PRESERVED": EXPECTED_PRESERVED,
        "REPLACED_BY_DECOMPOSITION": EXPECTED_REPLACED_HISTORY,
        "REPLACED_BY_PORTABILITY_CONTRACT": EXPECTED_REPLACED_PORTABILITY,
        "RETIRED_WITH_ABSTRACTION": EXPECTED_RETIRED,
    }
    missing = lineage_counts.get("MISSING", 0)
    if missing:
        raise RuntimeError(f"baseline lineage has {missing} unmapped test(s)")
    for state, expected in expected_lineage.items():
        observed = lineage_counts.get(state, 0)
        if observed != expected:
            raise RuntimeError(
                f"baseline lineage drift for {state}: expected {expected}, observed {observed}"
            )

    baseline_set = set(frozen)
    current_extra = [
        {
            **record,
            "lineage_state": "POST_BASELINE_OR_REPLACEMENT_CURRENT_TEST",
            "execution_state": _execution_state(
                integration_outcome=integration_outcome,
                markers=list(record["markers"]),
            )[0],
        }
        for record in current
        if str(record["nodeid"]) not in baseline_set
    ]
    if len(current_extra) != 5:
        raise RuntimeError(
            f"current post-baseline/replacement drift: expected 5, observed {len(current_extra)}"
        )

    return {
        "schema_version": 3,
        "revision": _git_head(cwd),
        "frozen_inventory": {
            "revision": FROZEN_INVENTORY_REVISION,
            "total": FROZEN_TOTAL,
            "group_counts": frozen_group_counts,
            "source": "specs/002-requirements/EVIDENCE-INVENTORY.md",
            "f0_evidence": "specs/006-execution/F0-BASELINE.md",
        },
        "current_collection": collection,
        "current_records": current,
        "current_total": len(current),
        "baseline_records": baseline_records,
        "baseline_summary": {
            "total": len(baseline_records),
            "lineage_counts": lineage_counts,
            "execution_counts": execution_counts,
            "missing": missing,
        },
        "current_extra_records": current_extra,
        "policy": {
            "historical_test_removal_requires_explicit_lineage": True,
            "retired_abstraction_is_not_recreated_for_test_count": True,
            "replacement_evidence_is_explicit": True,
            "collection_is_not_execution": integration_outcome != "executed_pass",
            "false_pass_is_forbidden": True,
        },
    }


def write_lineage(
    *,
    cwd: Path,
    output: Path,
    integration_outcome: str,
    replacement_evidence_outcome: str,
) -> Path:
    report = build_lineage(
        cwd=cwd,
        integration_outcome=integration_outcome,
        replacement_evidence_outcome=replacement_evidence_outcome,
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    # Atomic replacement avoids a truncated JSON report being mistaken for
    # evidence after interruption.
    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=output.parent,
        prefix=f".{output.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        json.dump(report, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.chmod(0o600)
    os.replace(temporary, output)
    output.chmod(0o600)
    return output


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reconcile the frozen 46-test inventory with current environment-gated tests."
    )
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-frozen-only", action="store_true")
    parser.add_argument(
        "--integration-outcome",
        choices=("not_executed", "executed_pass"),
        default="not_executed",
    )
    parser.add_argument(
        "--replacement-evidence-outcome",
        choices=("not_executed", "pass"),
        default="not_executed",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    cwd = args.cwd.resolve()
    try:
        if args.validate_frozen_only:
            nodeids, counts = reconstruct_frozen_inventory(cwd)
            print(
                json.dumps(
                    {
                        "revision": FROZEN_INVENTORY_REVISION,
                        "total": len(nodeids),
                        "group_counts": counts,
                    },
                    sort_keys=True,
                )
            )
            return 0

        if args.output is None:
            raise RuntimeError("--output is required unless --validate-frozen-only is used")

        path = write_lineage(
            cwd=cwd,
            output=args.output.resolve(),
            integration_outcome=args.integration_outcome,
            replacement_evidence_outcome=args.replacement_evidence_outcome,
        )
    except (RuntimeError, OSError, SyntaxError, ValueError) as exc:
        print(f"LINEAGE_FAILED: {exc}", file=sys.stderr)
        return 2
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
