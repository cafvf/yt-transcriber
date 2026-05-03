"""Entrypoint do bot. Roda com ``python -m yt_transcriber_bot``."""

from __future__ import annotations

import asyncio
import importlib.util
import logging
import shutil
import sys
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.composition_root import build
from yt_transcriber_bot.infrastructure.telegram.bot_adapter import TelegramBotAdapter
from yt_transcriber_bot.infrastructure.telegram.ptb_bot_client import PTBBotClient


def _configure_logging(logs_dir: Path) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    handler_file = logging.FileHandler(logs_dir / "bot.log", encoding="utf-8")
    handler_console = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler_file.setFormatter(fmt)
    handler_console.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler_file, handler_console]


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
    settings = AppSettings()
    _configure_logging(settings.logs_dir())
    _validate_environment(settings)

    logger = logging.getLogger("yt_transcriber_bot")
    logger.info("Iniciando bot. user_id=%s", settings.telegram_allowed_user_id)

    composition = build(settings)

    application: Application = (
        Application.builder().token(settings.telegram_bot_token).build()
    )
    client = PTBBotClient(application.bot)
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,
        use_case=composition.use_case,
        repository=composition.repository,
        rename_service=composition.rename_service,
        retention_policy=composition.retention_policy,
        models_dir=settings.models_dir,
    )

    def _uid(update: Update) -> int:
        return update.effective_user.id if update.effective_user else 0

    def _cid(update: Update) -> int:
        return update.effective_chat.id if update.effective_chat else 0

    async def on_text(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.effective_message.text if update.effective_message else ""
        await adapter.handle_message(chat_id=_cid(update), user_id=_uid(update), text=text or "")

    async def on_start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await adapter.handle_command_start(chat_id=_cid(update), user_id=_uid(update))

    async def on_help(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await adapter.handle_command_help(chat_id=_cid(update), user_id=_uid(update))

    async def on_status(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await adapter.handle_command_status(chat_id=_cid(update), user_id=_uid(update))

    async def on_cancel(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await adapter.handle_command_cancel(chat_id=_cid(update), user_id=_uid(update))

    async def on_redo(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.effective_message.text if update.effective_message else ""
        await adapter.handle_command_redo(chat_id=_cid(update), user_id=_uid(update), text=text or "")

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

    async def on_clearcache(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await adapter.handle_command_clearcache(chat_id=_cid(update), user_id=_uid(update))

    application.add_handler(CommandHandler("start", on_start))
    application.add_handler(CommandHandler("help", on_help))
    application.add_handler(CommandHandler("status", on_status))
    application.add_handler(CommandHandler("cancel", on_cancel))
    application.add_handler(CommandHandler("redo", on_redo))
    application.add_handler(CommandHandler("pt", on_pt))
    application.add_handler(CommandHandler("en", on_en))
    application.add_handler(CommandHandler("transcribe", on_transcribe))
    application.add_handler(CommandHandler("list", on_list))
    application.add_handler(CommandHandler("last", on_last))
    application.add_handler(CommandHandler("rename", on_rename))
    application.add_handler(CommandHandler("clearcache", on_clearcache))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    await adapter.start()
    try:
        async with application:
            await application.initialize()
            await application.start()
            assert application.updater is not None
            await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            logger.info("Bot em polling. Pressione Ctrl+C para parar.")
            stop_event = asyncio.Event()
            try:
                await stop_event.wait()
            except (KeyboardInterrupt, asyncio.CancelledError):
                pass
            await application.updater.stop()
            await application.stop()
    finally:
        await adapter.stop()


def main() -> None:
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        sys.stderr.write("\nEncerrando...\n")


if __name__ == "__main__":
    main()
