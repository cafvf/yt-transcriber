"""Tests for the Phase 4/8 rehearsal helper script."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import stat
import sys
import tarfile
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

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


def test_run_backup_creates_credential_free_standard_dataset(tmp_path: Path, monkeypatch) -> None:
    script = _load_script()
    app_dir = tmp_path / "app"
    db_path = app_dir / "data" / "jobs.db"
    runtime_file = app_dir / "data" / "logs" / "sample.log"
    models_file = app_dir / "models" / "model.bin"
    systemd_env = tmp_path / "systemd-env"
    dotenv = app_dir / ".env"
    cookie_file = app_dir / "data" / "cookies.txt"
    snapshot = app_dir / "data" / "transcripts" / "canonical-1.json"
    markdown = app_dir / "data" / "transcripts" / "canonical-1.md"

    _create_jobs_db(db_path)
    runtime_file.parent.mkdir(parents=True, exist_ok=True)
    runtime_file.write_text("hello", encoding="utf-8")
    models_file.parent.mkdir(parents=True, exist_ok=True)
    models_file.write_text("weights", encoding="utf-8")
    systemd_env.write_text("RUNTIME_VALUE=placeholder\n", encoding="utf-8")
    dotenv.write_text("NONSECRET_EXAMPLE=value\n", encoding="utf-8")
    cookie_file.write_text("cookie placeholder", encoding="utf-8")
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text('{"schema_version": 2}', encoding="utf-8")
    markdown.write_text("# canonical transcript", encoding="utf-8")
    monkeypatch.setattr(script, "_git_head", lambda _app_dir: "abc123")

    args = SimpleNamespace(
        app_dir=app_dir,
        db_path=Path("data/jobs.db"),
        transcripts_dir=Path("data/transcripts"),
        service="yt-transcriber-bot",
        output_dir=tmp_path / "evidence",
        stop_service=False,
        start_service=False,
    )

    snippet_path = script.run_backup(args)

    content = snippet_path.read_text(encoding="utf-8")
    assert "Standard Credential-Free Backup" in content
    assert "Credentials/cookies copied: `no`" in content
    assert "TASK-P06-006" in content
    assert "abc123" in content

    backup_dirs = [path for path in (tmp_path / "evidence").iterdir() if path.is_dir()]
    assert len(backup_dirs) == 1
    backup_dir = backup_dirs[0]
    assert (backup_dir / "jobs.db").exists()
    assert (backup_dir / "canonical-transcripts.tgz").exists()
    assert (backup_dir / "backup-contract.json").exists()
    assert (backup_dir / "git-revision.txt").read_text(encoding="utf-8").strip() == "abc123"

    assert not (backup_dir / "runtime-data.tgz").exists()
    assert not (backup_dir / "models.tgz").exists()
    assert not (backup_dir / "systemd-env").exists()
    assert not (backup_dir / "dotenv").exists()
    assert not (backup_dir / ".env").exists()
    assert not (backup_dir / "cookies.txt").exists()

    with tarfile.open(backup_dir / "canonical-transcripts.tgz", "r:gz") as tar:
        members = {member.name for member in tar.getmembers()}
    assert "transcripts/canonical-1.json" in members
    assert "transcripts/canonical-1.md" in members
    assert all(name == "transcripts" or name.startswith("transcripts/") for name in members)
    assert not any("logs/" in name for name in members)
    assert not any("cookies" in name.lower() for name in members)

    contract = json.loads((backup_dir / "backup-contract.json").read_text(encoding="utf-8"))
    assert contract["included_classes"] == [
        "sqlite_job_history",
        "canonical_transcripts",
        "git_revision",
    ]
    assert contract["credentials_reprovisioned_separately"] is True
    assert "provider_credentials" in contract["excluded_classes"]
    assert "authentication_cookies" in contract["excluded_classes"]

    with sqlite3.connect(backup_dir / "jobs.db") as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)

    assert stat.S_IMODE(backup_dir.stat().st_mode) == 0o700
    for artifact in backup_dir.iterdir():
        assert stat.S_IMODE(artifact.stat().st_mode) == 0o600
    assert stat.S_IMODE(snippet_path.stat().st_mode) == 0o600


def test_run_backup_restarts_service_when_backup_fails_after_stop(
    tmp_path: Path, monkeypatch
) -> None:
    script = _load_script()
    commands: list[tuple[str, ...]] = []

    def fake_run(command, **_kwargs):
        commands.append(tuple(command))
        return script.CommandResult(tuple(command), 0, "", "")

    monkeypatch.setattr(script, "_run", fake_run)
    monkeypatch.setattr(
        script, "_sqlite_backup", lambda *_args: (_ for _ in ()).throw(OSError("disk"))
    )
    args = SimpleNamespace(
        app_dir=tmp_path,
        db_path=Path("data/jobs.db"),
        runtime_dir=Path("data"),
        models_dir=Path("models"),
        systemd_env=tmp_path / "systemd-env",
        service="yt-transcriber-bot",
        output_dir=tmp_path / "evidence",
        stop_service=True,
        start_service=False,
    )

    with pytest.raises(OSError, match="disk"):
        script.run_backup(args)

    assert commands == [
        ("sudo", "systemctl", "stop", "yt-transcriber-bot"),
        ("sudo", "systemctl", "start", "yt-transcriber-bot"),
    ]


def test_systemd_smoke_fails_fast_after_mutating_command_error(tmp_path: Path, monkeypatch) -> None:
    script = _load_script()
    commands: list[tuple[str, ...]] = []

    def fake_run(command, **_kwargs):
        commands.append(tuple(command))
        return script.CommandResult(tuple(command), 1, "", "permission denied")

    monkeypatch.setattr(script, "_run", fake_run)
    args = SimpleNamespace(
        app_dir=tmp_path,
        service="yt-transcriber-bot",
        output_dir=tmp_path / "evidence",
        journal_lines=10,
    )

    with pytest.raises(RuntimeError, match="Falha ao executar comando mutável"):
        script.run_systemd_smoke(args)

    assert commands == [
        ("sudo", "systemctl", "status", "yt-transcriber-bot", "--no-pager"),
        ("sudo", "systemctl", "stop", "yt-transcriber-bot"),
    ]


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


def test_standard_backup_validator_rejects_credential_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = _load_script()
    app_dir = tmp_path / "app"
    _create_jobs_db(app_dir / "data" / "jobs.db")
    (app_dir / "data" / "transcripts").mkdir(parents=True)
    monkeypatch.setattr(script, "_git_head", lambda _app_dir: "abc123")
    args = SimpleNamespace(
        app_dir=app_dir,
        db_path=Path("data/jobs.db"),
        transcripts_dir=Path("data/transcripts"),
        service="yt-transcriber-bot",
        output_dir=tmp_path / "evidence",
        stop_service=False,
        start_service=False,
    )
    script.run_backup(args)
    backup_dir = next(path for path in (tmp_path / "evidence").iterdir() if path.is_dir())
    (backup_dir / "dotenv").write_text("placeholder", encoding="utf-8")

    with pytest.raises(RuntimeError, match="credencial/cookie"):
        script._validate_standard_backup(backup_dir)
