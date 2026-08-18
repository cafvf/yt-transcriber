from pathlib import Path


def test_plan006_p06_007_exposes_read_only_preflight_and_explicit_rehearsal() -> None:
    helper = Path("scripts/ops/upgrade_rollback_rehearsal.py").read_text(encoding="utf-8")
    assert 'subparsers.add_parser("preflight")' in helper
    assert 'subparsers.add_parser("rehearsal")' in helper
    assert "--execute" in helper
    assert "requires a clean worktree" in helper
    assert "backup revision" in helper
    assert "merge-base" in helper
    assert "final_production_revision" in helper


def test_plan006_p06_007_runbook_documents_upgrade_rollback_contract() -> None:
    runbook = Path("docs/11-operator-runbook.md").read_text(encoding="utf-8")
    assert "P06-007 — upgrade e rollback versionados" in runbook
    assert "upgrade_rollback_rehearsal.py preflight" in runbook
    assert "upgrade_rollback_rehearsal.py rehearsal" in runbook
    assert "--execute" in runbook
    assert "backup" in runbook.lower()
    assert "/healthcheck" in runbook
    assert "/status" in runbook
