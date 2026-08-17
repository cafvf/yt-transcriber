"""Testes do TelegramBotAdapter — sem usar a API real do Telegram."""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.job_request_context import JobRequestContext
from yt_transcriber_bot.application.services.startup_recovery import RecoveredPendingJob
from yt_transcriber_bot.application.use_cases.transcribe_video import (
    TranscribeVideoResult,
)
from yt_transcriber_bot.application.workflows.execution_queue import QueuedItem
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.media_source import MediaSource
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.persistence.sqlalchemy.job_repository import (
    SqlAlchemyJobRepository,
)
from yt_transcriber_bot.infrastructure.summarization.openai_compatible_client import (
    ChatCompletionError,
)
from yt_transcriber_bot.infrastructure.telegram.bot_adapter import (
    JobPayload,
    TelegramBotAdapter,
    _make_editor,
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
        self.fail_documents = False

    async def send_message(
        self, chat_id: int, text: str, reply_markup: object | None = None
    ) -> int:
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
        if self.fail_documents:
            raise RuntimeError("document delivery failed")
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
                time.sleep(0.01)
        if self.raise_exc is not None:
            raise self.raise_exc
        assert self.result is not None
        if self.result.canceled or self.result.failure_reason is not None:
            return self.result
        job.md_path = str(self.result.md_path) if self.result.md_path is not None else None
        job.audio_path = str(self.result.audio_path) if self.result.audio_path is not None else None
        job.canonical_transcript_ref = job.job_id
        for status in (
            JobStatus.CONVERTING,
            JobStatus.TRANSCRIBING,
            JobStatus.DIARIZING,
            JobStatus.RENDERING,
            JobStatus.DELIVERING,
        ):
            job.transition_to(status)
        return TranscribeVideoResult(
            job=job,
            md_path=self.result.md_path,
            audio_path=self.result.audio_path,
            diagnostics=self.result.diagnostics,
        )


class CapturingUseCase:
    def __init__(self, *, md_path: Path | None = None, audio_path: Path | None = None) -> None:
        self.md_path = md_path
        self.audio_path = audio_path
        self.started = threading.Event()
        self.cancel_seen = threading.Event()
        self.last_cancel_event: threading.Event | None = None

    def execute(self, job: Job, **kwargs: Any) -> TranscribeVideoResult:
        self.last_cancel_event = kwargs["cancel_event"]
        self.started.set()
        if self.md_path is None and self.audio_path is None:
            for _ in range(100):
                if self.last_cancel_event.is_set():
                    self.cancel_seen.set()
                    return TranscribeVideoResult(
                        job=job,
                        md_path=None,
                        audio_path=None,
                        diagnostics=(),
                        canceled=True,
                    )
                time.sleep(0.01)
        job.md_path = str(self.md_path) if self.md_path is not None else None
        job.audio_path = str(self.audio_path) if self.audio_path is not None else None
        job.canonical_transcript_ref = job.job_id
        for status in (
            JobStatus.CONVERTING,
            JobStatus.TRANSCRIBING,
            JobStatus.DIARIZING,
            JobStatus.RENDERING,
            JobStatus.DELIVERING,
        ):
            job.transition_to(status)
        return TranscribeVideoResult(
            job=job,
            md_path=self.md_path,
            audio_path=self.audio_path,
            diagnostics=(),
        )


class FakeRepo:
    def __init__(self) -> None:
        self.jobs: list[Job] = []
        self.contexts: dict[str, JobRequestContext] = {}

    def save(self, job: Job) -> None:
        for index, existing in enumerate(self.jobs):
            if existing.job_id == job.job_id:
                self.jobs[index] = job
                return
        self.jobs.append(job)

    def get_by_id(self, job_id: str) -> Job | None:
        return next((job for job in self.jobs if job.job_id == job_id), None)

    def get_latest_by_video_id(self, video_id: VideoId) -> Job | None:
        return next((job for job in reversed(self.jobs) if job.video_id == video_id), None)

    def get_latest_completed_for_user(self, user_id: int) -> Job | None:
        return next(
            (
                job
                for job in reversed(self.jobs)
                if job.requested_by_user_id == user_id and job.status == JobStatus.COMPLETED
            ),
            None,
        )

    def list_recent_for_user(self, user_id: int, limit: int) -> list[Job]:
        return [job for job in reversed(self.jobs) if job.requested_by_user_id == user_id][:limit]

    def list_completed_oldest_first(self) -> list[Job]:
        return [job for job in self.jobs if job.status == JobStatus.COMPLETED]

    def list_by_statuses_oldest_first(self, statuses: set[JobStatus]) -> list[Job]:
        return [job for job in self.jobs if job.status in statuses]

    def delete(self, job_id: str) -> None:
        self.jobs = [job for job in self.jobs if job.job_id != job_id]

    def save_request_context(self, context: JobRequestContext) -> None:
        self.contexts[context.job_id] = context

    def get_request_context(self, job_id: str) -> JobRequestContext | None:
        return self.contexts.get(job_id)


class FakeLastErrorService:
    def __init__(self) -> None:
        self.recorded: list[dict[str, object]] = []

    def record_operation_error(self, **kwargs: object) -> object:
        self.recorded.append(kwargs)
        return object()


class FakeOperationalWorkflow:
    def __init__(self, sink: FakeLastErrorService | None = None) -> None:
        self.sink = sink or FakeLastErrorService()

    def record_error(self, **kwargs: object) -> object:
        return self.sink.record_operation_error(**kwargs)

    def apply_retention(self) -> object:
        return type("Retention", (), {"expired_jobs": (), "removed_files": ()})()


class FailingSaveRepo(FakeRepo):
    def save(self, job: Job) -> None:
        raise OSError("database password=do-not-expose")


@dataclass
class RecordingAuditLogger:
    events: list[tuple[str, dict[str, object]]] = field(default_factory=list)

    def record(self, event: str, **fields: object) -> None:
        self.events.append((event, fields))


class ActiveStateUseCase:
    def __init__(self) -> None:
        self.observed_status: JobStatus | None = None

    def execute(self, job: Job, **_kwargs: object) -> TranscribeVideoResult:
        self.observed_status = job.status
        return TranscribeVideoResult(
            job=job, md_path=None, audio_path=None, diagnostics=(), canceled=True
        )


class FailingSummaryService:
    def __init__(self, exc: BaseException) -> None:
        self.exc = exc

    def summarize(self, **_kwargs: object) -> object:
        raise self.exc


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
    a = TelegramBotAdapter(
        settings=settings,
        client=client,
        use_case=fake_use_case,  # type: ignore[arg-type]
        repository=FakeRepo(),  # type: ignore[arg-type]
    )
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


@pytest.mark.asyncio
async def test_send_text_sanitizes_secrets_and_prompt_fragments(
    adapter: TelegramBotAdapter, client: FakeBotClient
) -> None:
    await adapter._send_text(
        10,
        (
            "Authorization: Bearer bearer-token-123 "
            'payload={"prompt":"secret prompt","content":"transcript body"} '
            "api_key=sk-live-secret123456"
        ),
    )

    message = client.sent[-1].text
    assert "bearer-token-123" not in message
    assert "secret prompt" not in message
    assert "transcript body" not in message
    assert "sk-live-secret123456" not in message
    assert "[REDACTED]" in message


@pytest.mark.asyncio
async def test_progress_editor_sanitizes_message_edits(
    settings: AppSettings, client: FakeBotClient
) -> None:
    editor = _make_editor(client, 10, 200, settings=settings)

    await editor('messages=[{"role":"user","content":"raw prompt"}] Cookie: SID=abc')

    _, _, text = client.edits[-1]
    assert "raw prompt" not in text
    assert "SID=abc" not in text
    assert "[REDACTED]" in text


@pytest.mark.asyncio
async def test_summary_llm_error_does_not_send_backend_body_to_telegram(
    settings: AppSettings,
    client: FakeBotClient,
    tmp_path: Path,
) -> None:
    md = tmp_path / "video.md"
    md.write_text("# transcript", encoding="utf-8")
    job = Job.new(VideoId("dQw4w9WgXcQ"), 42)
    job.md_path = str(md)
    job.canonical_transcript_ref = "video"
    for status in (
        JobStatus.ACQUIRING,
        JobStatus.CONVERTING,
        JobStatus.TRANSCRIBING,
        JobStatus.DIARIZING,
        JobStatus.RENDERING,
        JobStatus.DELIVERING,
        JobStatus.COMPLETED,
    ):
        job.transition_to(status)
    repo = FakeRepo()
    repo.save(job)
    lasterror = FakeLastErrorService()
    backend_error = ChatCompletionError(
        'HTTP 500 body={"messages":[{"role":"user","content":"raw prompt fragment"}],'
        '"Authorization":"Bearer backend-token","prompt":"full transcript prompt"}'
    )
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,
        use_case=MagicMock(),
        repository=repo,  # type: ignore[arg-type]
        summary_workflow=FailingSummaryService(backend_error),  # type: ignore[arg-type]
        operational_workflow=FakeOperationalWorkflow(lasterror),  # type: ignore[arg-type]
    )

    await adapter.handle_command_summary(chat_id=10, user_id=42, text="/summary 1")

    telegram_text = "\n".join(message.text for message in client.sent)
    assert "raw prompt fragment" not in telegram_text
    assert "backend-token" not in telegram_text
    assert "full transcript prompt" not in telegram_text
    assert "Detalhes técnicos sanitizados" in telegram_text
    assert lasterror.recorded[-1]["stage"] == "llm"


@pytest.mark.asyncio
async def test_unexpected_pipeline_error_does_not_edit_raw_body_to_telegram(
    settings: AppSettings,
    client: FakeBotClient,
) -> None:
    repo = FakeRepo()
    use_case = FakeUseCase(
        raise_exc=RuntimeError(
            'backend failed response_body={"messages":[{"role":"user",'
            '"content":"raw transcript body"}],"Authorization":"Bearer backend-token"}'
        )
    )
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,
        use_case=use_case,  # type: ignore[arg-type]
        repository=repo,  # type: ignore[arg-type]
        operational_workflow=FakeOperationalWorkflow(),  # type: ignore[arg-type]
    )
    await adapter.start()
    try:
        await adapter.handle_message(chat_id=10, user_id=42, text="https://youtu.be/dQw4w9WgXcQ")
        await asyncio.wait_for(adapter._queue._queue.join(), timeout=1.0)
    finally:
        await adapter.stop()

    telegram_text = "\n".join(text for _, _, text in client.edits)
    assert "raw transcript body" not in telegram_text
    assert "backend-token" not in telegram_text
    assert "Erro inesperado no pipeline" in telegram_text


@pytest.mark.asyncio
async def test_pipeline_exception_does_not_expose_arbitrary_text_in_audit_or_telegram(
    settings: AppSettings, client: FakeBotClient
) -> None:
    repo = FakeRepo()
    audit = RecordingAuditLogger()
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,
        use_case=FakeUseCase(raise_exc=RuntimeError("arbitrary internal customer transcript")),
        repository=repo,  # type: ignore[arg-type]
        audit_logger=audit,  # type: ignore[arg-type]
    )
    job = Job.new(VideoId("dQw4w9WgXcQ"), 42)
    repo.save(job)

    await adapter._process_job(
        QueuedItem(
            payload=JobPayload(
                job.job_id, 10, 42, "https://youtu.be/dQw4w9WgXcQ", job.video_id, 100
            ),
            item_id=job.job_id,
        )
    )

    exposed = "\n".join(message.text for message in client.sent) + repr(audit.events)
    assert "arbitrary internal customer transcript" not in exposed


@pytest.mark.asyncio
async def test_pipeline_exception_marks_persisted_downloading_job_failed(
    settings: AppSettings, client: FakeBotClient
) -> None:
    repo = FakeRepo()
    job = Job.new(VideoId("dQw4w9WgXcQ"), 42)
    repo.save(job)
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,
        use_case=FakeUseCase(raise_exc=RuntimeError("backend-token")),
        repository=repo,  # type: ignore[arg-type]
    )

    await adapter._process_job(
        QueuedItem(
            payload=JobPayload(
                job.job_id, 10, 42, "https://youtu.be/dQw4w9WgXcQ", job.video_id, 100
            ),
            item_id=job.job_id,
        )
    )

    stored = repo.get_by_id(job.job_id)
    assert stored is not None
    assert stored.status is JobStatus.FAILED
    assert stored.error_message == "Erro inesperado no pipeline: RuntimeError"


@pytest.mark.asyncio
async def test_job_is_persisted_as_active_before_pipeline_execution(
    settings: AppSettings, client: FakeBotClient
) -> None:
    repo = FakeRepo()
    use_case = ActiveStateUseCase()
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,
        use_case=use_case,
        repository=repo,  # type: ignore[arg-type]
    )
    job = Job.new(VideoId("dQw4w9WgXcQ"), 42)
    repo.save(job)

    await adapter._process_job(
        QueuedItem(
            payload=JobPayload(
                job.job_id, 10, 42, "https://youtu.be/dQw4w9WgXcQ", job.video_id, 100
            ),
            item_id=job.job_id,
        )
    )

    assert use_case.observed_status is JobStatus.ACQUIRING


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


@pytest.mark.asyncio
async def test_url_enqueue_requires_repository(
    settings: AppSettings, client: FakeBotClient
) -> None:
    adapter = TelegramBotAdapter(settings=settings, client=client, use_case=FakeUseCase())  # type: ignore[arg-type]

    await adapter.handle_message(chat_id=10, user_id=42, text="https://youtu.be/dQw4w9WgXcQ")

    current, pending = adapter._queue.snapshot()
    assert current is None
    assert pending == ()
    assert any("indisponível" in message.text for message in client.sent)


@pytest.mark.asyncio
async def test_successful_delivery_marks_delivering_job_completed(
    settings: AppSettings,
    client: FakeBotClient,
    tmp_path: Path,
) -> None:
    md = tmp_path / "transcript.md"
    md.write_text("# ok")
    repo = FakeRepo()
    use_case = CapturingUseCase(md_path=md)
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,
        use_case=use_case,  # type: ignore[arg-type]
        repository=repo,  # type: ignore[arg-type]
    )
    await adapter.start()
    try:
        await adapter.handle_message(chat_id=10, user_id=42, text="https://youtu.be/dQw4w9WgXcQ")
        await asyncio.wait_for(adapter._queue._queue.join(), timeout=1.0)
    finally:
        await adapter.stop()

    assert len(repo.jobs) == 1
    assert repo.jobs[0].status == JobStatus.COMPLETED
    assert any(d.path == md for d in client.docs)


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


@pytest.mark.asyncio
async def test_cancelall_signals_active_use_case_cancel_event(
    settings: AppSettings, client: FakeBotClient
) -> None:
    use_case = CapturingUseCase()
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,
        use_case=use_case,  # type: ignore[arg-type]
        repository=FakeRepo(),  # type: ignore[arg-type]
    )
    await adapter.start()
    try:
        await adapter.handle_message(chat_id=10, user_id=42, text="https://youtu.be/dQw4w9WgXcQ")
        assert await asyncio.to_thread(use_case.started.wait, 1.0)

        await adapter.handle_command_cancelall(chat_id=10, user_id=42)
        assert await asyncio.to_thread(use_case.cancel_seen.wait, 1.0)

        assert use_case.last_cancel_event is not None
        assert use_case.last_cancel_event.is_set()
        assert any("Cancelamento geral solicitado" in m.text for m in client.sent)
    finally:
        await adapter.stop()


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


def test_job_payload_does_not_own_cancellation_token() -> None:
    p = JobPayload(
        job_id=None,
        chat_id=1,
        user_id=2,
        url="https://youtu.be/aaaaaaaaaaa",
        video_id=VideoId("aaaaaaaaaaa"),
        progress_message_id=100,
    )
    assert not hasattr(p, "cancel_event")


@pytest.mark.asyncio
async def test_recovery_requeues_telegram_media_without_exposing_staging_path(
    settings: AppSettings, client: FakeBotClient, tmp_path: Path
) -> None:
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,
        use_case=CapturingUseCase(md_path=tmp_path / "recovered.md"),
    )
    job = Job.new(
        None,
        user_id=42,
        media_source=MediaSource.telegram_audio("private-file-id"),
        source_title="Mensagem de voz",
        source_duration_seconds=37,
        requested_language="pt",
    )
    request_context = JobRequestContext(
        job.job_id, delivery_chat_id=10, source_locator="/private/staging/private-file-id.ogg"
    )
    adapter._save_request_context_if_possible(request_context)

    await adapter._requeue_recovered_job(RecoveredPendingJob(job, request_context))

    _, pending = adapter._queue.snapshot()
    assert len(pending) == 1
    payload = pending[0].payload
    assert payload.media_source == job.media_source
    assert payload.source_title == "Mensagem de voz"
    assert payload.source_duration_seconds == 37
    await adapter._process_job(pending[0])

    visible = "\n".join(
        [message.text for message in client.sent] + [text for _, _, text in client.edits]
    )
    assert "Áudio privado do Telegram" in visible
    assert "Áudio privado do Telegram — idioma informado: pt" in visible
    assert "private-file-id" not in visible
    assert "/private/staging" not in visible


@pytest.mark.asyncio
@pytest.mark.integration
async def test_start_recovers_pending_job_from_sqlite_file(
    settings: AppSettings, client: FakeBotClient, tmp_path: Path
) -> None:
    repo = SqlAlchemyJobRepository.from_url(f"sqlite:///{tmp_path / 'jobs.db'}")
    pending = Job.new(
        VideoId("dQw4w9WgXcQ"),
        user_id=42,
        config_signature="sig",
        requested_language="pt",
    )
    repo.save(pending)
    repo.save_request_context(JobRequestContext(pending.job_id, 10, "https://youtu.be/dQw4w9WgXcQ"))
    use_case = CapturingUseCase(md_path=tmp_path / "recovered.md")
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,
        use_case=use_case,  # type: ignore[arg-type]
        repository=repo,
    )

    try:
        await adapter.start()
        assert await asyncio.to_thread(use_case.started.wait, 1.0)
        await asyncio.wait_for(adapter._queue._queue.join(), timeout=1.0)
    finally:
        await adapter.stop()

    assert any("Retomando job pendente" in message.text for message in client.sent)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_start_marks_interrupted_jobs_from_sqlite_file_and_notifies(
    settings: AppSettings, client: FakeBotClient, tmp_path: Path
) -> None:
    repo = SqlAlchemyJobRepository.from_url(f"sqlite:///{tmp_path / 'jobs.db'}")
    active = Job.new(
        VideoId("dQw4w9WgXcQ"),
        user_id=42,
        config_signature="sig",
    )
    for status in (
        JobStatus.ACQUIRING,
        JobStatus.CONVERTING,
        JobStatus.TRANSCRIBING,
    ):
        active.transition_to(status)
    repo.save(active)
    repo.save_request_context(JobRequestContext(active.job_id, 10, "https://youtu.be/dQw4w9WgXcQ"))
    delivering = Job.new(
        VideoId("aaaaaaaaaaa"),
        user_id=42,
        config_signature="sig",
    )
    for status in (
        JobStatus.ACQUIRING,
        JobStatus.CONVERTING,
        JobStatus.TRANSCRIBING,
        JobStatus.DIARIZING,
        JobStatus.RENDERING,
        JobStatus.DELIVERING,
    ):
        delivering.transition_to(status)
    delivering.md_path = "/tmp/out.md"
    repo.save(delivering)
    repo.save_request_context(
        JobRequestContext(delivering.job_id, 10, "https://youtu.be/aaaaaaaaaaa")
    )
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,
        use_case=FakeUseCase(result=None),  # type: ignore[arg-type]
        repository=repo,
    )

    await adapter.start()
    await adapter.stop()

    repaired_active = repo.get_by_id(active.job_id)
    repaired_delivering = repo.get_by_id(delivering.job_id)
    assert repaired_active is not None
    assert repaired_active.status is JobStatus.FAILED
    assert repaired_delivering is not None
    assert repaired_delivering.status is JobStatus.DELIVERY_FAILED
    assert any("interrompeu um job em andamento" in message.text for message in client.sent)
    assert any("delivery_failed" in message.text for message in client.sent)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_startup_recovery_runs_only_once_per_adapter_instance(
    settings: AppSettings, client: FakeBotClient, tmp_path: Path
) -> None:
    repo = SqlAlchemyJobRepository.from_url(f"sqlite:///{tmp_path / 'jobs.db'}")
    pending = Job.new(
        VideoId("dQw4w9WgXcQ"),
        user_id=42,
        config_signature="sig",
    )
    repo.save(pending)
    repo.save_request_context(JobRequestContext(pending.job_id, 10, "https://youtu.be/dQw4w9WgXcQ"))
    use_case = CapturingUseCase(md_path=tmp_path / "recovered.md")
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,
        use_case=use_case,  # type: ignore[arg-type]
        repository=repo,
    )

    try:
        await adapter.start()
        await adapter.start()
        await asyncio.wait_for(adapter._queue._queue.join(), timeout=1.0)
    finally:
        await adapter.stop()

    recovery_messages = [m for m in client.sent if "Retomando job pendente" in m.text]
    assert len(recovery_messages) == 1


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


@pytest.mark.asyncio
async def test_delivery_failure_marks_job_failed_and_preserves_artifact_paths(
    settings: AppSettings,
    client: FakeBotClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import yt_transcriber_bot.infrastructure.telegram.bot_adapter as bot_adapter_module

    async def no_retry(operation: Any) -> Any:
        try:
            return await operation()
        except Exception as exc:
            raise bot_adapter_module.TelegramSendError("send failed") from exc

    md = tmp_path / "transcript.md"
    md.write_text("# transcript")
    repo = FakeRepo()
    lasterror = FakeLastErrorService()
    use_case = CapturingUseCase(md_path=md)
    client.fail_documents = True
    monkeypatch.setattr(bot_adapter_module, "send_with_retry", no_retry)
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,
        use_case=use_case,  # type: ignore[arg-type]
        repository=repo,  # type: ignore[arg-type]
        operational_workflow=FakeOperationalWorkflow(lasterror),  # type: ignore[arg-type]
    )
    await adapter.start()
    try:
        await adapter.handle_message(chat_id=10, user_id=42, text="https://youtu.be/dQw4w9WgXcQ")
        await asyncio.wait_for(adapter._queue._queue.join(), timeout=1.0)
    finally:
        await adapter.stop()

    assert len(repo.jobs) == 1
    job = repo.jobs[0]
    assert job.status == JobStatus.DELIVERY_FAILED
    assert job.md_path == str(md)
    assert Path(job.md_path).read_text() == "# transcript"
    assert "entrega" in (job.error_message or "").lower()
    assert lasterror.recorded
    record = lasterror.recorded[-1]
    assert record["operation"] == "transcribe_delivery"
    assert record["stage"] == "delivery"
    assert record["context"] == {
        "job_id": job.job_id,
        "video_id": "dQw4w9WgXcQ",
        "md_path": str(md),
    }


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
        "/healthcheck",
        "/lasterror",
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
    await adapter.handle_message(
        chat_id=10, user_id=42, text="https://youtu.be/ccccccccccc --lang pt"
    )
    await asyncio.sleep(0.1)
    await adapter.handle_message(
        chat_id=10, user_id=42, text="https://youtu.be/ccccccccccc --lang pt"
    )
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
