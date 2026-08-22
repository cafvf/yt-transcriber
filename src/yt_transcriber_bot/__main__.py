"""Entrypoint do bot. Roda com ``python -m yt_transcriber_bot``."""

from __future__ import annotations

import asyncio
import contextlib
import importlib.util
import logging
import shutil
import sys

from telegram import Update
from telegram.ext import (
    ApplicationHandlerStop,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.incoming_media import (
    IncomingMedia,
    IncomingMediaKind,
)
from yt_transcriber_bot.composition_root import build_runtime, configure_runtime_logging
from yt_transcriber_bot.configuration.runtime_settings import load_runtime_settings


def _missing_runtime_ml_dependencies() -> list[str]:
    """Lista dependências de ML ausentes sem importá-las de fato.

    Usamos ``find_spec`` para evitar carregar PyTorch/WhisperX no startup.
    Isso torna o erro de instalação explícito antes de o usuário enviar o
    primeiro link ao Telegram.
    """

    required_modules = {
        "torch": "torch",
        "whisperx": "whisperx",
        "pyannote.audio": "pyannote.audio",
    }
    missing: list[str] = []
    for package_name, module_name in required_modules.items():
        if importlib.util.find_spec(module_name) is None:
            missing.append(package_name)
    return missing


def _validate_environment(settings: AppSettings) -> None:
    problems = settings.validate_runtime_secrets()
    if shutil.which("ffmpeg") is None:
        problems.append(
            "ffmpeg nao encontrado no PATH. Instale com:\n"
            "  Fedora:  sudo dnf install ffmpeg\n"
            "  Ubuntu:  sudo apt install ffmpeg"
        )

    missing_ml = _missing_runtime_ml_dependencies()
    if missing_ml:
        problems.append(
            "Dependencias de ML ausentes: "
            + ", ".join(missing_ml)
            + ". Rode: uv sync. Em pacotes antigos, use: uv sync --extra ml. "
            "Se o lock estiver desatualizado, rode: uv lock && uv sync."
        )

    if problems:
        sys.stderr.write("Falha de configuracao:\n")
        for p in problems:
            sys.stderr.write(f"  - {p}\n")
        sys.exit(2)


async def _run() -> None:
    settings = load_runtime_settings()
    configure_runtime_logging(settings)
    _validate_environment(settings)

    logger = logging.getLogger("yt_transcriber_bot")
    logger.info("Iniciando bot. user_id=%s", settings.telegram_allowed_user_id)

    credentials = settings.credentials
    runtime = build_runtime(settings, credentials=credentials)
    application = runtime.application
    adapter = runtime.adapter
    audience = runtime.audience

    def _uid(update: Update) -> int:
        return update.effective_user.id if update.effective_user else 0

    def _cid(update: Update) -> int:
        return update.effective_chat.id if update.effective_chat else 0

    async def on_unsupported_message(_update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        """Stop unsupported message audiences before any product handler."""

        raise ApplicationHandlerStop

    async def on_text(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.effective_message.text if update.effective_message else ""
        await adapter.handle_message(chat_id=_cid(update), user_id=_uid(update), text=text or "")

    async def on_media(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        if message is None:
            return
        if message.audio is not None:
            media = IncomingMedia(
                file_id=message.audio.file_id,
                file_name=message.audio.file_name,
                mime_type=message.audio.mime_type,
                size_bytes=message.audio.file_size,
                duration_seconds=message.audio.duration,
                kind=IncomingMediaKind.AUDIO,
            )
        elif message.voice is not None:
            media = IncomingMedia(
                file_id=message.voice.file_id,
                file_name=None,
                mime_type=message.voice.mime_type,
                size_bytes=message.voice.file_size,
                duration_seconds=message.voice.duration,
                kind=IncomingMediaKind.VOICE,
            )
        elif message.document is not None:
            media = IncomingMedia(
                file_id=message.document.file_id,
                file_name=message.document.file_name,
                mime_type=message.document.mime_type,
                size_bytes=message.document.file_size,
                duration_seconds=None,
                kind=IncomingMediaKind.DOCUMENT,
            )
        else:
            return
        await adapter.handle_incoming_media(
            chat_id=_cid(update),
            user_id=_uid(update),
            media=media,
        )

    async def on_start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await adapter.handle_command_start(chat_id=_cid(update), user_id=_uid(update))

    async def on_help(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await adapter.handle_command_help(chat_id=_cid(update), user_id=_uid(update))

    async def on_status(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await adapter.handle_command_status(chat_id=_cid(update), user_id=_uid(update))

    async def on_healthcheck(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await adapter.handle_command_healthcheck(chat_id=_cid(update), user_id=_uid(update))

    async def on_lasterror(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await adapter.handle_command_lasterror(chat_id=_cid(update), user_id=_uid(update))

    async def on_queue(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await adapter.handle_command_queue(chat_id=_cid(update), user_id=_uid(update))

    async def on_clearqueue(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await adapter.handle_command_clearqueue(chat_id=_cid(update), user_id=_uid(update))

    async def on_cancelall(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await adapter.handle_command_cancelall(chat_id=_cid(update), user_id=_uid(update))

    async def on_cancel(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await adapter.handle_command_cancel(chat_id=_cid(update), user_id=_uid(update))

    async def on_redo(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.effective_message.text if update.effective_message else ""
        await adapter.handle_command_redo(
            chat_id=_cid(update), user_id=_uid(update), text=text or ""
        )

    async def on_pt(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.effective_message.text if update.effective_message else ""
        await adapter.handle_command_language_link(
            chat_id=_cid(update), user_id=_uid(update), text=text or "", language="pt"
        )

    async def on_en(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.effective_message.text if update.effective_message else ""
        await adapter.handle_command_language_link(
            chat_id=_cid(update), user_id=_uid(update), text=text or "", language="en"
        )

    async def on_transcribe(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.effective_message.text if update.effective_message else ""
        await adapter.handle_message(chat_id=_cid(update), user_id=_uid(update), text=text or "")

    async def on_list(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await adapter.handle_command_list(chat_id=_cid(update), user_id=_uid(update))

    async def on_search(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.effective_message.text if update.effective_message else ""
        await adapter.handle_command_search(
            chat_id=_cid(update), user_id=_uid(update), text=text or ""
        )

    async def on_last(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.effective_message.text if update.effective_message else ""
        await adapter.handle_command_last(
            chat_id=_cid(update), user_id=_uid(update), text=text or ""
        )

    async def on_rename(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.effective_message.text if update.effective_message else ""
        await adapter.handle_command_rename(
            chat_id=_cid(update), user_id=_uid(update), text=text or ""
        )

    async def on_summary(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.effective_message.text if update.effective_message else ""
        await adapter.handle_command_summary(
            chat_id=_cid(update), user_id=_uid(update), text=text or ""
        )

    async def on_export(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.effective_message.text if update.effective_message else ""
        await adapter.handle_command_export(
            chat_id=_cid(update), user_id=_uid(update), text=text or ""
        )

    async def on_text_export(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.effective_message.text if update.effective_message else ""
        await adapter.handle_command_text(
            chat_id=_cid(update), user_id=_uid(update), text=text or ""
        )

    async def on_export_shortcut(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.effective_message.text if update.effective_message else ""
        command = (text or "").strip().split(maxsplit=1)[0].lstrip("/").split("@", 1)[0].lower()
        await adapter.handle_command_export_shortcut(
            chat_id=_cid(update), user_id=_uid(update), format=command, text=text or ""
        )

    async def on_video_subs(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.effective_message.text if update.effective_message else ""
        await adapter.handle_command_video_subs(
            chat_id=_cid(update), user_id=_uid(update), text=text or ""
        )

    async def on_clearcache(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await adapter.handle_command_clearcache(chat_id=_cid(update), user_id=_uid(update))

    async def on_callback(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None:
            return
        chat_id = query.message.chat.id if query.message else _cid(update)
        chat_type = query.message.chat.type if query.message else None
        user_id = query.from_user.id if query.from_user else _uid(update)
        if not audience.allows(user_id=user_id, chat_id=chat_id, chat_type=chat_type):
            raise ApplicationHandlerStop
        await query.answer()
        data = query.data or ""
        await adapter.handle_callback_query(chat_id=chat_id, user_id=user_id, data=data)

    # This first message handler matches only unsupported audiences. Allowed
    # private messages fall through to the existing command/text/media handlers
    # in the same PTB group; denied messages stop before any product work.
    application.add_handler(MessageHandler(runtime.denied_audience_filter, on_unsupported_message))

    application.add_handler(CommandHandler("start", on_start))
    application.add_handler(CommandHandler("help", on_help))
    application.add_handler(CommandHandler("status", on_status))
    application.add_handler(CommandHandler("healthcheck", on_healthcheck))
    application.add_handler(CommandHandler("lasterror", on_lasterror))
    application.add_handler(CommandHandler(["queue", "fila"], on_queue))
    application.add_handler(
        CommandHandler(["clearqueue", "cancelqueue", "limparfila"], on_clearqueue)
    )
    application.add_handler(CommandHandler(["cancelall", "cancelartudo"], on_cancelall))
    application.add_handler(CommandHandler("cancel", on_cancel))
    application.add_handler(CommandHandler("redo", on_redo))
    application.add_handler(CommandHandler("pt", on_pt))
    application.add_handler(CommandHandler("en", on_en))
    application.add_handler(CommandHandler("transcribe", on_transcribe))
    application.add_handler(CommandHandler("list", on_list))
    application.add_handler(CommandHandler("search", on_search))
    application.add_handler(CommandHandler("last", on_last))
    application.add_handler(CommandHandler("rename", on_rename))
    application.add_handler(CommandHandler("summary", on_summary))
    application.add_handler(CommandHandler("text", on_text_export))
    application.add_handler(CommandHandler("export", on_export))
    application.add_handler(CommandHandler(["json", "srt", "vtt"], on_export_shortcut))
    application.add_handler(CommandHandler(["video_subs", "videosubs"], on_video_subs))
    application.add_handler(CommandHandler("clearcache", on_clearcache))
    application.add_handler(CallbackQueryHandler(on_callback, pattern=r"^rename:"))
    application.add_handler(MessageHandler(filters.COMMAND, on_text))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    application.add_handler(
        MessageHandler(filters.AUDIO | filters.VOICE | filters.Document.AUDIO, on_media)
    )

    async with application:
        application_started = False
        updater_started = False
        try:
            await adapter.start()
            await application.start()
            application_started = True
            assert application.updater is not None
            await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            updater_started = True
            logger.info("Bot em polling. Pressione Ctrl+C para parar.")
            stop_event = asyncio.Event()
            with contextlib.suppress(KeyboardInterrupt, asyncio.CancelledError):
                await stop_event.wait()
        finally:
            await adapter.stop()
            if updater_started:
                assert application.updater is not None
                await application.updater.stop()
            if application_started:
                await application.stop()


def main() -> None:
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        sys.stderr.write("\nEncerrando...\n")


if __name__ == "__main__":
    main()
