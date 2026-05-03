"""Testes do TelegramBotAdapter — sem usar a API real do Telegram."""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.use_cases.transcribe_video import (
    TranscribeVideoResult,
)
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.telegram.bot_adapter import (
    JobPayload,
    TelegramBotAdapter,
)

# --------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------


@dataclass
class _SentMessage:
    chat_id: int
    text: str
    reply_markup: object | None = None


@dataclass
class _SentDoc:
    chat_id: int
    path: Path


class FakeBotClient:
    def __init__(self) -> None:
        self.sent: list[_SentMessage] = []
        self.edits: list[tuple[int, int, str]] = []
        self.docs: list[_SentDoc] = []
        self.audios: list[_SentDoc] = []
        self._next_message_id = 100
        self.fail_send_count = 0

    async def send_message(self, chat_id: int, text: str, reply_markup: object | None = None) -> int:
        if self.fail_send_count > 0:
            self.fail_send_count -= 1
            raise RuntimeError("transient")
        self.sent.append(_SentMessage(chat_id, text, reply_markup))
        self._next_message_id += 1
        return self._next_message_id

    async def edit_message(self, chat_id: int, message_id: int, text: str) -> None:
        self.edits.append((chat_id, message_id, text))

    async def send_document(
        self, chat_id: int, file_path: Path, caption: str | None = None
    ) -> None:
        self.docs.append(_SentDoc(chat_id, file_path))

    async def send_audio(self, chat_id: int, file_path: Path, caption: str | None = None) -> None:
        self.audios.append(_SentDoc(chat_id, file_path))


@dataclass
class FakeUseCase:
    """UseCase falso que devolve um resultado pré-configurado."""

    result: TranscribeVideoResult | None = None
    raise_exc: BaseException | None = None
    last_call_kwargs: dict[str, Any] = field(default_factory=dict)
    sleep_s: float = 0.0
    cancel_check_event: threading.Event | None = None

    def execute(self, job: Job, **kwargs: Any) -> TranscribeVideoResult:
        self.last_call_kwargs = kwargs
        if self.cancel_check_event is not None:
            self.cancel_check_event.set()
        if self.sleep_s > 0:
            event: threading.Event | None = kwargs.get("cancel_event")
            # poll cancelamento durante o sleep
            for _ in range(int(self.sleep_s * 100)):
                if event is not None and event.is_set():
                    return TranscribeVideoResult(
                        job=job,
                        md_path=None,
                        audio_path=None,
                        diagnostics=(),
                        canceled=True,
                    )
                import time

                time.sleep(0.01)
        if self.raise_exc is not None:
            raise self.raise_exc
        assert self.result is not None
        return self.result


# --------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------


@pytest.fixture
def settings(tmp_path: Path) -> AppSettings:
    return AppSettings(
        telegram_bot_token="dummy",
        telegram_allowed_user_id=42,
        hf_token="dummy",
        data_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
        logs_dir=tmp_path / "logs",
        telegram_message_edit_min_interval_s=0.5,
    )


@pytest.fixture
def client() -> FakeBotClient:
    return FakeBotClient()


@pytest.fixture
def fake_use_case() -> FakeUseCase:
    return FakeUseCase()


@pytest.fixture
async def adapter(
    settings: AppSettings, client: FakeBotClient, fake_use_case: FakeUseCase
) -> TelegramBotAdapter:
    a = TelegramBotAdapter(settings=settings, client=client, use_case=fake_use_case)  # type: ignore[arg-type]
    await a.start()
    yield a  # type: ignore[misc]
    await a.stop()


# --------------------------------------------------------------------
# Autorização (silenciosa)
# --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthorized_user_is_silently_ignored(
    adapter: TelegramBotAdapter, client: FakeBotClient
) -> None:
    await adapter.handle_message(chat_id=1, user_id=999, text="https://youtu.be/dQw4w9WgXcQ")
    await adapter.handle_command_start(chat_id=1, user_id=999)
    await adapter.handle_command_help(chat_id=1, user_id=999)
    await adapter.handle_command_status(chat_id=1, user_id=999)
    await adapter.handle_command_cancel(chat_id=1, user_id=999)
    assert client.sent == []
    assert client.edits == []


@pytest.mark.asyncio
async def test_authorized_user_gets_response(
    adapter: TelegramBotAdapter, client: FakeBotClient
) -> None:
    await adapter.handle_command_start(chat_id=10, user_id=42)
    assert any("link do YouTube" in m.text for m in client.sent)


# --------------------------------------------------------------------
# Mensagens com link
# --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_url_in_text_responds_with_hint(
    adapter: TelegramBotAdapter, client: FakeBotClient
) -> None:
    await adapter.handle_message(chat_id=1, user_id=42, text="oi")
    assert any("link do YouTube" in m.text for m in client.sent)


@pytest.mark.asyncio
async def test_invalid_youtube_url(adapter: TelegramBotAdapter, client: FakeBotClient) -> None:
    await adapter.handle_message(chat_id=1, user_id=42, text="https://youtube.com/abc")
    assert any("inválido" in m.text.lower() for m in client.sent)


@pytest.mark.asyncio
async def test_valid_url_is_enqueued_and_executed(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    fake_use_case: FakeUseCase,
    tmp_path: Path,
) -> None:
    md = tmp_path / "out.md"
    md.write_text("# ok")
    audio = tmp_path / "out.ogg"
    audio.write_bytes(b"OggS")
    fake_use_case.result = TranscribeVideoResult(
        job=Job.new(VideoId("dQw4w9WgXcQ"), 42),
        md_path=md,
        audio_path=audio,
        diagnostics=(),
    )
    await adapter.handle_message(chat_id=10, user_id=42, text="https://youtu.be/dQw4w9WgXcQ")
    # Espera worker concluir
    await asyncio.sleep(0.2)
    assert any(d.path == md for d in client.docs)
    assert any(a.path == audio for a in client.audios)


# --------------------------------------------------------------------
# Status / Cancel
# --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_when_idle(adapter: TelegramBotAdapter, client: FakeBotClient) -> None:
    await adapter.handle_command_status(chat_id=1, user_id=42)
    assert any("Bot ocioso" in m.text for m in client.sent)


@pytest.mark.asyncio
async def test_cancel_when_idle(adapter: TelegramBotAdapter, client: FakeBotClient) -> None:
    await adapter.handle_command_cancel(chat_id=1, user_id=42)
    assert any("Nada para cancelar" in m.text for m in client.sent)


@pytest.mark.asyncio
async def test_cancel_signals_use_case(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    fake_use_case: FakeUseCase,
) -> None:
    fake_use_case.sleep_s = 1.0  # ocupado por 1s, conferindo cancel_event
    fake_use_case.result = TranscribeVideoResult(
        job=Job.new(VideoId("dQw4w9WgXcQ"), 42),
        md_path=None,
        audio_path=None,
        diagnostics=(),
        canceled=True,
    )
    await adapter.handle_message(chat_id=10, user_id=42, text="https://youtu.be/dQw4w9WgXcQ")
    # Aguarda começar
    await asyncio.sleep(0.1)
    await adapter.handle_command_cancel(chat_id=10, user_id=42)
    await asyncio.sleep(0.5)
    # Mensagem de cancelamento foi disparada
    assert any("Cancelamento solicitado" in m.text for m in client.sent)


# --------------------------------------------------------------------
# Retry de envio
# --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_message_retries_on_transient_error(
    adapter: TelegramBotAdapter, client: FakeBotClient
) -> None:
    client.fail_send_count = 2  # primeiras 2 falham, terceira passa
    await adapter.handle_command_start(chat_id=1, user_id=42)
    # Mesmo com falhas iniciais, o texto deve aparecer na lista
    assert any("link do YouTube" in m.text for m in client.sent)


# --------------------------------------------------------------------
# JobPayload e VideoId
# --------------------------------------------------------------------


def test_job_payload_has_cancel_event() -> None:
    p = JobPayload(
        chat_id=1,
        user_id=2,
        url="https://youtu.be/aaaaaaaaaaa",
        video_id=VideoId("aaaaaaaaaaa"),
        progress_message_id=100,
    )
    assert isinstance(p.cancel_event, threading.Event)
    assert not p.cancel_event.is_set()


# --------------------------------------------------------------------
# Falhas no use case
# --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_use_case_failure_is_reported(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    fake_use_case: FakeUseCase,
) -> None:
    job = Job.new(VideoId("dQw4w9WgXcQ"), 42)
    job.transition_to(JobStatus.FAILED, error="fail")
    fake_use_case.result = TranscribeVideoResult(
        job=job,
        md_path=None,
        audio_path=None,
        diagnostics=(),
        failure_reason="boom",
    )
    await adapter.handle_message(chat_id=10, user_id=42, text="https://youtu.be/dQw4w9WgXcQ")
    await asyncio.sleep(0.2)
    assert any("Falhou" in e[2] or "boom" in e[2] for e in client.edits)


@pytest.mark.asyncio
async def test_use_case_exception_is_caught(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    fake_use_case: FakeUseCase,
) -> None:
    fake_use_case.raise_exc = RuntimeError("explosion")
    await adapter.handle_message(chat_id=10, user_id=42, text="https://youtu.be/dQw4w9WgXcQ")
    await asyncio.sleep(0.2)
    assert any("Erro inesperado" in e[2] for e in client.edits)


# --------------------------------------------------------------------
# Lifecycle
# --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lifecycle_start_stop(settings: AppSettings) -> None:
    a = TelegramBotAdapter(settings=settings, client=MagicMock(), use_case=MagicMock())
    await a.start()
    await a.stop()
    # Sem exceções → OK

# --------------------------------------------------------------------
# Queue commands / fallback
# --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_help_lists_queue_and_history_commands(
    adapter: TelegramBotAdapter, client: FakeBotClient
) -> None:
    await adapter.handle_command_help(chat_id=1, user_id=42)
    msg = client.sent[-1].text
    for command in [
        "/start",
        "/help",
        "/transcribe",
        "/pt",
        "/en",
        "/redo",
        "/status",
        "/queue",
        "/fila",
        "/clearqueue",
        "/cancelqueue",
        "/limparfila",
        "/cancel",
        "/cancelall",
        "/cancelartudo",
        "/list",
        "/last [n]",
        "/rename [n]",
        "/export json",
        "/export srt",
        "/export vtt",
        "/json [n]",
        "/srt [n]",
        "/vtt [n]",
        "/video_subs [n]",
        "/videosubs [n]",
        "/clearcache",
    ]:
        assert command in msg
    assert "→" in msg


@pytest.mark.asyncio
async def test_queue_command_via_text_fallback(
    adapter: TelegramBotAdapter, client: FakeBotClient
) -> None:
    await adapter.handle_message(chat_id=1, user_id=42, text="/queue")
    assert any("Fila de processamento" in m.text for m in client.sent)
    assert any("Fila vazia" in m.text for m in client.sent)


@pytest.mark.asyncio
async def test_cancelqueue_alias_clears_only_pending_items(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    fake_use_case: FakeUseCase,
) -> None:
    fake_use_case.sleep_s = 1.0
    fake_use_case.result = TranscribeVideoResult(
        job=Job.new(VideoId("aaaaaaaaaaa"), 42),
        md_path=None,
        audio_path=None,
        diagnostics=(),
        canceled=True,
    )
    await adapter.handle_message(chat_id=10, user_id=42, text="https://youtu.be/aaaaaaaaaaa")
    await asyncio.sleep(0.1)
    await adapter.handle_message(chat_id=10, user_id=42, text="https://youtu.be/bbbbbbbbbbb")
    await adapter.handle_message(chat_id=10, user_id=42, text="/cancelqueue")
    assert any("Fila limpa" in m.text and "1 job" in m.text for m in client.sent)


@pytest.mark.asyncio
async def test_duplicate_link_is_rejected_while_running(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    fake_use_case: FakeUseCase,
) -> None:
    fake_use_case.sleep_s = 1.0
    fake_use_case.result = TranscribeVideoResult(
        job=Job.new(VideoId("ccccccccccc"), 42),
        md_path=None,
        audio_path=None,
        diagnostics=(),
        canceled=True,
    )
    await adapter.handle_message(chat_id=10, user_id=42, text="https://youtu.be/ccccccccccc --lang pt")
    await asyncio.sleep(0.1)
    await adapter.handle_message(chat_id=10, user_id=42, text="https://youtu.be/ccccccccccc --lang pt")
    assert any("já está em processamento" in m.text for m in client.sent)


@pytest.mark.asyncio
async def test_cancel_final_success_message_is_sent(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    fake_use_case: FakeUseCase,
) -> None:
    fake_use_case.sleep_s = 1.0
    fake_use_case.result = TranscribeVideoResult(
        job=Job.new(VideoId("ddddddddddd"), 42),
        md_path=None,
        audio_path=None,
        diagnostics=(),
        canceled=True,
    )
    await adapter.handle_message(chat_id=10, user_id=42, text="https://youtu.be/ddddddddddd")
    await asyncio.sleep(0.1)
    await adapter.handle_command_cancel(chat_id=10, user_id=42)
    await asyncio.sleep(1.1)
    assert any("Job cancelado com sucesso" in m.text for m in client.sent)
