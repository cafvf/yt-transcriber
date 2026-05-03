"""Implementação de ``BotClient`` em cima de ``python-telegram-bot`` v21+.

Mantém a interface mínima exigida por ``TelegramBotAdapter``. Responsabilidades:
- enviar/editar mensagens de texto
- enviar documentos (.md) e áudio (.ogg)
- propagar exceções para que o retry do adapter possa atuar.
"""

from __future__ import annotations

import logging
from pathlib import Path

from telegram import Bot

logger = logging.getLogger(__name__)


class PTBBotClient:
    """Adapter fino para a Bot API via python-telegram-bot."""

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_message(self, chat_id: int, text: str) -> int:
        msg = await self._bot.send_message(chat_id=chat_id, text=text)
        return msg.message_id

    async def edit_message(self, chat_id: int, message_id: int, text: str) -> None:
        await self._bot.edit_message_text(
            chat_id=chat_id, message_id=message_id, text=text
        )

    async def send_document(
        self, chat_id: int, file_path: Path, caption: str | None = None
    ) -> None:
        with file_path.open("rb") as fh:
            await self._bot.send_document(
                chat_id=chat_id, document=fh, filename=file_path.name, caption=caption
            )

    async def send_audio(
        self, chat_id: int, file_path: Path, caption: str | None = None
    ) -> None:
        with file_path.open("rb") as fh:
            await self._bot.send_audio(
                chat_id=chat_id, audio=fh, filename=file_path.name, caption=caption
            )
