"""Implementação de ``BotClient`` em cima de ``python-telegram-bot`` v21+.

Mantém a interface mínima exigida por ``TelegramBotAdapter``. Responsabilidades:
- enviar/editar mensagens de texto
- enviar documentos (.md) e áudio (.ogg)
- converter botões inline simples para ``InlineKeyboardMarkup``
- propagar exceções para que o retry do adapter possa atuar.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)


class PTBBotClient:
    """Adapter fino para a Bot API via python-telegram-bot."""

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_message(
        self, chat_id: int, text: str, reply_markup: Any | None = None
    ) -> int:
        msg = await self._bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=_to_inline_keyboard_markup(reply_markup),
        )
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

    async def send_video(
        self, chat_id: int, file_path: Path, caption: str | None = None
    ) -> None:
        with file_path.open("rb") as fh:
            await self._bot.send_video(
                chat_id=chat_id, video=fh, filename=file_path.name, caption=caption
            )


def _to_inline_keyboard_markup(reply_markup: Any | None) -> InlineKeyboardMarkup | None:
    if reply_markup is None:
        return None
    rows: list[list[InlineKeyboardButton]] = []
    for row in reply_markup:
        buttons: list[InlineKeyboardButton] = []
        for button in row:
            text = getattr(button, "text")
            callback_data = getattr(button, "callback_data")
            buttons.append(InlineKeyboardButton(text=text, callback_data=callback_data))
        rows.append(buttons)
    return InlineKeyboardMarkup(rows)
