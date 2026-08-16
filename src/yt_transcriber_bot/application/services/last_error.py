from __future__ import annotations

import traceback
from dataclasses import dataclass
from pathlib import Path

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.application.ports.operational_error import (
    JobLogReader,
    OperationalErrorRecord,
    OperationalErrorStore,
)
from yt_transcriber_bot.application.services.sanitization import sanitize_text, sanitize_value
from yt_transcriber_bot.domain.entities.job import Job, JobStatus


@dataclass(frozen=True)
class LastErrorReport:
    job: Job | None
    message: str
    operational_error: OperationalErrorRecord | None = None


class LastErrorService:
    def __init__(
        self,
        *,
        repository: JobRepository,
        settings: AppSettings,
        error_store: OperationalErrorStore,
        log_reader: JobLogReader,
    ) -> None:
        self._repository = repository
        self._settings = settings
        self._error_store = error_store
        self._log_reader = log_reader

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
        resolved = (error_type or (type(error).__name__ if error else "")).strip()
        record = OperationalErrorRecord(
            user_id=user_id,
            operation=_clean_label(operation, fallback="unknown"),
            message=sanitize_text(message, self._settings),
            context={
                str(key): str(sanitize_value(str(key), value, self._settings))
                for key, value in (context or {}).items()
                if value is not None
            },
            error_type=sanitize_text(resolved, self._settings),
            stage=_clean_label(stage, fallback=""),
            severity=_clean_label(severity, fallback="error"),
            traceback_tail=_format_traceback_tail(error, self._settings) if error else "",
        )
        self._error_store.append(record)
        return record

    def latest_for_user(self, user_id: int) -> LastErrorReport:
        failed = self._latest_failed_job(user_id)
        operational = self._error_store.latest_for_user(
            user_id, limit=self._settings.lasterror_recent_limit
        )
        if failed is None and operational is None:
            return LastErrorReport(
                job=None, message="✅ Nenhum erro recente registrado para este usuário."
            )
        if operational is not None and (
            failed is None or operational.occurred_at >= failed.updated_at
        ):
            return LastErrorReport(
                job=None,
                operational_error=operational,
                message=self._render_operational_error(operational),
            )
        assert failed is not None
        return LastErrorReport(job=failed, message=self._render_job(failed))

    def _latest_failed_job(self, user_id: int) -> Job | None:
        jobs = self._repository.list_recent_for_user(
            user_id, limit=self._settings.lasterror_recent_limit
        )
        failed = [
            job for job in jobs if job.status in {JobStatus.FAILED, JobStatus.DELIVERY_FAILED}
        ]
        return max(failed, key=lambda job: job.updated_at) if failed else None

    def _render_job(self, job: Job) -> str:
        lines = [
            "❌ Último erro registrado",
            "",
            "Tipo: job de transcrição",
            "Operação: transcribe",
            f"Vídeo: {job.video_id.value if job.video_id is not None else 'Telegram (mídia privada)'}",
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
            lines.append("Markdown parcial: disponível")
        if job.audio_path:
            lines.append("Áudio parcial: disponível")
        if job.log_path:
            tail = self._log_reader.tail(
                Path(job.log_path),
                max_lines=self._settings.lasterror_log_tail_lines,
                max_chars=self._settings.lasterror_log_tail_chars,
            )
            lines.extend(["", "Trecho final do log:", sanitize_text(tail, self._settings)])
        hints = _hints_for_text(operation="transcribe", message=job.error_message or "")
        if hints:
            lines.extend(["", "Próximas verificações:", *(f"- {hint}" for hint in hints)])
        lines.extend(["", "Use /healthcheck para validar configuração e dependências atuais."])
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
            lines.extend(f"- {key}: {record.context[key]}" for key in sorted(record.context))
        if record.traceback_tail:
            lines.extend(["", "Traceback final sanitizado:", record.traceback_tail])
        hints = _hints_for_text(
            operation=record.operation,
            message="\n".join([record.message, record.error_type, record.stage]),
        )
        if hints:
            lines.extend(["", "Próximas verificações:", *(f"- {hint}" for hint in hints)])
        lines.extend(["", "Use /healthcheck para validar configuração e dependências atuais."])
        return sanitize_text("\n".join(lines), self._settings)


def _format_traceback_tail(error: BaseException, settings: AppSettings) -> str:
    raw = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    tail = "\n".join(raw.splitlines()[-settings.lasterror_traceback_tail_lines :])
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
        key in text for key in ("lm studio", "/v1/models", "connection refused", "chatcompletion")
    ):
        hints.append(
            "Verifique se o LM Studio Server está ativo e se SUMMARY_BASE_URL está correto."
        )
        hints.append("Rode /healthcheck para confirmar se SUMMARY_MODEL aparece em /v1/models.")
    if any(key in text for key in ("timeout", "timed out", "tempo")):
        hints.append(
            "Revise SUMMARY_MAX_INPUT_TOKENS, SUMMARY_TIMEOUT_S e SUMMARY_TIMEOUT_SPLIT_RETRIES."
        )
    if any(key in text for key in ("snapshot", "expirou", "filenotfound", "arquivo")):
        hints.append(
            "Use /list para confirmar se a transcrição ainda existe; se necessário, reprocesse."
        )
    if any(key in text for key in ("ffmpeg", "ffprobe", "video_subs", "vídeo legendado")):
        hints.append("Verifique ffmpeg/ffprobe no PATH e os limites de vídeo legendado.")
    if any(key in text for key in ("cookie", "private", "unavailable", "youtube")):
        hints.append("Verifique cookies do YouTube e disponibilidade/restrições do vídeo.")
    if any(key in text for key in ("cuda", "outofmemory", "oom", "memória")):
        hints.append("Reduza modelo/compute_type ou rode em CPU; confira VRAM e WHISPER_MODEL.")
    return list(dict.fromkeys(hints))[:5]


__all__ = ["LastErrorReport", "LastErrorService", "OperationalErrorRecord"]
