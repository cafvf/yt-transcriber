from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_plan006_round_b_systemd_template_is_least_privilege_oriented() -> None:
    unit = Path("deploy/yt-transcriber-bot.service").read_text(encoding="utf-8")
    assert "User=SEU_USUARIO" in unit
    assert "Group=SEU_USUARIO" in unit
    assert "EnvironmentFile=/etc/yt-transcriber-bot/env" in unit
    assert "NoNewPrivileges=true" in unit
    assert "PrivateTmp=true" in unit
    assert "UMask=0077" in unit
    assert "User=root" not in unit


def test_current_docs_expose_preflight_permissions_and_sanitization_contract() -> None:
    install = Path("docs/04-manual-de-instalacao.md").read_text(encoding="utf-8")
    runbook = Path("docs/11-operator-runbook.md").read_text(encoding="utf-8")
    security = Path("docs/08-seguranca-e-segredos.md").read_text(encoding="utf-8")

    assert "systemd_host_preflight.py" in install
    assert "systemd_host_preflight.py" in runbook
    assert "sudo install -m 0600" in install
    assert "/etc/yt-transcriber-bot/env" in install
    assert "## Sanitização" in security
    assert "Saída sanitizada continua privada" in security


def test_plan006_round_b_rehearsal_uses_evidence_sanitizer() -> None:
    rehearsal = Path("scripts/ops/phase4_phase8_rehearsal.py").read_text(encoding="utf-8")
    assert "sanitize_evidence_text" in rehearsal
    assert "sanitize_evidence_text(result.stdout" in rehearsal
    assert "sanitize_evidence_text(result.stderr" in rehearsal


def test_phase4_phase8_rehearsal_supports_direct_script_execution() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/ops/phase4_phase8_rehearsal.py",
            "--help",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "systemd-smoke" in result.stdout
