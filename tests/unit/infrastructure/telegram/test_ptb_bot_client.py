"""Regressões para armazenamento local de mídia Telegram."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from yt_transcriber_bot.application.ports.incoming_media import IncomingMedia, IncomingMediaKind
from yt_transcriber_bot.infrastructure.telegram.ptb_bot_client import PTBBotClient


@dataclass
class _TelegramFile:
    paths: list[Path]

    async def download_to_drive(self, custom_path: Path) -> None:
        self.paths.append(custom_path)
        custom_path.write_bytes(b"audio")


class _Bot:
    def __init__(self) -> None:
        self.paths: list[Path] = []

    async def get_file(self, _file_id: str) -> _TelegramFile:
        return _TelegramFile(self.paths)


@pytest.mark.asyncio
async def test_two_voice_messages_receive_distinct_staging_paths(tmp_path: Path) -> None:
    bot = _Bot()
    client = PTBBotClient(bot)  # type: ignore[arg-type]
    voice = IncomingMedia("same-file-id", None, "audio/ogg", 1, 1, IncomingMediaKind.VOICE)

    first = await client.download(voice, tmp_path)
    second = await client.download(voice, tmp_path)

    assert first != second
    assert first.exists()
    assert second.exists()
