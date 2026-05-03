"""TelegramBotAdapter — adaptador principal sobre python-telegram-bot.

Responsabilidades:
- Receber mensagens, autorizar (silenciosamente) o user_id permitido.
- Detectar URLs do YouTube e enfileirar o job via SequentialJobQueue.
- Despachar comandos: /start, /help, /status, /cancel, /list, /last, /redo, /rename e /clearcache.
- Editar uma única mensagem para reportar progresso (ProgressReporter).
- Enviar áudio comprimido + arquivo .md final, com retry exponencial.

A integração com python-telegram-bot é deliberadamente fina — todo o
trabalho real é executado por dependências testáveis injetadas. Isso
permite testar o adapter sem a Bot API real (mockando o ``BotClient``).
"""

from __future__ import annotations

import asyncio
import logging
import threading
import re
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.application.services.rename_speakers import (
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


# ----------------------------------------------------------------------
# Protocolo do client (permite mockar a Bot API)
# ----------------------------------------------------------------------


class BotClient(Protocol):
    """Subset da Bot API que usamos. Permite mockagem nos testes."""

    async def send_message(self, chat_id: int, text: str) -> int:
        """Envia mensagem e retorna o ``message_id``."""
        ...

    async def edit_message(self, chat_id: int, message_id: int, text: str) -> None: ...

    async def send_document(
        self, chat_id: int, file_path: Path, caption: str | None = None
    ) -> None: ...

    async def send_audio(
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
        retention_policy: RetentionPolicy | None = None,
        models_dir: Path | None = None,
    ) -> None:
        self._settings = settings
        self._client = client
        self._use_case = use_case
        self._repository = repository
        self._rename_service = rename_service
        self._retention_policy = retention_policy
        self._models_dir = models_dir
        self._pending_rename_user: int | None = None
        self._pending_rename_slug: str | None = None
        self._pending_rename_job_id: str | None = None
        self._pending_rename_md_path: str | None = None
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
        # Diálogo de rename pendente?
        if self._pending_rename_user == user_id and self._pending_rename_slug:
            await self._handle_rename_input(chat_id, user_id, text or "")
            return
        raw_text = text or ""
        url = extract_first_youtube_url(raw_text)
        if url is None:
            await self._send_text(chat_id, "Envie um link do YouTube para transcrever.")
            return
        requested_language = self._extract_language_hint(raw_text)
        if requested_language is not None and requested_language not in self._settings.allowed_languages:
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
        if item.enqueued_position > 1:
            await self._send_text(chat_id, f"⏳ Posição na fila: {item.enqueued_position}.")

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
        await self._send_text(
            chat_id,
            "Comandos:\n"
            "• Mande um link do YouTube → transcrevo o áudio.\n"
            "• Idioma opcional: adicione --lang pt ou --lang en ao link.\n"
            "• Atalhos: /pt <link> e /en <link>.\n"
            "• /status → mostra o que está em processamento.\n"
            "• /cancel → cancela o job em andamento.\n"
            "• /list → últimas transcrições concluídas, numeradas.\n"
            "• /last [n] → reenvia a n-ésima transcrição concluída; ex.: /last 2.\n"
            "• /redo <link> → reprocessa um vídeo.\n"
            "• /rename [n] → renomear falantes da n-ésima transcrição; ex.: /rename 2.\n"
            "• /clearcache → apaga modelos baixados.",
        )

    async def handle_command_status(self, *, chat_id: int, user_id: int) -> None:
        if not self._is_authorized(user_id):
            return
        current, pending = self._queue.snapshot()
        if current is None and not pending:
            await self._send_text(chat_id, "Nada na fila. Pronto para receber links.")
            return
        lines: list[str] = []
        if current is not None:
            lines.append(f"▶️ Processando: {current.payload.url}{_payload_language_suffix(current.payload)}")
        for it in pending:
            lines.append(f"⏳ Aguardando: {it.payload.url}{_payload_language_suffix(it.payload)}")
        await self._send_text(chat_id, "\n".join(lines))

    async def handle_command_cancel(self, *, chat_id: int, user_id: int) -> None:
        if not self._is_authorized(user_id):
            return
        # Cancela diálogo de rename, se ativo
        if self._pending_rename_user == user_id and self._pending_rename_slug:
            self._clear_pending_rename()
            await self._send_text(chat_id, "Renomeação cancelada.")
            return
        current, _ = self._queue.snapshot()
        if current is None:
            await self._send_text(chat_id, "Nada para cancelar.")
            return
        # Sinaliza ao runner do use case + ao loop da queue
        current.payload.cancel_event.set()
        await self._queue.cancel_current()
        await self._send_text(chat_id, "🛑 Cancelando o job em andamento…")

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
        if requested_language is not None and requested_language not in self._settings.allowed_languages:
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
            lines.append(f"{idx}. {_format_history_job(job)}")
        await self._send_text(chat_id, "\n".join(lines))

    async def handle_command_last(
        self, *, chat_id: int, user_id: int, text: str = ""
    ) -> None:
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

    async def handle_command_rename(
        self, *, chat_id: int, user_id: int, text: str = ""
    ) -> None:
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
            await self._send_text(
                chat_id, "Não consegui localizar o snapshot dessa transcrição."
            )
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
        self._pending_rename_user = user_id
        self._pending_rename_slug = slug
        self._pending_rename_job_id = selected.job_id
        self._pending_rename_md_path = selected.md_path
        await self._send_text(
            chat_id,
            f"Renomear falantes da transcrição #{index}.\n"
            f"Alvo: {_format_history_job(selected)}\n"
            f"Falantes detectados: {', '.join(speakers)}\n"
            "Envie o mapeamento no formato: SPEAKER_00=João, SPEAKER_01=Maria\n"
            "Para mesclar falantes, use o mesmo nome em dois labels.\n"
            "Use /cancel para abortar.",
        )

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

    async def _select_completed_job(
        self, *, chat_id: int, user_id: int, index: int
    ) -> Job | None:
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
        for entry in self._models_dir.rglob("*"):
            if entry.is_file():
                try:
                    entry.unlink()
                    removed += 1
                except OSError:
                    continue
        await self._send_text(chat_id, f"Cache limpo. {removed} arquivo(s) removido(s).")

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
        slug = self._pending_rename_slug
        assert slug is not None
        assert self._rename_service is not None
        aliases = _parse_rename_mapping(text)
        if not aliases:
            await self._send_text(
                chat_id,
                "Formato inválido. Use SPEAKER_00=João, SPEAKER_01=Maria. Ou /cancel.",
            )
            return
        # Recupera o job e o md_path selecionados no início do diálogo.
        assert self._repository is not None
        target = (
            self._repository.get_by_id(self._pending_rename_job_id)
            if self._pending_rename_job_id
            else None
        )
        md_path = self._pending_rename_md_path or (target.md_path if target else None)
        if target is None or md_path is None:
            await self._send_text(chat_id, "Job selecionado não encontrado.")
            self._clear_pending_rename()
            return
        try:
            result = self._rename_service.rename(slug, aliases, Path(md_path))
        except FileNotFoundError:
            await self._send_text(chat_id, "Snapshot expirou. Reprocesse o vídeo.")
            self._clear_pending_rename()
            return
        # Atualiza speaker_renames no Job para auditoria
        target.speaker_renames = dict(aliases)
        self._repository.save(target)
        self._clear_pending_rename()
        await self._send_text(
            chat_id, f"✅ {result.speakers_renamed} falante(s) renomeado(s). Reenviando MD…"
        )
        await self._send_document_with_retry(chat_id, result.md_path)

    def _clear_pending_rename(self) -> None:
        self._pending_rename_user = None
        self._pending_rename_slug = None
        self._pending_rename_job_id = None
        self._pending_rename_md_path = None

    @staticmethod
    def _slug_from_md_path(md_path: str | None) -> str | None:
        if md_path is None:
            return None
        return Path(md_path).stem

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

        try:
            result = await loop.run_in_executor(
                None,
                lambda: self._use_case.execute(
                    job,
                    progress_step=progress_step_cb,
                    progress_transcribe=progress_transcribe_cb,
                    progress_diarize=progress_diarize_cb,
                    cancel_event=payload.cancel_event,
                    requested_language=payload.requested_language,
                ),
            )
        except Exception as exc:
            logger.exception("Use case falhou: %s", exc)
            await progress.finish(f"❌ Erro inesperado: {exc}")
            return

        if result.canceled:
            await progress.finish("🛑 Cancelado pelo usuário.")
            return
        if result.failure_reason is not None:
            await progress.finish(f"⚠️ Falhou: {result.failure_reason}")
            return

        # Sucesso: envia áudio + markdown com retry.
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

    async def _send_text(self, chat_id: int, text: str) -> int:
        try:
            return await send_with_retry(lambda: self._client.send_message(chat_id, text))
        except TelegramSendError:
            return 0  # já loga internamente; não propaga

    async def _send_audio_with_retry(self, chat_id: int, path: Path) -> None:
        try:
            await send_with_retry(lambda: self._client.send_audio(chat_id, path))
        except TelegramSendError as exc:
            logger.error("Audio não enviado: %s", exc)

    async def _send_document_with_retry(self, chat_id: int, path: Path) -> None:
        try:
            await send_with_retry(lambda: self._client.send_document(chat_id, path))
        except TelegramSendError as exc:
            logger.error("Documento não enviado: %s", exc)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _make_editor(
    client: BotClient, chat_id: int, message_id: int
) -> Callable[[str], Awaitable[None]]:
    async def edit(text: str) -> None:
        await client.edit_message(chat_id, message_id, text)

    return edit


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
