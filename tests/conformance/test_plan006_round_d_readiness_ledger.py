"""P06-010 readiness-ledger conformance evidence."""

from __future__ import annotations

import re
from pathlib import Path

LEDGER = Path("specs/006-execution/PLAN-006-READINESS-LEDGER.md")
REQ = Path("specs/003-atomic-requirements/REQ-OPS-007.md")
TASKS = Path("specs/005-tasks/PLAN-006-TASKS.md")
READINESS = Path("docs/09-production-readiness.md")
EXEC_README = Path("specs/006-execution/README.md")
EXEC_ROADMAP = Path("specs/006-execution/POST-PLAN-004-EXECUTION-ROADMAP.md")
LINEAGE = Path("specs/006-execution/PLAN-006-ENVIRONMENT-GATED-LINEAGE.md")

BASELINE = "ed3985b7e9337cbd05a3dec896c29845865fbda2"

RECORDS = {
    "E-001": ("TASK-P06-001", "implemented/tested assurance"),
    "E-003": ("TASK-P06-003", "empirically rehearsed"),
    "E-004": ("TASK-P06-004", "implemented/tested behavior"),
    "E-005": ("TASK-P06-005", "empirically rehearsed"),
    "E-006": ("TASK-P06-006", "empirically rehearsed"),
    "E-007": ("TASK-P06-007", "empirically rehearsed"),
    "E-008": ("TASK-P06-008", "empirically rehearsed"),
}

REQUIRED_FIELDS = (
    "- Owner task:",
    "- Requirement:",
    "- Revision:",
    "- Environment class:",
    "- Objective:",
    "- Actions:",
    "- Expected:",
    "- Observed:",
    "- Decision:",
    "- Evidence mode:",
    "- Evidence source:",
    "- Materiality / reuse:",
)


def _record(text: str, record_id: str) -> str:
    match = re.search(
        rf"^## {re.escape(record_id)} —.*?(?=^## E-\d{{3}} —|^## REQ-OPS-007|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    assert match is not None, record_id
    return match.group(0)


def test_p06_010_frozen_sources_are_traceable() -> None:
    requirement = REQ.read_text(encoding="utf-8")
    tasks = TASKS.read_text(encoding="utf-8")

    assert "REQ-OPS-007 — Reproducible host/staging readiness evidence" in requirement
    assert "helper-script tests alone SHALL not count as proof" in requirement
    assert "## TASK-P06-010 — Reproducible host/staging readiness evidence" in tasks
    assert "evidence aggregator / owner" in tasks


def test_p06_010_ledger_has_every_required_record_and_field() -> None:
    ledger = LEDGER.read_text(encoding="utf-8")

    assert BASELINE in ledger
    for record_id, (owner, _) in RECORDS.items():
        block = _record(ledger, record_id)
        assert f"- Owner task: `{owner}`" in block
        for field in REQUIRED_FIELDS:
            assert field in block, f"{record_id}: {field}"
        assert "- Decision: **PASS**" in block


def test_p06_010_distinguishes_tested_from_empirically_rehearsed() -> None:
    ledger = LEDGER.read_text(encoding="utf-8")

    for record_id, (_, evidence_mode) in RECORDS.items():
        block = _record(ledger, record_id)
        assert f"- Evidence mode: `{evidence_mode}`" in block

    empirical = {
        "E-003",
        "E-005",
        "E-006",
        "E-007",
        "E-008",
    }
    tested_only = {"E-001", "E-004"}

    for record_id in empirical:
        assert "empirically rehearsed" in _record(ledger, record_id)
    for record_id in tested_only:
        assert "implemented/tested" in _record(ledger, record_id)


def test_p06_010_ledger_records_materiality_for_reused_rehearsals() -> None:
    ledger = LEDGER.read_text(encoding="utf-8")

    rollback = _record(ledger, "E-007")
    recovery = _record(ledger, "E-008")
    systemd = _record(ledger, "E-005")

    assert "33af49fbdb94bfd7c5c98c25f63ac9d2147c50de" in rollback
    assert BASELINE in rollback
    assert "did not change `scripts/ops/upgrade_rollback_rehearsal.py`" in rollback

    assert "595ae9d8afc65dd2fdbdb5c6d3d994b963329de0" in recovery
    assert BASELINE in recovery
    assert "manual-recovery helper/service contract was not changed" in recovery

    assert "exact two-file worktree later committed" in systemd
    assert BASELINE in systemd


def test_p06_010_versioned_ledger_contains_no_raw_private_evidence() -> None:
    ledger = LEDGER.read_text(encoding="utf-8")

    assert "/home/" not in ledger
    assert re.search(r"\bhf_[A-Za-z0-9_-]{10,}", ledger) is None
    assert re.search(r"\b\d{8,}:[A-Za-z0-9_-]{20,}\b", ledger) is None
    assert re.search(r"\buser_id\s*[=:]\s*\d+", ledger) is None
    assert re.search(r"\bchat_id\s*[=:]\s*\d+", ledger) is None
    assert "Authorization: Bearer " not in ledger
    assert "Cookie:" not in ledger
    assert "transcript body" not in ledger
    assert "`~/Downloads/" in ledger


def test_p06_010_acceptance_review_is_explicit() -> None:
    ledger = LEDGER.read_text(encoding="utf-8")

    for acceptance in ("AC-01", "AC-02", "AC-03", "AC-04"):
        assert f"- {acceptance} — **PASS**" in ledger
    assert "`TASK-P06-010` is **CLOSED**" in ledger
    assert "P06-011 exit-gate consumption" in ledger
    assert "318d90dda0ead178c5df30b899fb4fea4430fc0d" in ledger


def test_current_readiness_is_operational_not_plan006_evidence_ledger() -> None:
    readiness = READINESS.read_text(encoding="utf-8")

    stale = (
        "aguardando ensaios reais",
        "Pendente de ensaios reais",
        "Falta ensaio real em host systemd",
        "Procedimentos são documentados, mas smoke",
        "- [ ] Executar e registrar ensaio real de backup/restore",
        "- [ ] Executar e registrar smoke real de systemd",
        "- [ ] Executar e registrar ensaio de recovery de `delivery_failed`",
    )
    for phrase in stale:
        assert phrase not in readiness

    assert "Estado operacional atual para produção privada/single-operator em Linux" in readiness
    assert "EnvironmentFile=/etc/yt-transcriber-bot/env" in readiness
    assert "yt-transcriber-bot --preflight" in readiness
    assert "backup credential-free planejado" in readiness
    assert "TASK-P06-" not in readiness
    assert "~/Downloads/" not in readiness
    assert BASELINE not in readiness


def test_p06_010_execution_tracking_reports_plan006_closed() -> None:
    readme = EXEC_README.read_text(encoding="utf-8")
    roadmap = EXEC_ROADMAP.read_text(encoding="utf-8")

    assert "Packages 1-5 / PLAN-006 closed" in readme
    assert "`TASK-P06-011` exit gate passed" in readme
    assert "318d90dda0ead178c5df30b899fb4fea4430fc0d" in readme

    assert "Package 4 closure evidence" in roadmap
    assert "Package 5 closure evidence" in roadmap
    assert "Verified / closed" in roadmap
    assert BASELINE in roadmap
    assert "318d90dda0ead178c5df30b899fb4fea4430fc0d" in roadmap
    assert "`TASK-P06-010`" in roadmap
    assert "`TASK-P06-011`" in roadmap
    assert "Package 5 current state" not in roadmap


def test_p06_010_preserves_environment_gated_lineage() -> None:
    lineage = LINEAGE.read_text(encoding="utf-8")

    assert "46" in lineage
    assert "35" in lineage
    assert "MISSING" in lineage
    assert "0" in lineage
