"""Serviço para registrar e renderizar o último erro operacional conhecido."""

from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.application.services.sanitization import sanitize_text
from yt_transcriber_bot.domain.entities.job import Job, JobStatus


@dataclass(frozen=True)
class OperationalErrorRecord:
    """Erro operacional registrado fora do ciclo principal de transcrição.

    Exemplos: falha de ``/summary`` por LM Studio indisponível, snapshot expirado,
    erro de exportação, falha de vídeo legendado ou exceção defensiva em handler.
    Esses erros não devem necessariamente transformar a transcrição original em
    ``failed``.
    """

    user_id: int
    operation: str
    message: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    context: dict[str, str] = field(default_factory=dict)
    error_type: str = ""
    stage: str = ""
    severity: str = "error"
    traceback_tail: str = ""


@dataclass(frozen=True)
class LastErrorReport:
    """Resultado de consulta do último erro."""

    job: Job | None
    message: str
    operational_error: OperationalErrorRecord | None = None


class LastErrorService:
    """Consulta e registra erros operacionais de forma sanitizada."""

    def __init__(self, *, repository: JobRepository, settings: AppSettings) -> None:
        self._repository = repository
        self._settings = settings

    def record_operation_error(
        self,
        *,
        user_id: int,
        operation: str,
        message: str,
        context: dict[str, object] | None = None,
        error: BaseException | None = None,
        error_type: str = "",
        stage: str = "",
        severity: str = "error",
    ) -> OperationalErrorRecord:
        """Persiste um erro operacional sanitizado para consulta via ``/lasterror``."""

        resolved_error_type = (error_type or (type(error).__name__ if error else "")).strip()
        record = OperationalErrorRecord(
            user_id=user_id,
            operation=_clean_label(operation, fallback="unknown"),
            message=sanitize_text(message, self._settings),
            context={
                str(k): sanitize_text(str(v), self._settings)
                for k, v in (context or {}).items()
                if v is not None
            },
            error_type=sanitize_text(resolved_error_type, self._settings),
            stage=_clean_label(stage, fallback=""),
            severity=_clean_label(severity, fallback="error"),
            traceback_tail=_format_traceback_tail(error, self._settings) if error else "",
        )
        _append_operational_error(self._operational_errors_path(), record)
        return record

    def latest_for_user(self, user_id: int) -> LastErrorReport:
        failed_job = self._latest_failed_job(user_id)
        operational_error = self._latest_operational_error(user_id)

        if failed_job is None and operational_error is None:
            return LastErrorReport(job=None, message="✅ Nenhum erro recente registrado para este usuário.")

        if operational_error is not None and (
            failed_job is None or operational_error.occurred_at >= failed_job.updated_at
        ):
            return LastErrorReport(
                job=None,
                operational_error=operational_error,
                message=self._render_operational_error(operational_error),
            )

        assert failed_job is not None
        return LastErrorReport(job=failed_job, message=self._render_job(failed_job))

    def _latest_failed_job(self, user_id: int) -> Job | None:
        jobs = self._repository.list_recent_for_user(
            user_id, limit=self._settings.lasterror_recent_limit
        )
        failed = [job for job in jobs if job.status == JobStatus.FAILED]
        failed.sort(key=lambda job: job.updated_at, reverse=True)
        return failed[0] if failed else None

    def _latest_operational_error(self, user_id: int) -> OperationalErrorRecord | None:
        records = [
            record
            for record in _load_operational_errors(self._operational_errors_path())
            if record.user_id == user_id
        ]
        records.sort(key=lambda record: record.occurred_at, reverse=True)
        if self._settings.lasterror_recent_limit > 0:
            records = records[: self._settings.lasterror_recent_limit]
        return records[0] if records else None

    def _operational_errors_path(self) -> Path:
        return self._settings.logs_dir() / "operational_errors.jsonl"

    def _render_job(self, job: Job) -> str:
        lines = [
            "❌ Último erro registrado",
            "",
            "Tipo: job de transcrição",
            "Operação: transcribe",
            f"Vídeo: {job.video_id.value}",
            f"Job: {job.job_id}",
            f"Status: {job.status.value}",
            f"Solicitado em: {job.requested_at.strftime('%Y-%m-%d %H:%M:%S %Z')}",
            f"Atualizado em: {job.updated_at.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        ]
        if job.config_signature:
            lines.append(f"Assinatura de configuração: {job.config_signature}")
        if job.error_message:
            lines.extend(["", "Erro:", sanitize_text(job.error_message, self._settings)])
        if job.md_path:
            lines.append(f"Markdown parcial: {job.md_path}")
        if job.audio_path:
            lines.append(f"Áudio parcial: {job.audio_path}")
        if job.log_path:
            lines.extend(["", "Trecho final do log:", _tail_log(Path(job.log_path), self._settings)])
        hints = _hints_for_text(operation="transcribe", message=job.error_message or "")
        if hints:
            lines.extend(["", "Próximas verificações:"])
            lines.extend(f"- {hint}" for hint in hints)
        lines.append("")
        lines.append("Use /healthcheck para validar configuração e dependências atuais.")
        return sanitize_text("\n".join(lines), self._settings)

    def _render_operational_error(self, record: OperationalErrorRecord) -> str:
        lines = [
            "❌ Último erro registrado",
            "",
            "Tipo: operação derivada",
            f"Operação: {record.operation}",
            f"Severidade: {record.severity}",
            f"Ocorrido em: {record.occurred_at.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        ]
        if record.stage:
            lines.append(f"Etapa: {record.stage}")
        if record.error_type:
            lines.append(f"Classe do erro: {record.error_type}")
        lines.extend(["", "Erro:", sanitize_text(record.message, self._settings)])
        if record.context:
            lines.extend(["", "Contexto:"])
            for key in sorted(record.context):
                lines.append(f"- {key}: {record.context[key]}")
        if record.traceback_tail:
            lines.extend(["", "Traceback final sanitizado:", record.traceback_tail])
        hints = _hints_for_text(
            operation=record.operation,
            message="\n".join([record.message, record.error_type, record.stage]),
        )
        if hints:
            lines.extend(["", "Próximas verificações:"])
            lines.extend(f"- {hint}" for hint in hints)
        lines.append("")
        lines.append("Use /healthcheck para validar configuração e dependências atuais.")
        return sanitize_text("\n".join(lines), self._settings)


def _append_operational_error(path: Path, record: OperationalErrorRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "user_id": record.user_id,
        "operation": record.operation,
        "message": record.message,
        "occurred_at": record.occurred_at.isoformat(),
        "context": record.context,
        "error_type": record.error_type,
        "stage": record.stage,
        "severity": record.severity,
        "traceback_tail": record.traceback_tail,
    }
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _load_operational_errors(path: Path) -> list[OperationalErrorRecord]:
    if not path.is_file():
        return []
    records: list[OperationalErrorRecord] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload: dict[str, Any] = json.loads(line)
            records.append(_record_from_payload(payload))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
    return records


def _record_from_payload(payload: dict[str, Any]) -> OperationalErrorRecord:
    occurred_raw = str(payload.get("occurred_at", ""))
    try:
        occurred_at = datetime.fromisoformat(occurred_raw)
    except ValueError:
        occurred_at = datetime.now(UTC)
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=UTC)
    context_raw = payload.get("context", {})
    context = (
        {str(k): str(v) for k, v in context_raw.items()}
        if isinstance(context_raw, dict)
        else {}
    )
    return OperationalErrorRecord(
        user_id=int(payload.get("user_id", 0)),
        operation=str(payload.get("operation", "unknown")),
        message=str(payload.get("message", "")),
        occurred_at=occurred_at,
        context=context,
        error_type=str(payload.get("error_type", "")),
        stage=str(payload.get("stage", "")),
        severity=str(payload.get("severity", "error")),
        traceback_tail=str(payload.get("traceback_tail", "")),
    )


def _tail_log(path: Path, settings: AppSettings) -> str:
    if not path.is_file():
        return f"log não encontrado: {path}"
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return f"não consegui ler {path}: {exc}"
    tail = "\n".join(lines[-settings.lasterror_log_tail_lines :])
    if len(tail) > settings.lasterror_log_tail_chars:
        tail = tail[-settings.lasterror_log_tail_chars :]
        tail = "[...]\n" + tail
    return sanitize_text(tail, settings)


def _format_traceback_tail(error: BaseException, settings: AppSettings) -> str:
    raw = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    lines = raw.splitlines()
    tail = "\n".join(lines[-settings.lasterror_traceback_tail_lines :])
    if len(tail) > settings.lasterror_traceback_tail_chars:
        tail = "[...]\n" + tail[-settings.lasterror_traceback_tail_chars :]
    return sanitize_text(tail, settings)


def _clean_label(value: str, *, fallback: str) -> str:
    cleaned = "_".join((value or "").strip().lower().replace("/", " ").split())
    return cleaned or fallback


def _hints_for_text(*, operation: str, message: str) -> list[str]:
    text = f"{operation}\n{message}".lower()
    hints: list[str] = []
    if any(
        key in text
        for key in ["lm studio", "/v1/models", "connection refused", "urlerror", "chatcompletion"]
    ):
        hints.append(
            "Verifique se o LM Studio Server está ativo, acessível pelo WSL2/host e se "
            "SUMMARY_BASE_URL está correto."
        )
        hints.append("Rode /healthcheck para confirmar se SUMMARY_MODEL aparece em /v1/models.")
    if any(key in text for key in ["timeout", "timed out", "tempo"]):
        hints.append("Revise SUMMARY_MAX_INPUT_TOKENS, SUMMARY_TIMEOUT_S e SUMMARY_TIMEOUT_SPLIT_RETRIES.")
    if any(key in text for key in ["snapshot", "expirou", "filenotfound", "não encontrei", "arquivo"]):
        hints.append(
            "Use /list para confirmar se a transcrição ainda existe; se o snapshot expirou, "
            "reprocesse o vídeo."
        )
    if any(key in text for key in ["ffmpeg", "ffprobe", "vídeo legendado", "video_subs"]):
        hints.append(
            "Verifique ffmpeg/ffprobe no PATH e os limites "
            "MAX_VIDEO_SUBTITLES_DURATION_MIN/MAX_VIDEO_SUBTITLES_SIZE_MB."
        )
    if any(key in text for key in ["members", "cookie", "age", "private", "unavailable", "youtube"]):
        hints.append(
            "Verifique cookies do YouTube, disponibilidade do vídeo e restrições de "
            "idade/membros/geobloqueio."
        )
    if any(key in text for key in ["cuda", "outofmemory", "oom", "memória"]):
        hints.append("Reduza modelo/compute_type ou rode em CPU; confira VRAM e configuração WHISPER_MODEL.")
    if any(key in text for key in ["telegram", "networkerror", "connecterror", "readerror"]):
        hints.append("Verifique conectividade com api.telegram.org e os timeouts de polling/envio do Telegram.")
    out: list[str] = []
    for hint in hints:
        if hint not in out:
            out.append(hint)
    return out[:5]
