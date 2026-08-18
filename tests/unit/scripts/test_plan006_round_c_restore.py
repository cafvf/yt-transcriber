from __future__ import annotations

import importlib.util
import sqlite3
import sys
import tarfile
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

SCRIPT = Path("scripts/ops/phase4_phase8_rehearsal.py")


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("phase4_phase8_rehearsal_round_c", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _create_db(path: Path, *, reference: str = "canonical-1") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE jobs ("
            "job_id TEXT PRIMARY KEY, status TEXT NOT NULL, "
            "canonical_transcript_ref TEXT, md_path TEXT)"
        )
        conn.execute(
            "INSERT INTO jobs (job_id, status, canonical_transcript_ref, md_path) "
            "VALUES (?, ?, ?, ?)",
            ("job-1", "completed", reference, f"data/transcripts/{reference}.md"),
        )
        conn.execute(
            "CREATE TABLE job_search_documents ("
            "job_id TEXT PRIMARY KEY, canonical_transcript_ref TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO job_search_documents VALUES (?, ?)",
            ("job-1", reference),
        )


def _create_source(app_dir: Path) -> None:
    _create_db(app_dir / "data/jobs.db")
    transcripts = app_dir / "data/transcripts"
    transcripts.mkdir(parents=True)
    (transcripts / "canonical-1.json").write_text("{}", encoding="utf-8")
    (transcripts / "canonical-1.md").write_text("# transcript", encoding="utf-8")
    (app_dir / ".env").write_text("DUMMY_CONFIG=value\n", encoding="utf-8")
    (app_dir / "cookies.txt").write_text("DUMMY-cookie", encoding="utf-8")


def test_backup_then_restore_staging_preserves_history_and_canonical_links(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = _load()
    app_dir = tmp_path / "app"
    _create_source(app_dir)
    monkeypatch.setattr(script, "_git_head", lambda _app: "c513ffa")

    backup_args = SimpleNamespace(
        app_dir=app_dir,
        db_path=Path("data/jobs.db"),
        transcripts_dir=Path("data/transcripts"),
        service="yt-transcriber-bot",
        output_dir=tmp_path / "backup-evidence",
        stop_service=False,
        start_service=False,
    )
    script.run_backup(backup_args)
    backup_dir = next(path for path in (tmp_path / "backup-evidence").iterdir() if path.is_dir())

    restore_root = tmp_path / "restore-staging"
    restore_args = SimpleNamespace(
        app_dir=app_dir,
        backup_dir=backup_dir,
        restore_root=restore_root,
        output_dir=tmp_path / "restore-evidence",
    )
    evidence = script.run_restore_staging(restore_args)

    assert (restore_root / "data/jobs.db").is_file()
    assert (restore_root / "data/transcripts/canonical-1.json").is_file()
    assert (restore_root / "data/transcripts/canonical-1.md").is_file()
    assert not (restore_root / ".env").exists()
    assert not (restore_root / "cookies.txt").exists()

    validation = script._validate_restored_state(restore_root)
    assert validation["sqlite_integrity"] == "ok"
    assert validation["job_count"] == 1
    assert validation["canonical_job_references_validated"] == 1
    assert validation["search_document_references_validated"] == 1
    content = evidence.read_text(encoding="utf-8")
    assert "Production service mutated: `no`" in content
    assert "Credentials/cookies restored: `no`" in content


def test_restore_staging_refuses_application_tree_and_nonempty_target(tmp_path: Path) -> None:
    script = _load()
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    args = SimpleNamespace(
        app_dir=app_dir,
        backup_dir=backup_dir,
        restore_root=app_dir / "restore",
        output_dir=tmp_path / "evidence",
    )
    with pytest.raises(RuntimeError, match="fora da árvore da aplicação"):
        script.run_restore_staging(args)

    # Exercise the non-empty target guard after bypassing backup validation only.
    nonempty = tmp_path / "nonempty"
    nonempty.mkdir()
    (nonempty / "marker").write_text("keep", encoding="utf-8")
    script._validate_standard_backup = lambda _path: None
    args.restore_root = nonempty
    with pytest.raises(RuntimeError, match="ausente ou vazio"):
        script.run_restore_staging(args)


def test_restored_state_accepts_legacy_markdown_only_reference(tmp_path: Path) -> None:
    script = _load()
    restore_root = tmp_path / "restore"
    _create_db(restore_root / "data/jobs.db", reference="legacy")
    transcripts = restore_root / "data/transcripts"
    transcripts.mkdir(parents=True)
    (transcripts / "legacy.md").write_text("# legacy transcript", encoding="utf-8")

    with sqlite3.connect(restore_root / "data/jobs.db") as conn:
        conn.execute("DELETE FROM job_search_documents")

    validation = script._validate_restored_state(restore_root)
    assert validation["canonical_job_references_validated"] == 1
    assert validation["structured_canonical_references"] == 0
    assert validation["legacy_markdown_only_references"] == 1


def test_restored_state_rejects_reference_without_snapshot_or_markdown(tmp_path: Path) -> None:
    script = _load()
    restore_root = tmp_path / "restore"
    _create_db(restore_root / "data/jobs.db", reference="missing")
    (restore_root / "data/transcripts").mkdir(parents=True)

    with sqlite3.connect(restore_root / "data/jobs.db") as conn:
        conn.execute("DELETE FROM job_search_documents")

    with pytest.raises(RuntimeError, match="sem evidência recuperável"):
        script._validate_restored_state(restore_root)


def test_search_document_still_requires_structured_snapshot(tmp_path: Path) -> None:
    script = _load()
    restore_root = tmp_path / "restore"
    _create_db(restore_root / "data/jobs.db", reference="legacy")
    transcripts = restore_root / "data/transcripts"
    transcripts.mkdir(parents=True)
    (transcripts / "legacy.md").write_text("# legacy transcript", encoding="utf-8")

    with pytest.raises(RuntimeError, match=r"Documento de busca.*sem snapshot estruturado"):
        script._validate_restored_state(restore_root)


def test_safe_extract_rejects_path_traversal(tmp_path: Path) -> None:
    script = _load()
    archive = tmp_path / "bad.tgz"
    payload = tmp_path / "payload.txt"
    payload.write_text("DUMMY", encoding="utf-8")
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(payload, arcname="transcripts/../escape.txt")

    with pytest.raises(RuntimeError, match="fora de transcripts"):
        script._safe_extract_canonical_transcripts(archive, tmp_path / "restore")
