"""Tests for structured execution audit logging."""

from __future__ import annotations

import json
from pathlib import Path

from yt_transcriber_bot.infrastructure.logging.execution_audit import ExecutionAuditLogger


def test_execution_audit_logger_writes_jsonl_with_utf8(tmp_path: Path) -> None:
    path = tmp_path / "logs" / "execution_audit.jsonl"
    logger = ExecutionAuditLogger(path)

    logger.record(
        "job_started",
        job_id="j1",
        video_id="dQw4w9WgXcQ",
        stage="metadata",
        audit_note="Iniciando transcrição em português",
    )

    row = json.loads(path.read_text(encoding="utf-8").strip())
    assert row["event"] == "job_started"
    assert row["job_id"] == "j1"
    assert row["video_id"] == "dQw4w9WgXcQ"
    assert row["audit_note"] == "Iniciando transcrição em português"
    assert row["timestamp"].endswith("Z")


def test_execution_audit_logger_redacts_secrets_and_transcript_payload(tmp_path: Path) -> None:
    path = tmp_path / "execution_audit.jsonl"
    logger = ExecutionAuditLogger(path)

    logger.record(
        "step_completed",
        telegram_bot_token="secret-token",
        authorization="Bearer abc",
        transcript="fala privada completa",
        text="mensagem do usuário",
        message="mensagem do usuário",
        response="resposta privada",
        nested={"api_key": "abc", "safe": "ok", "cookie": "session=1", "body": "privado"},
    )

    row = json.loads(path.read_text(encoding="utf-8").strip())
    assert row["telegram_bot_token"] == "[REDACTED]"
    assert row["authorization"] == "[REDACTED]"
    assert row["transcript"] == "[OMITTED]"
    assert row["text"] == "[OMITTED]"
    assert row["message"] == "[OMITTED]"
    assert row["response"] == "[OMITTED]"
    assert row["nested"] == {
        "api_key": "[REDACTED]",
        "safe": "ok",
        "cookie": "[REDACTED]",
        "body": "[OMITTED]",
    }


def test_execution_audit_logger_sanitizes_free_form_error_messages(tmp_path: Path) -> None:
    path = tmp_path / "execution_audit.jsonl"
    logger = ExecutionAuditLogger(path)

    logger.record(
        "job_failed",
        error_message=(
            "failed token=secret-token Authorization: Bearer secret-bearer "
            "Cookie: session=abc123 transcript=fala privada text=mensagem do usuário"
        ),
        details=[
            "hf_" + "abcdefghijklmnopqrstuvwxyz",
            "chat_payload={private}",
            "response={'body': 'conteúdo privado'}",
        ],
    )

    row = json.loads(path.read_text(encoding="utf-8").strip())
    rendered = json.dumps(row, ensure_ascii=False)
    assert "secret-token" not in rendered
    assert "secret-bearer" not in rendered
    assert "session=abc123" not in rendered
    assert "fala privada" not in rendered
    assert "mensagem do usuário" not in rendered
    assert ("hf_" + "abcdefghijklmnopqrstuvwxyz") not in rendered
    assert "{private}" not in rendered
    assert "conteúdo privado" not in rendered
    assert "[REDACTED]" in rendered
    assert "[OMITTED]" in rendered


def test_execution_audit_logger_sanitizes_cookie_lists_and_serialized_payloads(
    tmp_path: Path,
) -> None:
    path = tmp_path / "execution_audit.jsonl"
    logger = ExecutionAuditLogger(path)

    logger.record(
        "job_failed",
        error_message=(
            "Cookie: session=abc123; other=def456; cookies: persisted=ghi789; "
            '{"transcript": "fala privada", "text": "mensagem privada", '
            '"chat_payload": {"body": "chat privado"}, "message": "msg privada", '
            '"content": "conteúdo privado", "prompt": "prompt privado", '
            '"response": "resposta privada", "error": {"body": "erro privado"}} '
            "{'transcript': 'outra fala', 'text': 'outro texto', 'message': 'outra msg'}"
        ),
    )

    row = json.loads(path.read_text(encoding="utf-8").strip())
    rendered = json.dumps(row, ensure_ascii=False)
    for forbidden in (
        "abc123",
        "def456",
        "ghi789",
        "fala privada",
        "mensagem privada",
        "chat privado",
        "msg privada",
        "conteúdo privado",
        "prompt privado",
        "resposta privada",
        "erro privado",
        "outra fala",
        "outro texto",
        "outra msg",
    ):
        assert forbidden not in rendered
    assert rendered.count("[REDACTED]") >= 1
    assert rendered.count("[OMITTED]") >= 3
