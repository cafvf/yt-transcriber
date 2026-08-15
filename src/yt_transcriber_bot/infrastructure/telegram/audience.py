"""Telegram audience policy for the private single-operator product surface."""

from __future__ import annotations

from dataclasses import dataclass

from telegram import Message
from telegram.ext import filters

PRIVATE_CHAT_TYPE = "private"


@dataclass(frozen=True)
class TelegramAudiencePolicy:
    """Authorize only the configured operator in that operator's private chat."""

    allowed_user_id: int

    def allows(self, *, user_id: int, chat_id: int, chat_type: str | None) -> bool:
        return (
            self.allowed_user_id > 0
            and user_id == self.allowed_user_id
            and chat_id == self.allowed_user_id
            and (chat_type or "").lower() == PRIVATE_CHAT_TYPE
        )


class DeniedAudienceFilter(filters.MessageFilter):
    """Match messages that are outside the supported private audience."""

    def __init__(self, policy: TelegramAudiencePolicy) -> None:
        super().__init__(name="DeniedAudienceFilter")
        self._policy = policy

    def filter(self, message: Message) -> bool:
        user_id = message.from_user.id if message.from_user is not None else 0
        return not self._policy.allows(
            user_id=user_id,
            chat_id=message.chat.id,
            chat_type=message.chat.type,
        )
