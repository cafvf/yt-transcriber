from pathlib import Path


def test_plan006_round_c_exposes_isolated_restore_command() -> None:
    rehearsal = Path("scripts/ops/phase4_phase8_rehearsal.py").read_text(encoding="utf-8")
    assert '"restore-staging"' in rehearsal
    assert "def run_restore_staging" in rehearsal
    assert "_validate_restored_state" in rehearsal
    assert "_safe_extract_canonical_transcripts" in rehearsal


def test_plan006_round_c_runbook_keeps_credentials_outside_restore() -> None:
    runbook = Path("docs/11-operator-runbook.md").read_text(encoding="utf-8")
    assert "P06-006 — backup credential-free e restore validado" in runbook
    assert "restore-staging" in runbook
    assert ".env" in runbook
    assert "/etc/yt-transcriber-bot/env" in runbook
    assert "cookies" in runbook.lower()
    assert "staging isolado" in runbook.lower()
    assert "/healthcheck" in runbook
    assert "/status" in runbook
    assert "/list" in runbook
