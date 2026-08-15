"""Regressões do Gate 9.2 para entrada de mídia do Telegram."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.incoming_media import (
    AudioDurationInspector,
    IncomingMedia,
    IncomingMediaDownloader,
    IncomingMediaKind,
)
from yt_transcriber_bot.domain.value_objects.media_source import MediaSource
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.telegram.bot_adapter import JobPayload, TelegramBotAdapter


@dataclass
class _Client:
    sent: list[str] = field(default_factory=list)

    async def send_message(
        self, _chat_id: int, text: str, reply_markup: object | None = None
    ) -> int:
        self.sent.append(text)
        return len(self.sent)

    async def edit_message(self, *_args: object) -> None:
        pass

    async def send_document(self, *_args: object, **_kwargs: object) -> None:
        pass

    async def send_audio(self, *_args: object, **_kwargs: object) -> None:
        pass

    async def send_video(self, *_args: object, **_kwargs: object) -> None:
        pass


@dataclass
class _Downloader(IncomingMediaDownloader):
    calls: list[IncomingMedia] = field(default_factory=list)

    async def download(self, media: IncomingMedia, dest_dir: Path) -> Path:
        self.calls.append(media)
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / "incoming.ogg"
        path.write_bytes(b"audio")
        return path


@dataclass
class _UseCase:
    calls: list[object] = field(default_factory=list)

    def execute(self, job: object, **_kwargs: object) -> object:
        self.calls.append(job)
        raise AssertionError("a fila não deve executar neste teste")


@dataclass
class _DurationInspector(AudioDurationInspector):
    duration: int

    def duration_seconds(self, _path: Path) -> int:
        return self.duration


class _FailingRepository:
    def save(self, _job: object) -> None:
        raise OSError("database password=do-not-expose")


@dataclass
class _RecordingRepository:
    jobs: list[object] = field(default_factory=list)

    def save(self, job: object) -> None:
        self.jobs.append(job)


@pytest.fixture
def settings(tmp_path: Path) -> AppSettings:
    return AppSettings(
        telegram_bot_token="dummy", telegram_allowed_user_id=42, hf_token="dummy", data_dir=tmp_path
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "name", "mime"),
    [
        (IncomingMediaKind.AUDIO, "reuniao.mp3", "audio/mpeg"),
        (IncomingMediaKind.VOICE, None, "audio/ogg"),
        (IncomingMediaKind.DOCUMENT, "entrevista.wav", "audio/wav"),
    ],
)
async def test_audio_voice_and_document_are_validated_then_enqueued(
    settings: AppSettings, kind: IncomingMediaKind, name: str | None, mime: str
) -> None:
    client = _Client()
    downloader = _Downloader()
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,
        use_case=_UseCase(),
        repository=_RecordingRepository(),  # type: ignore[arg-type]
        media_downloader=downloader,  # type: ignore[arg-type]
    )
    await adapter.handle_incoming_media(
        chat_id=10,
        user_id=42,
        media=IncomingMedia("file-123", name, mime, 1024, 60, kind),
    )
    assert downloader.calls
    assert downloader.calls[0].kind is kind
    current, pending = adapter._queue.snapshot()
    assert current is None
    assert len(pending) == 1
    assert pending[0].payload.media is not None
    assert pending[0].payload.media.kind is kind
    assert pending[0].payload.media_source == MediaSource.telegram_audio("file-123")


def test_payload_rebuild_preserves_telegram_source_without_repository(
    settings: AppSettings,
) -> None:
    adapter = TelegramBotAdapter(settings=settings, client=_Client(), use_case=_UseCase())  # type: ignore[arg-type]
    source = MediaSource.telegram_audio("file-123")
    job = adapter._load_or_create_job(
        JobPayload(
            None,
            10,
            42,
            "/private/audio.ogg",
            VideoId("abcdefghijk"),
            1,
            media_source=source,
            source_title="Reunião",
            source_duration_seconds=60,
        )
    )
    assert job.media_source == source
    assert job.video_id is None
    assert job.source_title == "Reunião"


@pytest.mark.asyncio
async def test_document_duration_is_inspected_before_enqueue_and_staged_file_is_removed(
    settings: AppSettings,
) -> None:
    client = _Client()
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,
        use_case=_UseCase(),
        media_downloader=_Downloader(),
        duration_inspector=_DurationInspector(181 * 60),  # type: ignore[arg-type]
    )
    before = (
        set(settings.downloads_dir().glob("**/*")) if settings.downloads_dir().exists() else set()
    )
    await adapter.handle_incoming_media(
        chat_id=10,
        user_id=42,
        media=IncomingMedia(
            "file-doc", "entrevista.wav", "audio/wav", 1024, None, IncomingMediaKind.DOCUMENT
        ),
    )
    current, pending = adapter._queue.snapshot()
    assert current is None
    assert pending == ()
    assert set(settings.downloads_dir().glob("**/*")) == before


@pytest.mark.asyncio
async def test_persistence_failure_does_not_enqueue_media_and_cleans_staging(
    settings: AppSettings,
) -> None:
    client = _Client()
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,
        use_case=_UseCase(),
        repository=_FailingRepository(),  # type: ignore[arg-type]
        media_downloader=_Downloader(),
    )
    before = (
        set(settings.downloads_dir().glob("**/*")) if settings.downloads_dir().exists() else set()
    )

    await adapter.handle_incoming_media(
        chat_id=10,
        user_id=42,
        media=IncomingMedia("file-123", None, "audio/ogg", 1024, 60, IncomingMediaKind.VOICE),
    )

    current, pending = adapter._queue.snapshot()
    assert current is None
    assert pending == ()
    assert set(settings.downloads_dir().glob("**/*")) == before
    assert "database password" not in "\n".join(client.sent)
    assert any("Não foi possível enfileirar" in message for message in client.sent)


@pytest.mark.asyncio
async def test_media_enqueue_requires_repository_before_download(
    settings: AppSettings,
) -> None:
    client = _Client()
    downloader = _Downloader()
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,
        use_case=_UseCase(),
        media_downloader=downloader,  # type: ignore[arg-type]
    )

    await adapter.handle_incoming_media(
        chat_id=10,
        user_id=42,
        media=IncomingMedia("file-123", None, "audio/ogg", 1024, 60, IncomingMediaKind.VOICE),
    )

    current, pending = adapter._queue.snapshot()
    assert current is None
    assert pending == ()
    assert downloader.calls == []
    assert any("indisponível" in message for message in client.sent)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "media",
    [
        IncomingMedia("bad-type", "x.txt", "text/plain", 20, 1, IncomingMediaKind.DOCUMENT),
        IncomingMedia("bad-ext", "x.exe", "audio/mpeg", 20, 1, IncomingMediaKind.DOCUMENT),
        IncomingMedia("audio-bad-ext", "x.exe", "audio/mpeg", 20, 1, IncomingMediaKind.AUDIO),
        IncomingMedia("big", "x.mp3", "audio/mpeg", 21 * 1024 * 1024, 1, IncomingMediaKind.AUDIO),
        IncomingMedia("long", "x.mp3", "audio/mpeg", 20, 181 * 60, IncomingMediaKind.AUDIO),
    ],
)
async def test_invalid_media_is_rejected_before_download_or_enqueue(
    settings: AppSettings, media: IncomingMedia
) -> None:
    client = _Client()
    downloader = _Downloader()
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,
        use_case=_UseCase(),
        media_downloader=downloader,  # type: ignore[arg-type]
    )
    await adapter.handle_incoming_media(chat_id=10, user_id=42, media=media)
    assert downloader.calls == []
    current, pending = adapter._queue.snapshot()
    assert current is None
    assert pending == ()
    assert client.sent
