from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src/yt_transcriber_bot"


def test_job_repository_save_has_no_hidden_indexing_or_artifact_reads() -> None:
    source = (SRC / "infrastructure/persistence/sqlalchemy/job_repository.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    cls = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "SqlAlchemyJobRepository"
    )
    save = next(
        node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "save"
    )
    assert "refresh_search_index" not in ast.unparse(save)
    assert "_document_from_artifacts" not in source
    assert "HistorySearchRepository" not in source


def test_summary_policy_is_application_owned_and_provider_free() -> None:
    source = (SRC / "application/services/transcript_summary.py").read_text(encoding="utf-8")
    assert "yt_transcriber_bot.infrastructure" not in source
    assert ".write_text(" not in source
    assert "AutoTokenizer" not in source
    assert "TextGenerationClient" in source


def test_operational_policy_files_have_no_direct_io() -> None:
    for relative in (
        "application/services/healthcheck.py",
        "application/services/last_error.py",
        "application/services/rename_speakers.py",
        "application/services/retention_policy.py",
    ):
        source = (SRC / relative).read_text(encoding="utf-8")
        for token in (".read_text(", ".write_text(", ".unlink(", ".mkdir(", ".rglob("):
            assert token not in source, f"{relative} retains direct I/O: {token}"


def test_runtime_wires_application_subphase_c_workflows() -> None:
    source = (SRC / "composition_root.py").read_text(encoding="utf-8")
    for token in (
        "text_search_workflow=core.text_search_workflow",
        "derivative_workflow=core.derivative_workflow",
        "summary_workflow=core.summary_workflow",
        "operational_workflow=core.operational_workflow",
        "execution_lifecycle=core.execution_lifecycle",
    ):
        assert token in source
