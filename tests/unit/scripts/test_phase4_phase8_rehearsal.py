"""Tests for the Phase 4/8 rehearsal helper script."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

SCRIPT_PATH = Path("scripts/ops/phase4_phase8_rehearsal.py")


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("phase4_phase8_rehearsal", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _create_jobs_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE jobs (
                job_id TEXT PRIMARY KEY,
                video_id TEXT NOT NULL,
                status TEXT NOT NULL,
                requested_by_user_id INTEGER NOT NULL,
                requested_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                error_message TEXT,
                config_signature TEXT NOT NULL DEFAULT '',
                source_url TEXT,
                requested_chat_id INTEGER,
                requested_language TEXT,
                artifact_policy TEXT NOT NULL DEFAULT 'audio+markdown',
                speaker_renames_json TEXT NOT NULL DEFAULT '{}',
                md_path TEXT,
                audio_path TEXT,
                log_path TEXT
            )
            """
        )


def test_run_backup_creates_artifacts_and_evidence_snippet(tmp_path: Path, monkeypatch) -> None:
    script = _load_script()
    app_dir = tmp_path / "app"
    db_path = app_dir / "data" / "jobs.db"
    runtime_file = app_dir / "data" / "logs" / "sample.log"
    models_file = app_dir / "models" / "model.bin"
    systemd_env = tmp_path / "systemd-env"
    dotenv = app_dir / ".env"

    _create_jobs_db(db_path)
    runtime_file.parent.mkdir(parents=True, exist_ok=True)
    runtime_file.write_text("hello", encoding="utf-8")
    models_file.parent.mkdir(parents=True, exist_ok=True)
    models_file.write_text("weights", encoding="utf-8")
    systemd_env.write_text("TOKEN=secret\n", encoding="utf-8")
    dotenv.write_text("FOO=bar\n", encoding="utf-8")
    monkeypatch.setattr(script, "_git_head", lambda _app_dir: "abc123")

    args = SimpleNamespace(
        app_dir=app_dir,
        db_path=Path("data/jobs.db"),
        runtime_dir=Path("data"),
        models_dir=Path("models"),
        systemd_env=systemd_env,
        service="yt-transcriber-bot",
        output_dir=tmp_path / "evidence",
        stop_service=False,
        start_service=False,
    )

    snippet_path = script.run_backup(args)

    content = snippet_path.read_text(encoding="utf-8")
    assert "Backup/Restore Rehearsal — Captured Evidence" in content
    assert "abc123" in content

    backup_dirs = [path for path in (tmp_path / "evidence").iterdir() if path.is_dir()]
    assert len(backup_dirs) == 1
    backup_dir = backup_dirs[0]
    assert (backup_dir / "jobs.db").exists()
    assert (backup_dir / "runtime-data.tgz").exists()
    assert (backup_dir / "models.tgz").exists()
    assert (backup_dir / "systemd-env").exists()
    assert (backup_dir / "dotenv").exists()
    assert (backup_dir / "git-revision.txt").read_text(encoding="utf-8").strip() == "abc123"


def test_run_inspect_delivery_failed_reports_jobs_and_errors(tmp_path: Path) -> None:
    script = _load_script()
    app_dir = tmp_path / "app"
    db_path = app_dir / "data" / "jobs.db"
    errors_path = app_dir / "data" / "logs" / "operational_errors.jsonl"
    _create_jobs_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO jobs (
                job_id, video_id, status, requested_by_user_id, requested_at, updated_at,
                error_message, md_path, audio_path, log_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "job-1",
                "yx7UkDppd_M",
                "delivery_failed",
                42,
                "2026-07-10T10:00:00Z",
                "2026-07-10T10:05:00Z",
                "Falha na entrega",
                "data/transcripts/video.md",
                "data/processed/video.ogg",
                None,
            ),
        )
    errors_path.parent.mkdir(parents=True, exist_ok=True)
    errors_path.write_text(
        json.dumps(
            {
                "operation": "transcribe_delivery",
                "job_id": "job-1",
                "message": "delivery failed",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    args = SimpleNamespace(
        app_dir=app_dir,
        db_path=Path("data/jobs.db"),
        errors_path=Path("data/logs/operational_errors.jsonl"),
        output_dir=tmp_path / "evidence",
        limit=5,
    )

    snippet_path = script.run_inspect_delivery_failed(args)

    content = snippet_path.read_text(encoding="utf-8")
    assert "job-1" in content
    assert "transcribe_delivery" in content
    assert "data/transcripts/video.md" in content


def test_run_inspect_restart_recovery_reports_jobs_and_audit(tmp_path: Path) -> None:
    script = _load_script()
    app_dir = tmp_path / "app"
    db_path = app_dir / "data" / "jobs.db"
    audit_path = app_dir / "data" / "logs" / "execution_audit.jsonl"
    _create_jobs_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO jobs (
                job_id, video_id, status, requested_by_user_id, requested_at, updated_at,
                error_message, md_path, audio_path, log_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "job-pending",
                    "aaaaaaaaaaa",
                    "pending",
                    42,
                    "2026-07-10T10:00:00Z",
                    "2026-07-10T10:01:00Z",
                    None,
                    None,
                    None,
                    None,
                ),
                (
                    "job-delivery",
                    "bbbbbbbbbbb",
                    "delivery_failed",
                    42,
                    "2026-07-10T10:02:00Z",
                    "2026-07-10T10:03:00Z",
                    "delivery interrupted",
                    "data/transcripts/b.md",
                    "data/processed/b.ogg",
                    None,
                ),
            ],
        )
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {"event": "job_recovered_requeued", "job_id": "job-pending"},
        {"event": "job_delivery_failed", "job_id": "job-delivery"},
    ]
    audit_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )

    args = SimpleNamespace(
        app_dir=app_dir,
        db_path=Path("data/jobs.db"),
        audit_path=Path("data/logs/execution_audit.jsonl"),
        output_dir=tmp_path / "evidence",
        limit=10,
    )

    snippet_path = script.run_inspect_restart_recovery(args)

    content = snippet_path.read_text(encoding="utf-8")
    assert "job-pending" in content
    assert "job-delivery" in content
    assert "job_recovered_requeued" in content
    assert "job_delivery_failed" in content
