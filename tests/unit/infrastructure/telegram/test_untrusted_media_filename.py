"""Untrusted Telegram filename containment regressions."""

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
async def test_user_filename_cannot_choose_staging_path(tmp_path: Path) -> None:
    bot = _Bot()
    client = PTBBotClient(bot)  # type: ignore[arg-type]
    media = IncomingMedia(
        "file-id",
        "../../outside.mp3",
        "audio/mpeg",
        10,
        1,
        IncomingMediaKind.DOCUMENT,
    )

    result = await client.download(media, tmp_path)

    assert result.parent == tmp_path
    assert result.name != "outside.mp3"
    assert result.suffix == ".mp3"
    assert result.exists()
    assert not (tmp_path.parent / "outside.mp3").exists()
