"""TelegramBotAdapter — adaptador principal sobre python-telegram-bot.

Responsabilidades:
- Receber mensagens, autorizar (silenciosamente) o user_id permitido.
- Detectar URLs do YouTube e enfileirar o job via SequentialJobQueue.
- Despachar comandos de operação, fila, histórico, exportação e manutenção.
- Editar uma única mensagem para reportar progresso (ProgressReporter).
- Enviar áudio comprimido + arquivo .md final, com retry exponencial.

A integração com python-telegram-bot é deliberadamente fina — todo o
trabalho real é executado por dependências testáveis injetadas. Isso
permite testar o adapter sem a Bot API real (mockando o ``BotClient``).
"""

from __future__ import annotations

import asyncio
import logging
import re
import threading
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.application.services.healthcheck import HealthCheckService
from yt_transcriber_bot.application.services.last_error import LastErrorService
from yt_transcriber_bot.application.services.rename_speakers import (
    RenameResult,
    RenameSpeakersService,
)
from yt_transcriber_bot.application.services.retention_policy import (
    RetentionPolicy,
)
from yt_transcriber_bot.application.use_cases.transcribe_video import (
    TranscribeVideoUseCase,
)
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.video_id import (
    InvalidYouTubeUrlError,
    VideoId,
)
from yt_transcriber_bot.infrastructure.exporting.transcript_exporter import (
    SUPPORTED_EXPORT_FORMATS,
    TranscriptExportService,
)
from yt_transcriber_bot.infrastructure.exporting.video_subtitles_exporter import (
    VideoSoftSubtitleExportService,
    VideoSubtitleExportError,
    VideoSubtitleTooLargeError,
    VideoSubtitleTooLongError,
)
from yt_transcriber_bot.infrastructure.logging.execution_audit import ExecutionAuditLogger
from yt_transcriber_bot.infrastructure.summarization.openai_compatible_client import (
    ChatCompletionError,
)
from yt_transcriber_bot.infrastructure.summarization.transcript_summarizer import (
    SummaryError,
    SummaryProgress,
    TranscriptSummaryService,
)
from yt_transcriber_bot.infrastructure.telegram.job_queue import (
    QueuedItem,
    SequentialJobQueue,
)
from yt_transcriber_bot.infrastructure.telegram.progress_reporter import (
    ProgressReporter,
)
from yt_transcriber_bot.infrastructure.telegram.retry import (
    TelegramSendError,
    send_with_retry,
)
from yt_transcriber_bot.infrastructure.telegram.url_extractor import (
    extract_first_youtube_url,
)

logger = logging.getLogger(__name__)

HELP_TEXT = """🤖 yt-transcriber-bot — comandos disponíveis

Entrada e idioma
• <link do YouTube> → enfileira e transcreve o vídeo em Markdown.
• /transcribe <link> [--lang pt|en] → enfileira explicitamente um link para transcrição.
• /pt <link> → transcreve informando português como idioma do vídeo.
• /en <link> → transcreve informando inglês como idioma do vídeo.
• /redo <link> [--lang pt|en] → reprocessa um vídeo, sem reaproveitar o resultado anterior.

Estado, fila e cancelamento
• /status → mostra o job atual e o estado operacional do bot.
• /healthcheck → valida configuração, dependências, diretórios, SQLite e LM Studio.
• /lasterror → mostra o último erro registrado de forma sanitizada.
• /queue → mostra a fila completa de processamento.
• /fila → alias em português de /queue.
• /clearqueue → remove apenas os jobs pendentes da fila.
• /cancelqueue → alias de /clearqueue.
• /limparfila → alias em português de /clearqueue.
• /cancel → solicita cancelamento do job em andamento.
• /cancelall → cancela o job atual e remove todos os pendentes.
• /cancelartudo → alias em português de /cancelall.

Histórico e revisão
• /list → lista as últimas transcrições concluídas, numeradas por título e horário.
• /last [n] → reenvia a n-ésima transcrição concluída; exemplo: /last 2.
• /rename [n] → abre botões para renomear ou mesclar falantes; exemplo: /rename 2.

Resumos e artefatos derivados
• /summary [n] → gera um resumo estruturado em Markdown usando a LLM configurada; exemplo: /summary 2.

Exportações
• /export json [n] → exporta a transcrição estruturada em JSON.
• /export srt [n] → exporta legenda SubRip (.srt).
• /export vtt [n] → exporta legenda WebVTT (.vtt).
• /json [n] → atalho para /export json [n].
• /srt [n] → atalho para /export srt [n].
• /vtt [n] → atalho para /export vtt [n].
• /video_subs [n] → envia MP4 com legenda selecionável; limite padrão: 30 min e 200 MB.
• /videosubs [n] → alias de /video_subs [n].

Manutenção e ajuda
• /start → mostra a mensagem inicial do bot.
• /help → mostra esta lista de comandos.
• /clearcache → apaga modelos baixados no diretório de cache configurado.
"""


# ----------------------------------------------------------------------
# Protocolo do client (permite mockar a Bot API)
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class InlineButton:
    """Botão inline independente do python-telegram-bot.

    O adapter usa esta estrutura simples para permanecer testável sem importar
    classes concretas da Bot API. O client real converte para
    ``InlineKeyboardMarkup``.
    """

    text: str
    callback_data: str


InlineKeyboard = tuple[tuple[InlineButton, ...], ...]


class BotClient(Protocol):
    """Subset da Bot API que usamos. Permite mockagem nos testes."""

    async def send_message(
        self, chat_id: int, text: str, reply_markup: InlineKeyboard | None = None
    ) -> int:
        """Envia mensagem e retorna o ``message_id``."""
        ...

    async def edit_message(self, chat_id: int, message_id: int, text: str) -> None: ...

    async def send_document(
        self, chat_id: int, file_path: Path, caption: str | None = None
    ) -> None: ...

    async def send_audio(
        self, chat_id: int, file_path: Path, caption: str | None = None
    ) -> None: ...

    async def send_video(
        self, chat_id: int, file_path: Path, caption: str | None = None
    ) -> None: ...


# ----------------------------------------------------------------------
# Payload da fila
# ----------------------------------------------------------------------


@dataclass
class JobPayload:
    """Tudo que o worker precisa para processar um job."""

    chat_id: int
    user_id: int
    url: str
    video_id: VideoId
    progress_message_id: int
    requested_language: str | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)


@dataclass
class RenameSession:
    """Estado do diálogo de /rename para permitir múltiplos falantes."""

    user_id: int
    slug: str
    job_id: str
    md_path: str | None
    aliases: dict[str, str] = field(default_factory=dict)
    selected_label: str | None = None


# ----------------------------------------------------------------------
# Adapter principal
# ----------------------------------------------------------------------


class TelegramBotAdapter:
    """Adaptador entre handlers de mensagem e o use case principal."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        client: BotClient,
        use_case: TranscribeVideoUseCase,
        repository: JobRepository | None = None,
        rename_service: RenameSpeakersService | None = None,
        export_service: TranscriptExportService | None = None,
        summary_service: TranscriptSummaryService | None = None,
        video_subtitle_export_service: VideoSoftSubtitleExportService | None = None,
        healthcheck_service: HealthCheckService | None = None,
        lasterror_service: LastErrorService | None = None,
        retention_policy: RetentionPolicy | None = None,
        models_dir: Path | None = None,
        audit_logger: ExecutionAuditLogger | None = None,
    ) -> None:
        self._settings = settings
        self._client = client
        self._use_case = use_case
        self._repository = repository
        self._rename_service = rename_service
        self._export_service = export_service
        self._summary_service = summary_service
        self._video_subtitle_export_service = video_subtitle_export_service
        self._healthcheck_service = healthcheck_service
        self._lasterror_service = lasterror_service
        self._retention_policy = retention_policy
        self._models_dir = models_dir
        self._audit_logger = audit_logger
        self._rename_session: RenameSession | None = None
        self._queue: SequentialJobQueue[JobPayload] = SequentialJobQueue(self._process_job)

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    async def start(self) -> None:
        await self._queue.start()

    async def stop(self) -> None:
        await self._queue.stop()

    # ------------------------------------------------------------------
    # Autorização (Dúvida 3 + 30: ignorar silenciosamente)
    # ------------------------------------------------------------------

    def _is_authorized(self, user_id: int) -> bool:
        return user_id == self._settings.telegram_allowed_user_id

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    async def handle_message(self, *, chat_id: int, user_id: int, text: str) -> None:
        if not self._is_authorized(user_id):
            return  # silêncio total (Dúvida 3)
        raw_text = text or ""
        if await self._handle_text_command(chat_id=chat_id, user_id=user_id, text=raw_text):
            return
        # Diálogo de rename pendente?
        if self._rename_session is not None and self._rename_session.user_id == user_id:
            await self._handle_rename_input(chat_id, user_id, raw_text)
            return
        url = extract_first_youtube_url(raw_text)
        if url is None:
            await self._send_text(chat_id, "Envie um link do YouTube para transcrever.")
            return
        requested_language = self._extract_language_hint(raw_text)
        if (
            requested_language is not None
            and requested_language not in self._settings.allowed_languages
        ):
            await self._send_text(
                chat_id,
                f"Idioma '{requested_language}' não está permitido. "
                f"Idiomas aceitos: {', '.join(self._settings.allowed_languages)}.",
            )
            return
        await self._enqueue_url(
            chat_id=chat_id,
            user_id=user_id,
            url=url,
            redo=False,
            requested_language=requested_language,
        )

    async def _handle_text_command(self, *, chat_id: int, user_id: int, text: str) -> bool:
        """Fallback defensivo para comandos que cheguem como texto comum.

        O entrypoint real registra ``CommandHandler`` para todos os comandos,
        mas este fallback evita comandos silenciosos se algum handler não for
        instalado ou se o comando vier com sufixo ``@NomeDoBot``.
        """
        stripped = (text or "").strip()
        if not stripped.startswith("/"):
            return False
        token = stripped.split(maxsplit=1)[0]
        command = token[1:].split("@", 1)[0].lower()
        if command == "start":
            await self.handle_command_start(chat_id=chat_id, user_id=user_id)
        elif command == "help":
            await self.handle_command_help(chat_id=chat_id, user_id=user_id)
        elif command == "status":
            await self.handle_command_status(chat_id=chat_id, user_id=user_id)
        elif command == "healthcheck":
            await self.handle_command_healthcheck(chat_id=chat_id, user_id=user_id)
        elif command == "lasterror":
            await self.handle_command_lasterror(chat_id=chat_id, user_id=user_id)
        elif command in {"queue", "fila"}:
            await self.handle_command_queue(chat_id=chat_id, user_id=user_id)
        elif command in {"clearqueue", "cancelqueue", "limparfila"}:
            await self.handle_command_clearqueue(chat_id=chat_id, user_id=user_id)
        elif command in {"cancelall", "cancelartudo"}:
            await self.handle_command_cancelall(chat_id=chat_id, user_id=user_id)
        elif command == "cancel":
            await self.handle_command_cancel(chat_id=chat_id, user_id=user_id)
        elif command == "redo":
            await self.handle_command_redo(chat_id=chat_id, user_id=user_id, text=stripped)
        elif command == "pt":
            await self.handle_command_language_link(
                chat_id=chat_id, user_id=user_id, text=stripped, language="pt"
            )
        elif command == "en":
            await self.handle_command_language_link(
                chat_id=chat_id, user_id=user_id, text=stripped, language="en"
            )
        elif command == "transcribe":
            rest = stripped.split(maxsplit=1)[1] if len(stripped.split(maxsplit=1)) > 1 else ""
            await self.handle_message(chat_id=chat_id, user_id=user_id, text=rest)
        elif command == "list":
            await self.handle_command_list(chat_id=chat_id, user_id=user_id)
        elif command == "last":
            await self.handle_command_last(chat_id=chat_id, user_id=user_id, text=stripped)
        elif command == "rename":
            await self.handle_command_rename(chat_id=chat_id, user_id=user_id, text=stripped)
        elif command == "summary":
            await self.handle_command_summary(chat_id=chat_id, user_id=user_id, text=stripped)
        elif command == "export":
            await self.handle_command_export(chat_id=chat_id, user_id=user_id, text=stripped)
        elif command in set(SUPPORTED_EXPORT_FORMATS):
            await self.handle_command_export_shortcut(
                chat_id=chat_id, user_id=user_id, format=command, text=stripped
            )
        elif command in {"video_subs", "videosubs"}:
            await self.handle_command_video_subs(chat_id=chat_id, user_id=user_id, text=stripped)
        elif command == "clearcache":
            await self.handle_command_clearcache(chat_id=chat_id, user_id=user_id)
        else:
            await self._send_text(
                chat_id, "Comando não reconhecido. Use /help para ver os comandos disponíveis."
            )
        return True

    async def _enqueue_url(
        self,
        *,
        chat_id: int,
        user_id: int,
        url: str,
        redo: bool,
        requested_language: str | None = None,
    ) -> None:
        """Valida URL, cria payload e enfileira um job novo.

        ``redo=True`` não reaproveita histórico: sempre cria nova entrada na fila.
        """
        try:
            video_id = VideoId.from_url(url)
        except (InvalidYouTubeUrlError, ValueError) as exc:
            await self._send_text(chat_id, f"Link inválido: {exc}")
            return

        if self._is_already_queued(video_id, requested_language):
            await self._send_text(
                chat_id,
                "Esse vídeo já está em processamento ou na fila "
                f"para o idioma {requested_language or 'automático'}.",
            )
            return
        current, pending = self._queue.snapshot()
        total_in_queue = (1 if current is not None else 0) + len(pending)
        if total_in_queue >= self._settings.telegram_max_queue_size:
            await self._send_text(
                chat_id,
                "Fila cheia. Aguarde um job terminar ou use /queue, /clearqueue ou /cancelall.",
            )
            return

        prefix = "🔁 Reprocessando" if redo else "📥 Recebido"
        lang_line = (
            f"\n🌐 Idioma informado: {requested_language}"
            if requested_language
            else "\n🌐 Idioma: automático"
        )
        message_id = await self._send_text(chat_id, f"{prefix}: {url}{lang_line}\nEnfileirando…")
        payload = JobPayload(
            chat_id=chat_id,
            user_id=user_id,
            url=url,
            video_id=video_id,
            progress_message_id=message_id,
            requested_language=requested_language,
        )
        item = await self._queue.enqueue(payload, item_id=str(uuid.uuid4()))
        self._audit(
            "job_enqueued",
            item_id=item.item_id,
            user_id=user_id,
            video_id=video_id.value,
            requested_language=requested_language or "auto",
            queue_position=item.enqueued_position,
        )
        if item.enqueued_position > 1:
            await self._send_text(chat_id, f"⏳ Posição na fila: {item.enqueued_position}.")

    def _audit(self, event: str, **fields: object) -> None:
        if self._audit_logger is None:
            return
        try:
            self._audit_logger.record(event, **fields)
        except Exception as exc:  # pragma: no cover - caminho defensivo
            logger.warning("Falha ao registrar auditoria %s: %s", event, exc)

    def _is_already_queued(self, video_id: VideoId, requested_language: str | None) -> bool:
        current, pending = self._queue.snapshot()
        for item in ([current] if current is not None else []) + list(pending):
            payload = item.payload
            if payload.video_id == video_id and payload.requested_language == requested_language:
                return True
        return False

    async def handle_command_start(self, *, chat_id: int, user_id: int) -> None:
        if not self._is_authorized(user_id):
            return
        await self._send_text(
            chat_id,
            "Olá! Envie um link do YouTube para que eu transcreva o áudio em Markdown.\n"
            "Comandos: /help para ver os disponíveis.",
        )

    async def handle_command_help(self, *, chat_id: int, user_id: int) -> None:
        if not self._is_authorized(user_id):
            return
        await self._send_text(chat_id, HELP_TEXT)

    async def handle_command_status(self, *, chat_id: int, user_id: int) -> None:
        if not self._is_authorized(user_id):
            return
        current, pending = self._queue.snapshot()
        if current is None:
            if pending:
                await self._send_text(
                    chat_id,
                    "📡 Status do bot\n"
                    f"✅ Nenhum job em execução. Pendentes: {len(pending)}. Use /queue para ver a fila.",
                )
            else:
                await self._send_text(
                    chat_id,
                    "📡 Status do bot\n✅ Bot ocioso. Nenhum job em execução e nenhum item pendente.",
                )
            return
        await self._send_text(
            chat_id,
            "📡 Status do bot\n\n"
            "▶️ Em execução:\n"
            f"🔗 {current.payload.url}\n"
            f"🌐{_payload_language_suffix(current.payload).replace(' — idioma:', ' Idioma:')}\n"
            f"⏳ Fila pendente: {len(pending)} item(ns).\n\n"
            "Use /queue para ver a fila completa.",
        )

    async def handle_command_healthcheck(self, *, chat_id: int, user_id: int) -> None:
        if not self._is_authorized(user_id):
            return
        if self._healthcheck_service is None:
            await self._send_text(chat_id, "Healthcheck indisponível neste bot.")
            return
        try:
            report = await asyncio.to_thread(self._healthcheck_service.run)
        except Exception as exc:  # pragma: no cover - caminho defensivo
            logger.exception("Healthcheck falhou: %s", exc)
            await self._send_text(chat_id, f"❌ Healthcheck falhou inesperadamente: {exc}")
            return
        await self._send_text(chat_id, report.render(self._settings))

    async def handle_command_lasterror(self, *, chat_id: int, user_id: int) -> None:
        if not self._is_authorized(user_id):
            return
        if self._lasterror_service is None:
            await self._send_text(chat_id, "Consulta de último erro indisponível neste bot.")
            return
        try:
            report = await asyncio.to_thread(self._lasterror_service.latest_for_user, user_id)
        except Exception as exc:  # pragma: no cover - caminho defensivo
            logger.exception("/lasterror falhou: %s", exc)
            await self._send_text(chat_id, f"❌ Falha ao consultar último erro: {exc}")
            return
        await self._send_text(chat_id, report.message)

    async def _record_operational_error(
        self,
        *,
        user_id: int,
        operation: str,
        message: str,
        context: dict[str, object] | None = None,
        error: BaseException | None = None,
        stage: str = "",
        severity: str = "error",
    ) -> None:
        """Registra falhas de comandos derivados para consulta via /lasterror."""
        if self._lasterror_service is None:
            return
        try:
            await asyncio.to_thread(
                self._lasterror_service.record_operation_error,
                user_id=user_id,
                operation=operation,
                message=message,
                context=context,
                error=error,
                stage=stage,
                severity=severity,
            )
        except Exception as exc:  # pragma: no cover - caminho defensivo
            logger.warning("Não consegui registrar erro operacional %s: %s", operation, exc)

    async def handle_command_queue(self, *, chat_id: int, user_id: int) -> None:
        if not self._is_authorized(user_id):
            return
        current, pending = self._queue.snapshot()
        total = (1 if current is not None else 0) + len(pending)
        lines: list[str] = [
            f"📋 Fila de processamento ({total}/{self._settings.telegram_max_queue_size})"
        ]
        if current is None and not pending:
            lines.append("\n✅ Fila vazia. Envie um link do YouTube para começar.")
        if current is not None:
            lines.extend(
                [
                    "\n▶️ Em execução:",
                    f"1. {current.payload.url}{_payload_language_suffix(current.payload)}",
                ]
            )
        if pending:
            lines.append("\n⏳ Aguardando:")
            start = 2 if current is not None else 1
            for idx, item in enumerate(pending, start=start):
                lines.append(f"{idx}. {item.payload.url}{_payload_language_suffix(item.payload)}")
        lines.append("\nComandos úteis: /status, /clearqueue, /cancelqueue, /cancelall.")
        await self._send_text(chat_id, "\n".join(lines))

    async def handle_command_clearqueue(self, *, chat_id: int, user_id: int) -> None:
        if not self._is_authorized(user_id):
            return
        removed = await self._queue.clear_pending()
        if removed == 0:
            await self._send_text(chat_id, "Não havia jobs pendentes para remover da fila.")
        else:
            await self._send_text(
                chat_id, f"🧹 Fila limpa. {removed} job(s) pendente(s) removido(s)."
            )

    async def handle_command_cancelall(self, *, chat_id: int, user_id: int) -> None:
        if not self._is_authorized(user_id):
            return
        current_cancelled, pending_cancelled = await self._queue.cancel_all()
        if not current_cancelled and pending_cancelled == 0:
            await self._send_text(chat_id, "Nada para cancelar.")
            return
        parts: list[str] = []
        if current_cancelled:
            parts.append("job atual sinalizado para cancelamento")
        if pending_cancelled:
            parts.append(f"{pending_cancelled} pendente(s) removido(s)")
        await self._send_text(
            chat_id, "🛑 Cancelamento geral solicitado: " + "; ".join(parts) + "."
        )

    async def handle_command_cancel(self, *, chat_id: int, user_id: int) -> None:
        if not self._is_authorized(user_id):
            return
        # Cancela diálogo de rename, se ativo
        if self._rename_session is not None and self._rename_session.user_id == user_id:
            self._clear_pending_rename()
            await self._send_text(chat_id, "Renomeação cancelada.")
            return
        current, _ = self._queue.snapshot()
        if current is None:
            await self._send_text(chat_id, "Nada para cancelar.")
            return
        # Sinaliza ao runner do use case + ao loop da queue.
        current.payload.cancel_event.set()
        cancelled = await self._queue.cancel_current()
        if cancelled:
            await self._send_text(
                chat_id,
                "🛑 Cancelamento solicitado. Avisarei quando o job for encerrado com sucesso.",
            )
        else:
            await self._send_text(chat_id, "Nada para cancelar.")

    async def handle_command_redo(
        self,
        *,
        chat_id: int,
        user_id: int,
        text: str = "",
    ) -> None:
        """Reprocessa explicitamente um link enviado com ``/redo <link>``."""
        if not self._is_authorized(user_id):
            return
        url = extract_first_youtube_url(text or "")
        if url is None:
            await self._send_text(chat_id, "Uso: /redo <link do YouTube>")
            return
        requested_language = self._extract_language_hint(text or "")
        if (
            requested_language is not None
            and requested_language not in self._settings.allowed_languages
        ):
            await self._send_text(
                chat_id,
                f"Idioma '{requested_language}' não está permitido. "
                f"Idiomas aceitos: {', '.join(self._settings.allowed_languages)}.",
            )
            return
        await self._enqueue_url(
            chat_id=chat_id,
            user_id=user_id,
            url=url,
            redo=True,
            requested_language=requested_language,
        )

    async def handle_command_language_link(
        self,
        *,
        chat_id: int,
        user_id: int,
        text: str = "",
        language: str,
    ) -> None:
        """Processa atalhos como ``/pt <link>`` e ``/en <link>``."""
        if not self._is_authorized(user_id):
            return
        requested_language = language.strip().lower()
        if requested_language not in self._settings.allowed_languages:
            await self._send_text(
                chat_id,
                f"Idioma '{requested_language}' não está permitido. "
                f"Idiomas aceitos: {', '.join(self._settings.allowed_languages)}.",
            )
            return
        url = extract_first_youtube_url(text or "")
        if url is None:
            await self._send_text(chat_id, f"Uso: /{requested_language} <link do YouTube>")
            return
        await self._enqueue_url(
            chat_id=chat_id,
            user_id=user_id,
            url=url,
            redo=False,
            requested_language=requested_language,
        )

    async def handle_command_list(self, *, chat_id: int, user_id: int) -> None:
        if not self._is_authorized(user_id):
            return
        if self._repository is None:
            await self._send_text(chat_id, "Histórico indisponível neste bot.")
            return
        jobs = self._completed_jobs_for_user(user_id, limit=10)
        if not jobs:
            await self._send_text(chat_id, "Nenhuma transcrição concluída registrada ainda.")
            return
        lines: list[str] = [
            "Últimas transcrições concluídas:",
            "Use /last n para reenviar ou /rename n para renomear falantes.",
        ]
        for idx, job in enumerate(jobs, start=1):
            lines.append(f"{idx}. {self._format_history_job(job)}")
        await self._send_text(chat_id, "\n".join(lines))

    async def handle_command_last(self, *, chat_id: int, user_id: int, text: str = "") -> None:
        if not self._is_authorized(user_id):
            return
        if self._repository is None:
            await self._send_text(chat_id, "Histórico indisponível.")
            return
        index = _parse_history_index(text)
        selected = await self._select_completed_job(chat_id=chat_id, user_id=user_id, index=index)
        if selected is None:
            return
        if selected.md_path is None:
            await self._send_text(chat_id, "O arquivo desse job não está mais disponível.")
            return
        path = Path(selected.md_path)
        if not path.is_file():
            await self._send_text(chat_id, "O Markdown desse job foi removido ou movido.")
            return
        await self._send_document_with_retry(chat_id, path)

    async def handle_command_rename(self, *, chat_id: int, user_id: int, text: str = "") -> None:
        if not self._is_authorized(user_id):
            return
        if self._repository is None or self._rename_service is None:
            await self._send_text(chat_id, "Renomeação indisponível neste bot.")
            return
        index = _parse_history_index(text)
        selected = await self._select_completed_job(chat_id=chat_id, user_id=user_id, index=index)
        if selected is None:
            return
        slug = self._slug_from_md_path(selected.md_path)
        if slug is None:
            await self._send_text(chat_id, "Não consegui localizar o snapshot dessa transcrição.")
            return
        try:
            speakers = self._rename_service.list_speakers(slug)
        except FileNotFoundError:
            await self._send_text(
                chat_id, "Snapshot dessa transcrição expirou. Reprocesse o vídeo."
            )
            return
        if not speakers:
            await self._send_text(chat_id, "Nenhum falante para renomear.")
            return
        self._rename_session = RenameSession(
            user_id=user_id,
            slug=slug,
            job_id=selected.job_id,
            md_path=selected.md_path,
            aliases=dict(selected.speaker_renames),
        )
        keyboard = _rename_keyboard(speakers)
        await self._send_text(
            chat_id,
            f"✏️ Renomear falantes da transcrição #{index}.\n"
            f"Alvo: {self._format_history_job(selected)}\n"
            f"Falantes detectados: {', '.join(speakers)}\n\n"
            "Toque em um falante para renomear com botões, ou envie diretamente:\n"
            "SPEAKER_00=João, SPEAKER_01=Maria\n\n"
            "Para mesclar falantes, use o mesmo nome em dois labels.",
            reply_markup=keyboard,
        )

    async def handle_callback_query(self, *, chat_id: int, user_id: int, data: str) -> None:
        """Trata botões inline de renomeação/mesclagem."""
        if not self._is_authorized(user_id):
            return
        if not data.startswith("rename:"):
            await self._send_text(chat_id, "Ação não reconhecida.")
            return
        session = self._rename_session
        if session is None or session.user_id != user_id:
            await self._send_text(chat_id, "Nenhuma renomeação ativa. Use /rename ou /rename n.")
            return
        action = data.split(":", 2)
        if len(action) < 2:
            await self._send_text(chat_id, "Ação de renomeação inválida.")
            return
        kind = action[1]
        if kind == "done":
            self._clear_pending_rename()
            await self._send_text(chat_id, "✅ Renomeação concluída.")
            return
        if kind == "merge":
            session.selected_label = None
            await self._send_text(
                chat_id,
                "🔗 Para mesclar falantes, envie o mesmo nome para dois ou mais labels.\n"
                "Exemplo: SPEAKER_00=Maria, SPEAKER_02=Maria",
            )
            return
        if kind == "speaker" and len(action) == 3:
            label = action[2]
            session.selected_label = label
            await self._send_text(chat_id, f"Qual nome deseja usar para {label}?")
            return
        await self._send_text(chat_id, "Ação de renomeação inválida.")

    def _completed_jobs_for_user(self, user_id: int, *, limit: int) -> list[Job]:
        if self._repository is None:
            return []
        jobs = self._repository.list_recent_for_user(user_id, limit=max(limit * 3, limit))
        completed = [
            job
            for job in jobs
            if job.requested_by_user_id == user_id and job.status == JobStatus.COMPLETED
        ]
        completed.sort(key=lambda job: job.updated_at, reverse=True)
        return completed[:limit]

    async def _select_completed_job(self, *, chat_id: int, user_id: int, index: int) -> Job | None:
        if index <= 0:
            await self._send_text(chat_id, "Use um número positivo. Exemplo: /last 2 ou /rename 2.")
            return None
        jobs = self._completed_jobs_for_user(user_id, limit=max(index, 10))
        if not jobs:
            await self._send_text(chat_id, "Sem transcrições concluídas ainda.")
            return None
        if index > len(jobs):
            await self._send_text(
                chat_id,
                f"Não encontrei a transcrição #{index}. Use /list para ver as opções disponíveis.",
            )
            return None
        return jobs[index - 1]

    async def handle_command_summary(self, *, chat_id: int, user_id: int, text: str = "") -> None:
        """Gera resumo estruturado em Markdown para uma transcrição concluída."""
        if not self._is_authorized(user_id):
            return
        if self._repository is None or self._summary_service is None:
            await self._send_text(
                chat_id,
                "Sumarização indisponível neste bot. Verifique SUMMARY_BACKEND e a configuração do LM Studio.",
            )
            return
        index = _parse_history_index(text)
        selected = await self._select_completed_job(chat_id=chat_id, user_id=user_id, index=index)
        if selected is None:
            return
        slug = self._slug_from_md_path(selected.md_path)
        if slug is None:
            await self._send_text(chat_id, "Não consegui localizar o snapshot dessa transcrição.")
            return
        output_base = (
            Path(selected.md_path) if selected.md_path else self._settings.summaries_dir() / slug
        )
        progress_message_id = await self._send_text(
            chat_id,
            f"🧠 Gerando resumo da transcrição #{index} com {self._settings.summary_model}. "
            "Preparando transcrição para a LLM…",
        )
        loop = asyncio.get_running_loop()
        progress = (
            ProgressReporter(
                _make_editor(self._client, chat_id, progress_message_id),
                min_interval_s=self._settings.telegram_message_edit_min_interval_s,
            )
            if progress_message_id
            else None
        )

        def summary_progress_cb(event: SummaryProgress) -> None:
            if progress is None:
                return
            asyncio.run_coroutine_threadsafe(
                progress.stage(_humanize_summary_progress(event)), loop
            )

        try:
            result = await asyncio.to_thread(
                self._summary_service.summarize,
                slug=slug,
                output_base_path=output_base,
                speaker_aliases=selected.speaker_renames,
                on_progress=summary_progress_cb,
            )
        except FileNotFoundError as exc:
            await self._record_operational_error(
                user_id=user_id,
                operation="summary",
                message="Snapshot dessa transcrição expirou. Reprocesse o vídeo.",
                context=_artifact_error_context(
                    selected, index=index, error=exc, artifact="summary"
                ),
                error=exc,
                stage="snapshot",
            )
            await self._send_text(
                chat_id, "Snapshot dessa transcrição expirou. Reprocesse o vídeo."
            )
            return
        except ChatCompletionError as exc:
            await self._record_operational_error(
                user_id=user_id,
                operation="summary",
                message=f"Falha ao chamar a LLM de resumo: {exc}",
                context=_artifact_error_context(
                    selected, index=index, error=exc, artifact="summary"
                ),
                error=exc,
                stage="llm",
            )
            await self._send_text(chat_id, f"Falha ao chamar a LLM de resumo: {exc}")
            return
        except SummaryError as exc:
            await self._record_operational_error(
                user_id=user_id,
                operation="summary",
                message=f"Falha ao gerar resumo: {exc}",
                context=_artifact_error_context(
                    selected, index=index, error=exc, artifact="summary"
                ),
                error=exc,
                stage="summary",
            )
            await self._send_text(chat_id, f"Falha ao gerar resumo: {exc}")
            return
        if progress is not None:
            await progress.finish(
                f"✅ Resumo gerado para a transcrição #{index} "
                f"({result.chunks} bloco(s), modelo {result.model}). Enviando arquivo…"
            )
        else:
            await self._send_text(
                chat_id,
                f"✅ Resumo gerado para a transcrição #{index} "
                f"({result.chunks} bloco(s), modelo {result.model}). Enviando arquivo…",
            )
        await self._send_document_with_retry(chat_id, result.path)

    async def handle_command_export_shortcut(
        self, *, chat_id: int, user_id: int, format: str, text: str = ""
    ) -> None:
        """Atalho para /json [n], /srt [n] e /vtt [n]."""
        parts = (text or "").strip().split(maxsplit=1)
        rest = parts[1] if len(parts) > 1 else ""
        await self.handle_command_export(
            chat_id=chat_id,
            user_id=user_id,
            text=(f"/export {format} {rest}" if rest else f"/export {format}"),
        )

    async def handle_command_export(self, *, chat_id: int, user_id: int, text: str = "") -> None:
        """Exporta JSON/SRT/VTT de uma transcrição concluída sem reprocessar."""
        if not self._is_authorized(user_id):
            return
        if self._repository is None or self._export_service is None:
            await self._send_text(chat_id, "Exportação indisponível neste bot.")
            return
        parsed = _parse_export_command(text)
        if parsed is None:
            await self._send_text(
                chat_id,
                "Uso: /export json|srt|vtt [n]. Exemplo: /export srt 2. "
                "Use /list para ver as transcrições disponíveis.",
            )
            return
        fmt, index = parsed
        selected = await self._select_completed_job(chat_id=chat_id, user_id=user_id, index=index)
        if selected is None:
            return
        slug = self._slug_from_md_path(selected.md_path)
        if slug is None:
            await self._send_text(chat_id, "Não consegui localizar o snapshot dessa transcrição.")
            return
        output_base = (
            Path(selected.md_path) if selected.md_path else self._settings.transcripts_dir() / slug
        )
        try:
            result = self._export_service.export(
                slug=slug,
                output_base_path=output_base,
                format=fmt,
                speaker_aliases=selected.speaker_renames,
            )
        except FileNotFoundError as exc:
            await self._record_operational_error(
                user_id=user_id,
                operation="export",
                message="Snapshot dessa transcrição expirou. Reprocesse o vídeo.",
                context=_artifact_error_context(selected, index=index, error=exc, artifact=fmt),
                error=exc,
                stage="snapshot",
            )
            await self._send_text(
                chat_id, "Snapshot dessa transcrição expirou. Reprocesse o vídeo."
            )
            return
        except ValueError as exc:
            await self._record_operational_error(
                user_id=user_id,
                operation="export",
                message=str(exc),
                context=_artifact_error_context(selected, index=index, error=exc, artifact=fmt),
                error=exc,
                stage="export",
            )
            await self._send_text(chat_id, str(exc))
            return
        await self._send_text(
            chat_id,
            f"📦 Exportação {result.format.upper()} gerada para a transcrição #{index}. Enviando arquivo…",
        )
        await self._send_document_with_retry(chat_id, result.path)

    async def handle_command_video_subs(
        self, *, chat_id: int, user_id: int, text: str = ""
    ) -> None:
        """Gera e envia MP4 com legenda selecionável para uma transcrição concluída."""
        if not self._is_authorized(user_id):
            return
        if self._repository is None or self._video_subtitle_export_service is None:
            await self._send_text(chat_id, "Exportação de vídeo legendado indisponível neste bot.")
            return
        index = _parse_history_index(text)
        selected = await self._select_completed_job(chat_id=chat_id, user_id=user_id, index=index)
        if selected is None:
            return
        slug = self._slug_from_md_path(selected.md_path)
        if slug is None:
            await self._send_text(chat_id, "Não consegui localizar o snapshot dessa transcrição.")
            return
        await self._send_text(
            chat_id,
            "🎬 Gerando MP4 com legenda selecionável. "
            f"Limites: {self._settings.max_video_subtitles_duration_min} min e "
            f"{self._settings.max_video_subtitles_size_mb} MB.",
        )
        try:
            result = await asyncio.to_thread(
                self._video_subtitle_export_service.export,
                video_id=selected.video_id,
                slug=slug,
                speaker_aliases=selected.speaker_renames,
            )
        except FileNotFoundError as exc:
            await self._record_operational_error(
                user_id=user_id,
                operation="video_subs",
                message="Snapshot dessa transcrição expirou. Reprocesse o vídeo.",
                context=_artifact_error_context(
                    selected, index=index, error=exc, artifact="video_subs"
                ),
                error=exc,
                stage="snapshot",
            )
            await self._send_text(
                chat_id, "Snapshot dessa transcrição expirou. Reprocesse o vídeo."
            )
            return
        except VideoSubtitleTooLongError as exc:
            await self._record_operational_error(
                user_id=user_id,
                operation="video_subs",
                message=f"Vídeo não exportado: {exc}",
                context=_artifact_error_context(
                    selected, index=index, error=exc, artifact="video_subs"
                ),
                error=exc,
                stage="limits",
                severity="warn",
            )
            await self._send_text(chat_id, f"Vídeo não exportado: {exc}")
            return
        except VideoSubtitleTooLargeError as exc:
            await self._record_operational_error(
                user_id=user_id,
                operation="video_subs",
                message=f"Vídeo não exportado: {exc}",
                context=_artifact_error_context(
                    selected, index=index, error=exc, artifact="video_subs"
                ),
                error=exc,
                stage="limits",
                severity="warn",
            )
            await self._send_text(chat_id, f"Vídeo não exportado: {exc}")
            return
        except VideoSubtitleExportError as exc:
            await self._record_operational_error(
                user_id=user_id,
                operation="video_subs",
                message=f"Falha ao gerar vídeo legendado: {exc}",
                context=_artifact_error_context(
                    selected, index=index, error=exc, artifact="video_subs"
                ),
                error=exc,
                stage="ffmpeg",
            )
            await self._send_text(chat_id, f"Falha ao gerar vídeo legendado: {exc}")
            return
        await self._send_text(
            chat_id,
            f"✅ MP4 com legenda selecionável gerado para a transcrição #{index}. Enviando vídeo…",
        )
        await self._send_video_with_retry(
            chat_id,
            result.path,
            caption=(
                "🎬 Vídeo com legenda selecionável\n"
                f"Arquivo: {_format_file_size(result.size_bytes)}\n"
                "A legenda foi adicionada como faixa selecionável no MP4."
            ),
        )

    async def handle_command_clearcache(self, *, chat_id: int, user_id: int) -> None:
        if not self._is_authorized(user_id):
            return
        if self._models_dir is None or not self._models_dir.is_dir():
            await self._send_text(chat_id, "Diretório de cache de modelos não definido.")
            return
        if not self._is_safe_models_cache_dir(self._models_dir):
            await self._send_text(
                chat_id,
                "Operação recusada: diretório de cache de modelos parece inseguro.",
            )
            return
        removed = 0
        failures: list[str] = []
        for entry in self._models_dir.rglob("*"):
            if entry.is_file():
                try:
                    entry.unlink()
                    removed += 1
                except OSError as exc:
                    failures.append(f"{entry}: {exc}")
        if failures:
            await self._record_operational_error(
                user_id=user_id,
                operation="clearcache",
                message=f"Falha ao remover {len(failures)} arquivo(s) do cache de modelos.",
                context={
                    "models_dir": self._models_dir,
                    "failed_files": " | ".join(failures[:5]),
                },
                stage="filesystem",
                severity="warn",
            )
        suffix = f" {len(failures)} falha(s) foram registradas em /lasterror." if failures else ""
        await self._send_text(chat_id, f"Cache limpo. {removed} arquivo(s) removido(s).{suffix}")

    def _is_safe_models_cache_dir(self, path: Path) -> bool:
        """Impede que /clearcache apague diretórios amplos por erro de configuração."""
        try:
            resolved = path.resolve()
            configured = self._settings.models_dir.resolve()
        except OSError:
            return False
        unsafe_names = {"", "/", "home", "usr", "var", "tmp", "etc", "opt"}
        return (
            resolved == configured
            and resolved.parent != resolved
            and resolved.name not in unsafe_names
            and len(resolved.parts) >= 2
        )

    def _extract_language_hint(self, text: str) -> str | None:
        """Extrai ``--lang pt``/``lang=pt`` de uma mensagem.

        Retorna ``None`` quando o usuário não informou idioma. A validação contra
        ``allowed_languages`` fica no handler, para permitir mensagem de erro
        mais amigável no Telegram.
        """
        match = re.search(r"(?:--lang|\blang)\s*[=:]?\s*([a-zA-Z]{2})\b", text or "")
        if not match:
            return None
        return match.group(1).lower()

    # ------------------------------------------------------------------
    # Diálogo de rename (interno)
    # ------------------------------------------------------------------

    async def _handle_rename_input(self, chat_id: int, user_id: int, text: str) -> None:
        session = self._rename_session
        assert session is not None
        assert self._rename_service is not None
        selected_label = session.selected_label
        aliases: dict[str, str]
        if selected_label is not None and "=" not in text:
            is_inline_name = True
            aliases = {selected_label: text.strip()} if text.strip() else {}
        else:
            is_inline_name = False
            aliases = _parse_rename_mapping(text)
        if not aliases:
            await self._send_text(
                chat_id,
                "Formato inválido. Use SPEAKER_00=João, SPEAKER_01=Maria, "
                "ou toque em um botão de falante e envie apenas o nome. Use /cancel para abortar.",
            )
            return
        merged_aliases = {**session.aliases, **aliases}
        result = await self._apply_rename_aliases(
            chat_id=chat_id, session=session, aliases=merged_aliases
        )
        if result is None:
            return
        session.aliases = merged_aliases
        if is_inline_name:
            changed = ", ".join(f"{label} → {name}" for label, name in aliases.items())
            session.selected_label = None
            await self._send_text(
                chat_id,
                f"✅ {changed} registrado. Toque em outro falante ou em ✅ Concluir.",
            )
            await self._send_document_with_retry(chat_id, result.md_path)
            return
        self._clear_pending_rename()
        await self._send_text(
            chat_id, f"✅ {result.speakers_renamed} falante(s) renomeado(s). Reenviando MD…"
        )
        await self._send_document_with_retry(chat_id, result.md_path)

    async def _apply_rename_aliases(
        self,
        *,
        chat_id: int,
        session: RenameSession,
        aliases: dict[str, str],
    ) -> RenameResult | None:
        # Recupera o job e o md_path selecionados no início do diálogo.
        assert self._repository is not None
        assert self._rename_service is not None
        target = self._repository.get_by_id(session.job_id)
        md_path = session.md_path or (target.md_path if target else None)
        if target is None or md_path is None:
            await self._send_text(chat_id, "Job selecionado não encontrado.")
            self._clear_pending_rename()
            return None
        try:
            result = self._rename_service.rename(session.slug, aliases, Path(md_path))
        except FileNotFoundError:
            await self._send_text(chat_id, "Snapshot expirou. Reprocesse o vídeo.")
            self._clear_pending_rename()
            return None
        # Atualiza speaker_renames no Job para auditoria
        target.speaker_renames = dict(aliases)
        self._repository.save(target)
        return result

    def _clear_pending_rename(self) -> None:
        self._rename_session = None

    @staticmethod
    def _slug_from_md_path(md_path: str | None) -> str | None:
        if md_path is None:
            return None
        return Path(md_path).stem

    def _format_history_job(self, job: Job) -> str:
        slug = self._slug_from_md_path(job.md_path)
        title: str | None = None
        if slug is not None and self._rename_service is not None:
            metadata = self._rename_service.metadata_for(slug)
            if metadata is not None:
                title = metadata.title
        label = title or (Path(job.md_path).stem if job.md_path else job.video_id.value)
        when = job.updated_at.strftime("%Y-%m-%d %H:%M")
        return f"{label} — {job.video_id.value} — executado em {when}"

    # ------------------------------------------------------------------
    # Worker — executa o use case e envia entregáveis
    # ------------------------------------------------------------------

    async def _process_job(self, item: QueuedItem[JobPayload]) -> None:
        payload = item.payload
        editor = _make_editor(self._client, payload.chat_id, payload.progress_message_id)
        progress = ProgressReporter(
            editor,
            min_interval_s=self._settings.telegram_message_edit_min_interval_s,
        )
        title = payload.url
        if payload.requested_language:
            title = f"{payload.url} — idioma informado: {payload.requested_language}"
        await progress.set_title(title)
        await progress.stage("📥 Buscando metadados…")

        loop = asyncio.get_running_loop()

        # Callbacks vindos do use case (rodando em thread executor) precisam
        # agendar de volta no loop principal para tocar no Telegram.
        def progress_step_cb(step_name: str, message: str) -> None:
            asyncio.run_coroutine_threadsafe(
                progress.stage(_humanize_step(step_name, message)), loop
            )

        def progress_transcribe_cb(fraction: float, _stage: str) -> None:
            asyncio.run_coroutine_threadsafe(progress.fixed_progress(fraction), loop)

        def progress_diarize_cb(fraction: float, _stage: str) -> None:
            asyncio.run_coroutine_threadsafe(progress.fixed_progress(fraction), loop)

        # Cria o Job de domínio
        job = Job.new(
            video_id=payload.video_id,
            user_id=payload.user_id,
            config_signature=self._settings.transcription_signature(),
        )
        self._audit(
            "job_started",
            job_id=job.job_id,
            video_id=payload.video_id.value,
            user_id=payload.user_id,
            requested_language=payload.requested_language or "auto",
            config_signature=job.config_signature,
        )

        def audit_cb(event: str, fields: dict[str, object]) -> None:
            self._audit(
                event,
                **fields,
                user_id=payload.user_id,
                requested_language=payload.requested_language or "auto",
            )

        try:
            result = await loop.run_in_executor(
                None,
                lambda: self._use_case.execute(
                    job,
                    progress_step=progress_step_cb,
                    progress_transcribe=progress_transcribe_cb,
                    progress_diarize=progress_diarize_cb,
                    audit=audit_cb,
                    cancel_event=payload.cancel_event,
                    requested_language=payload.requested_language,
                ),
            )
        except Exception as exc:
            logger.exception("Use case falhou: %s", exc)
            await self._record_operational_error(
                user_id=payload.user_id,
                operation="transcribe",
                message=f"Erro inesperado no pipeline: {type(exc).__name__}: {exc}",
                context={
                    "video_id": payload.video_id.value,
                    "url": payload.url,
                    "requested_language": payload.requested_language or "auto",
                },
                error=exc,
                stage="pipeline",
            )
            self._audit(
                "job_failed",
                job_id=job.job_id,
                video_id=payload.video_id.value,
                user_id=payload.user_id,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            await progress.finish(f"❌ Erro inesperado: {exc}")
            return

        if result.canceled:
            self._audit(
                "job_canceled",
                job_id=result.job.job_id,
                video_id=payload.video_id.value,
                user_id=payload.user_id,
            )
            await progress.finish("🛑 Cancelado pelo usuário.")
            await self._send_text(payload.chat_id, "✅ Job cancelado com sucesso.")
            return
        if result.failure_reason is not None:
            self._audit(
                "job_failed",
                job_id=result.job.job_id,
                video_id=payload.video_id.value,
                user_id=payload.user_id,
                error_message=result.failure_reason,
            )
            await progress.finish(f"⚠️ Falhou: {result.failure_reason}")
            return

        # Sucesso: envia áudio + markdown com retry.
        self._audit(
            "job_completed",
            job_id=result.job.job_id,
            video_id=payload.video_id.value,
            user_id=payload.user_id,
            language_code=result.language_code,
            language_source=result.language_source,
            has_audio=result.audio_path is not None,
            has_markdown=result.md_path is not None,
        )
        await progress.finish(f"✅ Pronto. Enviando arquivos…\n{_format_language_status(result)}")
        if result.audio_path is not None:
            await self._send_audio_with_retry(payload.chat_id, result.audio_path)
        if result.md_path is not None:
            await self._send_document_with_retry(payload.chat_id, result.md_path)
        self._apply_retention_after_success()

    def _apply_retention_after_success(self) -> None:
        """Aplica retenção FIFO após entrega bem-sucedida sem derrubar o bot."""
        if self._retention_policy is None:
            return
        try:
            result = self._retention_policy.apply()
        except Exception as exc:  # pragma: no cover - caminho defensivo
            logger.warning("Falha ao aplicar retenção FIFO: %s", exc)
            return
        if result.removed_files:
            logger.info(
                "Retenção FIFO: %d job(s) expirado(s), %d arquivo(s) removido(s).",
                len(result.expired_jobs),
                len(result.removed_files),
            )

    # ------------------------------------------------------------------
    # Envio com retry
    # ------------------------------------------------------------------

    async def _send_text(
        self, chat_id: int, text: str, reply_markup: InlineKeyboard | None = None
    ) -> int:
        try:
            return await send_with_retry(
                lambda: self._client.send_message(chat_id, text, reply_markup=reply_markup)
            )
        except TelegramSendError:
            return 0  # já loga internamente; não propaga

    async def _send_audio_with_retry(self, chat_id: int, path: Path) -> None:
        try:
            await send_with_retry(lambda: self._client.send_audio(chat_id, path))
        except TelegramSendError as exc:
            logger.error("Audio não enviado: %s", exc)

    async def _send_video_with_retry(
        self, chat_id: int, path: Path, caption: str | None = None
    ) -> None:
        try:
            await send_with_retry(lambda: self._client.send_video(chat_id, path, caption=caption))
        except TelegramSendError as exc:
            logger.error("Video não enviado: %s", exc)

    async def _send_document_with_retry(self, chat_id: int, path: Path) -> None:
        try:
            await send_with_retry(lambda: self._client.send_document(chat_id, path))
        except TelegramSendError as exc:
            logger.error("Documento não enviado: %s", exc)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _artifact_error_context(
    job: Job, *, index: int, error: BaseException, artifact: str
) -> dict[str, object]:
    """Contexto comum para falhas de artefatos derivados."""
    context: dict[str, object] = {
        "artifact": artifact,
        "history_index": index,
        "job_id": job.job_id,
        "video_id": job.video_id.value,
        "job_status": job.status.value,
        "error_type": type(error).__name__,
    }
    if job.md_path:
        context["md_path"] = job.md_path
    if job.audio_path:
        context["audio_path"] = job.audio_path
    return context


def _humanize_summary_progress(event: SummaryProgress) -> str:
    """Converte eventos de sumarização em texto curto para o painel do Telegram."""

    if event.kind == "planned":
        return f"🧩 {event.message}"
    if event.kind == "single_started":
        return "🧠 Enviando transcrição completa para a LLM…"
    if event.kind == "single_completed":
        return "✅ Resumo em passagem única concluído."
    if event.kind == "chunk_started":
        return f"🧠 {event.message}"
    if event.kind == "chunk_completed":
        return f"✅ {event.message}"
    if event.kind == "chunk_split":
        return f"⚠️ {event.message}"
    if event.kind == "synthesis_started":
        return "🧩 Blocos resumidos. Gerando síntese final…"
    if event.kind == "synthesis_completed":
        return "✅ Síntese final concluída. Preparando arquivo…"
    if event.kind == "synthesis_split":
        return f"⚠️ {event.message}"
    return event.message


def _make_editor(
    client: BotClient, chat_id: int, message_id: int
) -> Callable[[str], Awaitable[None]]:
    async def edit(text: str) -> None:
        await client.edit_message(chat_id, message_id, text)

    return edit


def _rename_keyboard(speakers: tuple[str, ...]) -> InlineKeyboard:
    rows: list[tuple[InlineButton, ...]] = []
    for label in speakers:
        rows.append((InlineButton(f"✏️ {label}", f"rename:speaker:{label}"),))
    rows.append((InlineButton("🔗 Mesclar falantes", "rename:merge"),))
    rows.append((InlineButton("✅ Concluir", "rename:done"),))
    return tuple(rows)


def _parse_rename_mapping(text: str) -> dict[str, str]:
    """Aceita 'SPEAKER_00=João, SPEAKER_01=Maria' e devolve dict.

    Aceita também linhas separadas por nova linha. Tolera espaços.
    Retorna dict vazio se nenhuma entrada válida foi encontrada.
    """
    out: dict[str, str] = {}
    for raw in text.replace("\n", ",").split(","):
        if "=" not in raw:
            continue
        label, name = raw.split("=", 1)
        label_clean = label.strip()
        name_clean = name.strip()
        if not label_clean.startswith("SPEAKER_") or not name_clean:
            continue
        out[label_clean] = name_clean
    return out


def _parse_export_command(text: str) -> tuple[str, int] | None:
    """Extrai formato e índice de ``/export srt 2``.

    Quando o índice é omitido, retorna 1 para operar sobre a transcrição mais
    recente, seguindo ``/last`` e ``/rename``.
    """
    parts = (text or "").strip().split()
    if len(parts) < 2:
        return None
    fmt = parts[1].strip().lower().lstrip(".")
    if fmt not in SUPPORTED_EXPORT_FORMATS:
        return None
    index = 1
    if len(parts) >= 3:
        try:
            index = int(parts[2])
        except ValueError:
            index = 1
    return fmt, index


def _parse_history_index(text: str) -> int:
    """Extrai índice positivo de comandos como ``/last 2`` ou ``/rename 2``.

    Quando nenhum número é informado, retorna 1 para manter compatibilidade
    com ``/last`` e ``/rename`` sobre a transcrição mais recente.
    """
    parts = (text or "").strip().split()
    if len(parts) < 2:
        return 1
    try:
        return int(parts[1])
    except ValueError:
        return 1


def _format_history_job(job: Job) -> str:
    stem = Path(job.md_path).stem if job.md_path else job.video_id.value
    when = job.updated_at.strftime("%Y-%m-%d %H:%M")
    return f"{stem} — {job.video_id.value} — {when}"


def _payload_language_suffix(payload: JobPayload) -> str:
    if payload.requested_language:
        return f" — idioma: {payload.requested_language}"
    return " — idioma: automático"


def _format_file_size(size_bytes: int) -> str:
    mb = size_bytes / (1024 * 1024)
    if mb >= 1:
        return f"{mb:.1f} MB"
    return f"{size_bytes / 1024:.1f} KB"


def _format_language_status(result: object) -> str:
    code = getattr(result, "language_code", None)
    source = getattr(result, "language_source", None)
    confidence = getattr(result, "language_confidence", None)
    if not code:
        return "🌐 Idioma: não determinado"
    labels = {
        "user": "informado pelo usuário",
        "metadata": "inferido dos metadados",
        "asr": "detectado pelo ASR",
        "youtube_manual": "legenda manual do YouTube",
        "youtube_auto": "legenda automática do YouTube",
    }
    label = labels.get(str(source), str(source or "detectado"))
    if isinstance(confidence, float):
        return f"🌐 Idioma: {code} ({label}; confiança {confidence * 100:.1f}%)"
    return f"🌐 Idioma: {code} ({label})"


_STEP_LABELS: dict[str, str] = {
    "fetch_metadata": "📋 Lendo metadados",
    "try_youtube_subtitles": "📑 Avaliando legendas do YouTube",
    "download_audio": "📥 Baixando áudio",
    "convert_audio": "🎚️ Comprimindo áudio",
    "select_runtime": "🧠 Selecionando hardware",
    "transcribe": "🎙️ Transcrevendo",
    "diarize": "👥 Identificando falantes",
    "render_md": "📝 Gerando Markdown",
    # Compatibilidade com versões antigas dos testes/docs.
    "FetchMetadataStep": "📋 Lendo metadados",
    "TryYouTubeSubtitlesStep": "📑 Avaliando legendas do YouTube",
    "DownloadAudioStep": "📥 Baixando áudio",
    "ConvertAudioStep": "🎚️ Comprimindo áudio",
    "SelectRuntimeStep": "🧠 Selecionando hardware",
    "TranscribeStep": "🎙️ Transcrevendo",
    "DiarizeStep": "👥 Identificando falantes",
    "RenderMarkdownStep": "📝 Gerando Markdown",
}


def _humanize_step(step_name: str, default_msg: str) -> str:
    return _STEP_LABELS.get(step_name, default_msg)
