from pathlib import Path


def test_plan006_round_c_exposes_isolated_restore_command() -> None:
    rehearsal = Path("scripts/ops/phase4_phase8_rehearsal.py").read_text(encoding="utf-8")
    assert '"restore-staging"' in rehearsal
    assert "def run_restore_staging" in rehearsal
    assert "_validate_restored_state" in rehearsal
    assert "_safe_extract_canonical_transcripts" in rehearsal


def test_current_runbook_keeps_credentials_outside_restore() -> None:
    runbook = Path("docs/11-operator-runbook.md").read_text(encoding="utf-8")

    assert "## Backup credential-free" in runbook
    assert "## Restore" in runbook
    assert "/etc/yt-transcriber-bot/env" in runbook
    assert "cookies" in runbook.lower()
    assert "Credenciais/cookies são reprovisionados separadamente" in runbook
    assert "PRAGMA integrity_check" in runbook
    assert "/healthcheck" in runbook
    assert "/status" in runbook
    assert "/list" in runbook
