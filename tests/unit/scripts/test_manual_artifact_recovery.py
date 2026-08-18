from __future__ import annotations

import importlib.util
import stat
import sys
from pathlib import Path
from types import ModuleType

import pytest

from yt_transcriber_bot.application.services.manual_artifact_recovery import (
    ArtifactRecoveryState,
    ManualArtifactRecoveryReport,
    RecoverableArtifact,
)
from yt_transcriber_bot.domain.entities.job import JobStatus

SCRIPT = Path("scripts/ops/manual_artifact_recovery.py")


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("manual_artifact_recovery", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _report(path: Path | None, state: ArtifactRecoveryState) -> ManualArtifactRecoveryReport:
    return ManualArtifactRecoveryReport(
        job_id="job-recovery",
        status=JobStatus.DELIVERY_FAILED,
        eligible=True,
        artifacts=(
            RecoverableArtifact("markdown", path, state),
            RecoverableArtifact("audio", None, ArtifactRecoveryState.REFERENCE_ABSENT),
        ),
    )


def test_copy_is_explicit_private_and_does_not_overwrite(tmp_path: Path) -> None:
    module = _load()
    source_root = tmp_path / "data"
    source_root.mkdir()
    source = source_root / "artifact.md"
    source.write_text("preserved", encoding="utf-8")
    destination = tmp_path / "recovered.md"

    copied = module.copy_artifact(
        report=_report(source, ArtifactRecoveryState.AVAILABLE),
        kind="markdown",
        allowed_root=source_root,
        destination=destination,
    )

    assert copied.read_text(encoding="utf-8") == "preserved"
    assert stat.S_IMODE(copied.stat().st_mode) == 0o600
    assert source.read_text(encoding="utf-8") == "preserved"
    with pytest.raises(RuntimeError, match="already exists"):
        module.copy_artifact(
            report=_report(source, ArtifactRecoveryState.AVAILABLE),
            kind="markdown",
            allowed_root=source_root,
            destination=destination,
        )


def test_copy_rejects_source_outside_allowed_root(tmp_path: Path) -> None:
    module = _load()
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    source = tmp_path / "outside.md"
    source.write_text("private", encoding="utf-8")

    with pytest.raises(RuntimeError, match="outside allowed root"):
        module.copy_artifact(
            report=_report(source, ArtifactRecoveryState.AVAILABLE),
            kind="markdown",
            allowed_root=allowed,
            destination=tmp_path / "copy.md",
        )


@pytest.mark.parametrize(
    ("state", "message"),
    [
        (ArtifactRecoveryState.REFERENCE_ABSENT, "no persisted reference"),
        (ArtifactRecoveryState.REFERENCED_MISSING, "local file is missing"),
    ],
)
def test_copy_refuses_unavailable_artifact(
    state: ArtifactRecoveryState,
    message: str,
) -> None:
    module = _load()
    with pytest.raises(RuntimeError, match=message):
        module._selected_artifact(_report(None, state), "markdown")


def test_report_contract_records_no_implicit_actions(tmp_path: Path) -> None:
    module = _load()
    report = _report(tmp_path / "a.md", ArtifactRecoveryState.AVAILABLE)
    payload = module._report_dict(report)
    assert payload["implicit_resend"] is False
    assert payload["job_reopened"] is False
    assert payload["recomputation_triggered"] is False


def test_copy_rejects_symlink_before_path_resolution(tmp_path: Path) -> None:
    module = _load()
    source_root = tmp_path / "data"
    source_root.mkdir()
    real = source_root / "real.md"
    real.write_text("private", encoding="utf-8")
    link = source_root / "link.md"
    link.symlink_to(real)
    destination = tmp_path / "copy.md"

    with pytest.raises(RuntimeError, match="non-symlink"):
        module.copy_artifact(
            report=_report(link, ArtifactRecoveryState.AVAILABLE),
            kind="markdown",
            allowed_root=source_root,
            destination=destination,
        )

    assert not destination.exists()
