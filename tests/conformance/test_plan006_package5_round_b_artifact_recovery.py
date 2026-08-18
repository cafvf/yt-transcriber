from pathlib import Path

REQ = Path("specs/003-atomic-requirements/REQ-OPS-006.md")
SCENARIO = Path("specs/001-use-cases/operational-scenarios/OS-004-MANUAL-ARTIFACT-RECOVERY.md")
SERVICE = Path("src/yt_transcriber_bot/application/services/manual_artifact_recovery.py")
HELPER = Path("scripts/ops/manual_artifact_recovery.py")
RUNBOOK = Path("docs/11-operator-runbook.md")


def test_p06_008_manual_recovery_contract_is_traceable() -> None:
    requirement = REQ.read_text(encoding="utf-8")
    scenario = SCENARIO.read_text(encoding="utf-8")
    service = SERVICE.read_text(encoding="utf-8")
    helper = HELPER.read_text(encoding="utf-8")
    runbook = RUNBOOK.read_text(encoding="utf-8")

    assert "delivery_failed" in requirement
    assert "No implicit resend or Job reopen" in requirement
    assert "Automatic re-delivery is not part" in scenario
    assert "JobStatus.DELIVERY_FAILED" in service
    assert '"implicit_resend": False' in helper
    assert '"job_reopened": False' in helper
    assert '"recomputation_triggered": False' in helper
    assert "P06-008" in runbook
    assert "manual_artifact_recovery.py" in runbook
