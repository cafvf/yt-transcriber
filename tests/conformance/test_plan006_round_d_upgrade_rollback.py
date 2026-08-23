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


def test_current_runbook_documents_upgrade_rollback_contract() -> None:
    runbook = Path("docs/11-operator-runbook.md").read_text(encoding="utf-8")

    assert "## Atualização" in runbook
    assert "## Rollback" in runbook
    assert "/opt/yt-transcriber-bot/venv/bin/pip install --upgrade ." in runbook
    assert "/opt/yt-transcriber-bot/venv/bin/yt-transcriber-bot --preflight" in runbook
    assert "revisão previamente conhecida" in runbook
    assert "Dados não são revertidos automaticamente com código" in runbook
    assert "backup" in runbook.lower()
    assert "/healthcheck" in runbook
    assert "/status" in runbook
