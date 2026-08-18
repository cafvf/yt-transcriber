"""PLAN-006 Package 4 Round A conformance checks."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path


def test_supported_python_versions_match_metadata_ci_and_install_docs() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]
    ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    install = Path("docs/04-manual-de-instalacao.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    supported = {"3.11", "3.12"}
    assert project["requires-python"] == ">=3.11,<3.13"
    classifiers = set(project["classifiers"])
    for version in supported:
        assert f"Programming Language :: Python :: {version}" in classifiers

    ci_versions = set(re.findall(r'^\s*-\s*"(\d+\.\d+)"\s*$', ci, flags=re.MULTILINE))
    assert supported <= ci_versions
    assert "Python 3.11 ou 3.12" in readme
    assert "Python 3.11 ou 3.12" in install


def test_supported_linux_and_system_dependencies_have_preflight_evidence_path() -> None:
    install = Path("docs/04-manual-de-instalacao.md").read_text(encoding="utf-8")
    runbook = Path("docs/11-operator-runbook.md").read_text(encoding="utf-8")

    for phrase in ("Fedora 38+", "Ubuntu 22.04+", "WSL2"):
        assert phrase in install
    for dependency in ("uv", "ffmpeg", "ffprobe"):
        assert dependency in runbook
    assert "/healthcheck" in runbook


def test_environment_gated_inventory_preserves_frozen_46_lineage() -> None:
    helper = Path("scripts/ops/environment_gated_inventory.py").read_text(encoding="utf-8")
    lineage = Path("specs/006-execution/PLAN-006-ENVIRONMENT-GATED-LINEAGE.md").read_text(
        encoding="utf-8"
    )

    assert 'FROZEN_INVENTORY_REVISION = "5266d01b660398d0ff25c1bff01eb287114f0d7d"' in helper
    assert "FROZEN_TOTAL = 46" in helper
    assert "EXPECTED_PRESERVED = 30" in helper
    assert "EXPECTED_REPLACED_HISTORY = 4" in helper
    assert "EXPECTED_REPLACED_PORTABILITY = 1" in helper
    assert "EXPECTED_RETIRED = 11" in helper
    assert "JOB_REPOSITORY: 25" in helper
    assert "HISTORY_SEARCH: 4" in helper
    assert "LOCAL_FILE_STORAGE: 11" in helper
    assert "46 = 30 + 4 + 1 + 11" in lineage
    assert "5266d01b" in lineage
    assert "c666305" in lineage
    assert "0e2bb0a" in lineage


def test_current_docs_do_not_claim_mid_stage_checkpoint_resume() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    runbook = Path("docs/11-operator-runbook.md").read_text(encoding="utf-8")
    recovery = Path("src/yt_transcriber_bot/application/services/startup_recovery.py").read_text(
        encoding="utf-8"
    )

    assert re.search(r"não\s+retomam no meio de ASR ou diarização", readme)
    assert "não retoma o meio da etapa" in runbook
    assert "Job interrompido por reinício do processo antes da conclusão" in recovery
    assert "checkpoint resume" not in readme.lower()
    assert "checkpoint resume" not in runbook.lower()
