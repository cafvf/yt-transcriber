"""PLAN-006/P06-011 final closure-document conformance."""

from __future__ import annotations

import re
from pathlib import Path

BASELINE = "318d90dda0ead178c5df30b899fb4fea4430fc0d"
GATE_DIR = "p06-011-exit-gate-20260818T231226Z"
SUMMARY = (
    "~/Downloads/p06-011-exit-gate-20260818T231226Z/p06-011-exit-gate-summary-20260818T231226Z.txt"
)

EXEC_README = Path("specs/006-execution/README.md")
ROADMAP = Path("specs/006-execution/POST-PLAN-004-EXECUTION-ROADMAP.md")
LEDGER = Path("specs/006-execution/PLAN-006-READINESS-LEDGER.md")
CLOSURE = Path("specs/006-execution/PLAN-006-CLOSURE.md")
READINESS = Path("docs/09-production-readiness.md")
FROZEN_TASKS = Path("specs/005-tasks/PLAN-006-TASKS.md")


def test_p06_011_closure_traces_frozen_exit_gate() -> None:
    frozen = FROZEN_TASKS.read_text(encoding="utf-8")
    closure = CLOSURE.read_text(encoding="utf-8")
    assert "TASK-P06-011" in frozen
    assert "PLAN-006 exit-gate verification" in frozen
    assert "All required host/staging rehearsals" in frozen
    assert "TASK-P06-011" in closure
    assert "PLAN-006 exit gate passed" in closure


def test_p06_011_closure_records_exact_gate_baseline_and_private_summary() -> None:
    closure = CLOSURE.read_text(encoding="utf-8")
    assert BASELINE in closure
    assert SUMMARY in closure
    assert "GREEN / PASS" in closure
    assert "private detailed log" in closure
    assert "are not versioned" in closure


def test_p06_011_closure_records_all_frozen_gate_families() -> None:
    closure = CLOSURE.read_text(encoding="utf-8")
    required = (
        "Required host/staging rehearsals",
        "Credential-free backup/restore",
        "systemd/upgrade/rollback/recovery procedures",
        "README/manual/help/roadmap/readiness conformance",
        "Environment-gated inventory",
        "Final conformance/quality review",
        "Remediation milestone stability",
    )
    for claim in required:
        assert claim in closure
    assert closure.count("**PASS**") >= len(required)


def test_p06_011_stage_b_is_explicitly_non_material_to_operational_evidence() -> None:
    closure = CLOSURE.read_text(encoding="utf-8")
    assert "do not touch" in closure
    assert "`src/`" in closure
    assert "persistence schema" in closure
    assert "operational helpers" in closure
    normalized = " ".join(closure.split())
    assert "not repeated solely for documentation bookkeeping" in normalized


def test_plan006_closure_uses_sanitized_new_private_locators() -> None:
    unsafe_gate_locator = re.compile(rf"/home/[^/]+/Downloads/{re.escape(GATE_DIR)}/")
    for path in (CLOSURE, LEDGER, ROADMAP, READINESS):
        text = path.read_text(encoding="utf-8")
        assert SUMMARY in text, path
        assert unsafe_gate_locator.search(text) is None, path

    closure = CLOSURE.read_text(encoding="utf-8")
    assert "/home/" not in closure


def test_plan006_execution_readme_reports_closed_state() -> None:
    text = EXEC_README.read_text(encoding="utf-8")
    assert "Packages 1-5 / PLAN-006 closed" in text
    assert "TASK-P06-011` exit gate passed" in text
    assert BASELINE in text


def test_plan006_roadmap_marks_all_packages_closed() -> None:
    text = ROADMAP.read_text(encoding="utf-8")
    for package in range(1, 6):
        assert f"[x] Package {package}" in text
    assert "Package 5 closure evidence" in text
    assert "Verified / closed - Production readiness and roadmap closure" in text
    assert BASELINE in text
    assert SUMMARY in text
    assert "pending final PLAN-006 exit-gate verification" not in text
    assert "readiness evidence aggregation is the current task" not in text


def test_p06_010_ledger_is_closed_and_consumed_by_p06_011() -> None:
    text = LEDGER.read_text(encoding="utf-8")
    assert "Verified / closed - TASK-P06-010 readiness evidence accepted" in text
    assert "`TASK-P06-010` is **CLOSED**" in text
    assert "P06-011 exit-gate consumption" in text
    assert BASELINE in text
    assert SUMMARY in text
    assert "READY TO CLOSE" not in text


def test_production_readiness_declares_private_single_operator_baseline_complete() -> None:
    text = READINESS.read_text(encoding="utf-8")
    assert "baseline privada/single-operator está completa" in text
    assert "`TASK-P06-011` passou" in text
    assert BASELINE in text
    assert "[x] Declarar produção privada/single-operator completa" in text
    assert "PLAN-006 exit gate - 2026-08-18" in text
    assert "Nenhum blocker do PLAN-006 permanece" in text
    assert "ainda depende do exit gate" not in text
    assert "ainda precisa confirmar" not in text


def test_plan006_closure_does_not_claim_frozen_out_features() -> None:
    closure = CLOSURE.read_text(encoding="utf-8").lower()
    for future_claim in (
        "semantic search is complete",
        "translation is complete",
        "checkpoint resume is complete",
        "multi-user production is complete",
    ):
        assert future_claim not in closure
