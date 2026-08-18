"""Tests for PLAN-006 frozen/current environment-gated lineage."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT_PATH = Path("scripts/ops/environment_gated_inventory.py")


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("environment_gated_inventory", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_ast_nodeids_handles_module_and_class_tests() -> None:
    script = _load_script()
    source = """
def test_top():
    pass

class TestGroup:
    def test_one(self):
        pass
    async def test_two(self):
        pass
"""
    assert script._ast_nodeids("tests/example.py", source) == [
        "tests/example.py::test_top",
        "tests/example.py::TestGroup::test_one",
        "tests/example.py::TestGroup::test_two",
    ]


def test_nodeid_parser_ignores_warnings_and_summaries() -> None:
    script = _load_script()
    output = """tests/a.py::test_one
tests/b.py::TestB::test_two[param]
WARNING pkg::thing is deprecated
=== 2/10 tests collected ===
"""
    assert script._nodeids(output) == (
        "tests/a.py::test_one",
        "tests/b.py::TestB::test_two[param]",
    )


def test_frozen_inventory_reconstructs_exact_baseline_groups() -> None:
    script = _load_script()
    nodeids, counts = script.reconstruct_frozen_inventory(Path.cwd())
    assert len(nodeids) == 46
    assert counts == {
        script.JOB_REPOSITORY: 25,
        script.HISTORY_SEARCH: 4,
        script.LOCAL_FILE_STORAGE: 11,
        f"{script.FFMPEG}::TestFfmpegRealIntegration": 3,
        f"{script.BOT_ADAPTER}::startup_recovery": 3,
    }
    assert script.FROZEN_FFPROBE_NODEID in nodeids


def _fake_frozen(script: ModuleType) -> tuple[str, ...]:
    preserved = [f"tests/preserved.py::test_{idx}" for idx in range(30)]
    history = [f"{script.HISTORY_SEARCH}::test_old_{idx}" for idx in range(4)]
    local = [f"{script.LOCAL_FILE_STORAGE}::TestLocal::test_old_{idx}" for idx in range(11)]
    return tuple(preserved + history + local + [script.FROZEN_FFPROBE_NODEID])


def _fake_current(script: ModuleType) -> list[dict[str, object]]:
    records: list[dict[str, object]] = [
        {
            "nodeid": f"tests/preserved.py::test_{idx}",
            "markers": ["integration"],
            "evidence_roles": ["integration contract"],
        }
        for idx in range(30)
    ]
    records.extend(
        {
            "nodeid": f"{script.HISTORY_SEARCH}::test_new_{idx}",
            "markers": ["integration"],
            "evidence_roles": ["integration contract"],
        }
        for idx in range(3)
    )
    records.extend(
        [
            {
                "nodeid": script.FFPROBE_REPLACEMENT_NODEID,
                "markers": ["integration"],
                "evidence_roles": ["integration contract"],
            },
            {
                "nodeid": "tests/new_job_migration.py::test_new",
                "markers": ["integration"],
                "evidence_roles": ["integration contract"],
            },
        ]
    )
    return records


def _collection() -> dict[str, object]:
    return {
        "integration": {"count": 35},
        "slow": {"count": 0},
        "e2e": {"count": 0},
    }


def test_lineage_reconciles_all_46_without_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = _load_script()
    frozen = _fake_frozen(script)
    current = _fake_current(script)

    monkeypatch.setattr(
        script,
        "reconstruct_frozen_inventory",
        lambda _cwd: (frozen, script.FROZEN_GROUP_COUNTS),
    )
    monkeypatch.setattr(
        script,
        "_current_marker_inventory",
        lambda _cwd: (_collection(), current),
    )
    monkeypatch.setattr(script, "_git_head", lambda _cwd: "abc123")

    report = script.build_lineage(
        cwd=tmp_path,
        integration_outcome="executed_pass",
        replacement_evidence_outcome="pass",
    )

    summary = report["baseline_summary"]
    assert summary["total"] == 46
    assert summary["missing"] == 0
    assert summary["lineage_counts"] == {
        "PRESERVED": 30,
        "REPLACED_BY_DECOMPOSITION": 4,
        "REPLACED_BY_PORTABILITY_CONTRACT": 1,
        "RETIRED_WITH_ABSTRACTION": 11,
    }
    assert summary["execution_counts"] == {
        "EXECUTED_PASS": 30,
        "NOT_EXECUTED": 16,
    }
    assert report["current_total"] == 35
    assert len(report["current_extra_records"]) == 5


def test_missing_ffprobe_replacement_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = _load_script()
    frozen = _fake_frozen(script)
    current = [
        record
        for record in _fake_current(script)
        if record["nodeid"] != script.FFPROBE_REPLACEMENT_NODEID
    ]
    current.append(
        {
            "nodeid": "tests/unrelated.py::test_extra",
            "markers": ["integration"],
            "evidence_roles": ["integration contract"],
        }
    )

    monkeypatch.setattr(
        script,
        "reconstruct_frozen_inventory",
        lambda _cwd: (frozen, script.FROZEN_GROUP_COUNTS),
    )
    monkeypatch.setattr(
        script,
        "_current_marker_inventory",
        lambda _cwd: (_collection(), current),
    )

    with pytest.raises(RuntimeError, match="unmapped"):
        script.build_lineage(cwd=tmp_path)


def test_current_integration_count_drift_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = _load_script()
    frozen = _fake_frozen(script)
    current = _fake_current(script)[:-1]

    monkeypatch.setattr(
        script,
        "reconstruct_frozen_inventory",
        lambda _cwd: (frozen, script.FROZEN_GROUP_COUNTS),
    )
    monkeypatch.setattr(
        script,
        "_current_marker_inventory",
        lambda _cwd: (
            {
                "integration": {"count": 34},
                "slow": {"count": 0},
                "e2e": {"count": 0},
            },
            current,
        ),
    )

    with pytest.raises(RuntimeError, match="current integration inventory drift"):
        script.build_lineage(cwd=tmp_path)


def test_collection_only_never_claims_execution_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = _load_script()
    frozen = _fake_frozen(script)
    current = _fake_current(script)

    monkeypatch.setattr(
        script,
        "reconstruct_frozen_inventory",
        lambda _cwd: (frozen, script.FROZEN_GROUP_COUNTS),
    )
    monkeypatch.setattr(
        script,
        "_current_marker_inventory",
        lambda _cwd: (_collection(), current),
    )

    report = script.build_lineage(cwd=tmp_path)
    preserved = [
        record for record in report["baseline_records"] if record["lineage_state"] == "PRESERVED"
    ]
    assert all(record["execution_state"] == "NOT_EXECUTED" for record in preserved)


def test_written_lineage_is_private_and_valid_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = _load_script()
    monkeypatch.setattr(
        script,
        "build_lineage",
        lambda **_kwargs: {
            "baseline_summary": {"total": 46, "missing": 0},
            "current_total": 35,
        },
    )

    output = script.write_lineage(
        cwd=tmp_path,
        output=tmp_path / "evidence" / "lineage.json",
        integration_outcome="executed_pass",
        replacement_evidence_outcome="pass",
    )

    assert output.exists()
    assert output.stat().st_mode & 0o777 == 0o600
    assert json.loads(output.read_text(encoding="utf-8"))["current_total"] == 35
