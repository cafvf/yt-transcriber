"""Testes dos novos handlers de Gate 6: /list, /last, /rename, /clearcache."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.services.healthcheck import HealthCheckItem, HealthCheckReport
from yt_transcriber_bot.application.services.history_search import HistorySearchResult
from yt_transcriber_bot.application.services.last_error import LastErrorReport
from yt_transcriber_bot.application.services.rename_speakers import (
    RenameSpeakersService,
)
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.entities.transcript import (
    Transcript,
    TranscriptSegment,
)
from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.media_source import MediaSource
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.exporting.transcript_exporter import (
    TranscriptExportService,
)
from yt_transcriber_bot.infrastructure.exporting.video_subtitles_exporter import (
    VideoSubtitleExportError,
)
from yt_transcriber_bot.infrastructure.persistence.filesystem.canonical_markdown_writer import (
    FilesystemCanonicalMarkdownWriter,
)
from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
    TranscriptSnapshot,
    TranscriptSnapshotRepository,
)
from yt_transcriber_bot.infrastructure.rendering.markdown_renderer import (
    MarkdownTranscriptRenderer,
    RenderContext,
)
from yt_transcriber_bot.infrastructure.summarization.openai_compatible_client import (
    ChatCompletionError,
)
from yt_transcriber_bot.infrastructure.summarization.transcript_summarizer import SummaryProgress
from yt_transcriber_bot.infrastructure.telegram.bot_adapter import (
    TelegramBotAdapter,
    _parse_rename_mapping,
)
from yt_transcriber_bot.infrastructure.telegram.history import HistoryPresentation

# --------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------


class FakeBotClient:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []
        self.docs: list[Path] = []
        self.audios: list[Path] = []
        self.videos: list[tuple[Path, str | None]] = []
        self.edits: list[tuple[int, int, str]] = []

    async def send_message(
        self, chat_id: int, text: str, reply_markup: object | None = None
    ) -> int:
        self.sent.append((chat_id, text, reply_markup))
        return 100 + len(self.sent)

    async def edit_message(self, chat_id: int, message_id: int, text: str) -> None:
        self.edits.append((chat_id, message_id, text))

    async def send_document(
        self, chat_id: int, file_path: Path, caption: str | None = None
    ) -> None:
        self.docs.append(file_path)

    async def send_audio(self, chat_id: int, file_path: Path, caption: str | None = None) -> None:
        self.audios.append(file_path)

    async def send_video(self, chat_id: int, file_path: Path, caption: str | None = None) -> None:
        self.videos.append((file_path, caption))


class FakeSummaryService:
    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path
        self.calls: list[dict[str, object]] = []
        self.error: BaseException | None = None

    def summarize(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        on_progress = kwargs.get("on_progress")
        if callable(on_progress):
            on_progress(
                SummaryProgress(
                    kind="planned",
                    current=0,
                    total=2,
                    message="Transcrição preparada em 2 bloco(s).",
                )
            )
            on_progress(
                SummaryProgress(
                    kind="chunk_started",
                    current=1,
                    total=2,
                    message="Iniciando resumo parcial 1/2.",
                )
            )
            on_progress(
                SummaryProgress(
                    kind="chunk_completed",
                    current=1,
                    total=2,
                    message="Resumo parcial 1/2 concluído.",
                )
            )
            on_progress(
                SummaryProgress(
                    kind="synthesis_started",
                    current=2,
                    total=2,
                    message="Gerando síntese final.",
                )
            )
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text("# Resumo\n\nConteúdo resumido.")
        return type(
            "Result",
            (),
            {
                "path": self.output_path,
                "chunks": 1,
                "model": "qwen3.5-9b",
            },
        )()


class FakeVideoSubtitleExportService:
    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path
        self.calls: list[dict[str, object]] = []
        self.error: BaseException | None = None

    def export(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_bytes(b"fake-mp4")
        return type(
            "Result",
            (),
            {
                "path": self.output_path,
                "subtitle_path": self.output_path.with_suffix(".srt"),
                "source_video_path": self.output_path,
                "size_bytes": self.output_path.stat().st_size,
            },
        )()


class FakePlainTextExportService:
    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path
        self.calls: list[dict[str, object]] = []
        self.error: BaseException | None = None

    def export(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text("Título: texto\n\nSPEAKER_00: Conteúdo", encoding="utf-8")
        return type("Result", (), {"path": self.output_path})()


class FakeHealthCheckService:
    def run(self) -> HealthCheckReport:
        return HealthCheckReport(
            (
                HealthCheckItem("Configuração obrigatória", "ok", "segredos mínimos definidos."),
                HealthCheckItem("LM Studio", "ok", "modelo disponível."),
            )
        )


class FakeLastErrorService:
    def __init__(self) -> None:
        self.calls: list[int] = []
        self.recorded: list[dict[str, object]] = []

    def latest_for_user(self, user_id: int) -> LastErrorReport:
        self.calls.append(user_id)
        return LastErrorReport(
            job=None, message="✅ Nenhum erro recente registrado para este usuário."
        )

    def record_operation_error(self, **kwargs: object) -> object:
        self.recorded.append(kwargs)
        return object()


class FakeHistorySearchService:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str]] = []
        self.results: list[HistorySearchResult] = []

    def search(self, *, user_id: int, query: str) -> list[HistorySearchResult]:
        self.calls.append((user_id, query))
        return self.results


class FakeRepo:
    def __init__(self) -> None:
        self.jobs: list[Job] = []

    def save(self, job: Job) -> None:
        for i, j in enumerate(self.jobs):
            if j.job_id == job.job_id:
                self.jobs[i] = job
                return
        self.jobs.append(job)

    def get_by_id(self, job_id: str) -> Job | None:
        return next((j for j in self.jobs if j.job_id == job_id), None)

    def get_latest_by_video_id(self, video_id: VideoId) -> Job | None:
        matches = [j for j in self.jobs if j.video_id == video_id]
        return matches[-1] if matches else None

    def get_latest_completed_for_user(self, user_id: int) -> Job | None:
        matches = [
            j
            for j in self.jobs
            if j.requested_by_user_id == user_id and j.status == JobStatus.COMPLETED
        ]
        return matches[-1] if matches else None

    def list_recent_for_user(self, user_id: int, limit: int) -> list[Job]:
        return [j for j in self.jobs if j.requested_by_user_id == user_id][-limit:][::-1]

    def list_completed_oldest_first(self) -> list[Job]:
        return sorted(
            [j for j in self.jobs if j.status == JobStatus.COMPLETED],
            key=lambda j: j.requested_at,
        )

    def list_by_statuses_oldest_first(self, statuses: set[JobStatus]) -> list[Job]:
        return sorted(
            [j for j in self.jobs if j.status in statuses],
            key=lambda j: j.requested_at,
        )

    def delete(self, job_id: str) -> None:
        self.jobs = [j for j in self.jobs if j.job_id != job_id]


# --------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------


@pytest.fixture
def settings(tmp_path: Path) -> AppSettings:
    return AppSettings(
        telegram_bot_token="x",
        telegram_allowed_user_id=42,
        hf_token="x",
        data_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
        logs_dir=tmp_path / "logs",
    )


@pytest.fixture
def repo() -> FakeRepo:
    return FakeRepo()


@pytest.fixture
def snapshots(tmp_path: Path) -> TranscriptSnapshotRepository:
    return TranscriptSnapshotRepository(tmp_path / "segments")


@pytest.fixture
def rename_service(
    snapshots: TranscriptSnapshotRepository,
) -> RenameSpeakersService:
    return RenameSpeakersService(
        snapshots, MarkdownTranscriptRenderer(), FilesystemCanonicalMarkdownWriter()
    )


@pytest.fixture
def export_service(snapshots: TranscriptSnapshotRepository) -> TranscriptExportService:
    return TranscriptExportService(snapshots)


@pytest.fixture
def client() -> FakeBotClient:
    return FakeBotClient()


@pytest.fixture
def summary_service(tmp_path: Path) -> FakeSummaryService:
    return FakeSummaryService(tmp_path / "summaries" / "summary.md")


@pytest.fixture
def video_subtitle_service(tmp_path: Path) -> FakeVideoSubtitleExportService:
    return FakeVideoSubtitleExportService(tmp_path / "video_exports" / "video.mp4")


@pytest.fixture
def plain_text_export_service(tmp_path: Path) -> FakePlainTextExportService:
    return FakePlainTextExportService(tmp_path / "text_exports" / "transcript.txt")


@pytest.fixture
def healthcheck_service() -> FakeHealthCheckService:
    return FakeHealthCheckService()


@pytest.fixture
def lasterror_service() -> FakeLastErrorService:
    return FakeLastErrorService()


@pytest.fixture
def history_search_service() -> FakeHistorySearchService:
    return FakeHistorySearchService()


@pytest.fixture
async def adapter(
    settings: AppSettings,
    client: FakeBotClient,
    repo: FakeRepo,
    rename_service: RenameSpeakersService,
    export_service: TranscriptExportService,
    summary_service: FakeSummaryService,
    video_subtitle_service: FakeVideoSubtitleExportService,
    healthcheck_service: FakeHealthCheckService,
    lasterror_service: FakeLastErrorService,
    history_search_service: FakeHistorySearchService,
    tmp_path: Path,
) -> TelegramBotAdapter:
    a = TelegramBotAdapter(
        settings=settings,
        client=client,  # type: ignore[arg-type]
        use_case=MagicMock(),
        repository=repo,  # type: ignore[arg-type]
        rename_service=rename_service,
        export_service=export_service,
        summary_service=summary_service,  # type: ignore[arg-type]
        video_subtitle_export_service=video_subtitle_service,  # type: ignore[arg-type]
        healthcheck_service=healthcheck_service,  # type: ignore[arg-type]
        lasterror_service=lasterror_service,  # type: ignore[arg-type]
        history_search_service=history_search_service,  # type: ignore[arg-type]
        models_dir=tmp_path / "models",
    )
    await a.start()
    yield a  # type: ignore[misc]
    await a.stop()


def _make_completed_job(
    user_id: int,
    md_path: Path,
    requested_at: datetime,
    *,
    video_id: str = "dQw4w9WgXcQ",
) -> Job:
    job = Job.new(VideoId(video_id), user_id)
    object.__setattr__(job, "requested_at", requested_at)
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
    object.__setattr__(job, "updated_at", requested_at)
    job.md_path = str(md_path)
    job.canonical_transcript_ref = md_path.stem
    return job


def _populate_snapshot(snapshots: TranscriptSnapshotRepository, slug: str) -> None:
    snapshots.save(
        slug,
        TranscriptSnapshot(
            metadata=VideoMetadata(
                video_id=VideoId("dQw4w9WgXcQ"),
                title="Hello",
                channel="Ch",
                duration=Duration.from_seconds(60.0),
                upload_date=date(2024, 1, 1),
                original_language=Language("pt"),
            ),
            transcript=Transcript(
                segments=(
                    TranscriptSegment(0, 3, "Olá", "SPEAKER_00"),
                    TranscriptSegment(3, 6, "Tudo bem?", "SPEAKER_01"),
                ),
                language=Language("pt"),
                language_confidence=0.95,
            ),
            context=RenderContext(
                rendered_at=datetime(2026, 5, 1, tzinfo=UTC),
                whisper_model="small",
                diarization_model="pyannote/speaker-diarization-3.1",
                transcription_source="whisperx",
            ),
        ),
    )


# --------------------------------------------------------------------
# /list
# --------------------------------------------------------------------


def test_history_presentation_prefers_batch_titles_and_falls_back_to_slug(
    repo: FakeRepo, tmp_path: Path
) -> None:
    """Caracteriza o prefetch único para /list e o fallback textual legado."""

    class TitleProvider:
        def __init__(self) -> None:
            self.batch_calls: list[tuple[str, ...]] = []

        def metadata_for_many(self, slugs: tuple[str, ...]) -> dict[str, VideoMetadata]:
            self.batch_calls.append(slugs)
            return {
                "named": VideoMetadata(
                    video_id=VideoId("dQw4w9WgXcQ"),
                    title="Título do snapshot",
                    channel="Canal",
                    duration=Duration.from_seconds(1),
                    upload_date=None,
                    original_language=Language("pt"),
                )
            }

        def metadata_for(self, slug: str) -> VideoMetadata | None:
            raise AssertionError("o prefetch em lote não deve usar busca unitária")

    named = _make_completed_job(42, tmp_path / "named.md", datetime(2026, 5, 1, tzinfo=UTC))
    fallback = _make_completed_job(
        42,
        tmp_path / "fallback.md",
        datetime(2026, 5, 1, 1, 0, tzinfo=UTC),
        video_id="L9awVwLDH18",
    )
    repo.save(named)
    repo.save(fallback)
    provider = TitleProvider()
    history = HistoryPresentation(provider)
    jobs = [fallback, named]

    titles = history.prefetch_titles(jobs)

    assert provider.batch_calls == [("fallback", "named")]
    assert history.format_job(jobs[1], titles).startswith("Título do snapshot —")
    assert history.format_job(jobs[0], titles).startswith("fallback — L9awVwLDH18")


@pytest.mark.asyncio
async def test_list_empty(adapter: TelegramBotAdapter, client: FakeBotClient) -> None:
    await adapter.handle_command_list(chat_id=1, user_id=42)
    assert any("Nenhuma transcrição" in t for _, t, *_ in client.sent)


@pytest.mark.asyncio
async def test_list_shows_recent_jobs(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    tmp_path: Path,
) -> None:
    md = tmp_path / "x.md"
    md.write_text("# x")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, 12, 0, tzinfo=UTC)))
    await adapter.handle_command_list(chat_id=1, user_id=42)
    assert any("dQw4w9WgXcQ" in t for _, t, *_ in client.sent)


# --------------------------------------------------------------------
# /search
# --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_requires_query(adapter: TelegramBotAdapter, client: FakeBotClient) -> None:
    await adapter.handle_command_search(chat_id=1, user_id=42, text="/search")

    assert client.sent[-1][1] == "Uso: /search <texto>. Exemplo: /search privacidade."


@pytest.mark.asyncio
async def test_search_reports_no_results(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    history_search_service: FakeHistorySearchService,
) -> None:
    await adapter.handle_command_search(chat_id=1, user_id=42, text="/search inexistente")

    assert history_search_service.calls == [(42, "inexistente")]
    assert client.sent[-1][1] == "Nenhum resultado para “inexistente”."


@pytest.mark.asyncio
async def test_search_formats_current_history_index_and_sanitizes_delivery(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    history_search_service: FakeHistorySearchService,
    repo: FakeRepo,
    tmp_path: Path,
) -> None:
    older = _make_completed_job(42, tmp_path / "older.md", datetime(2026, 5, 1, 10, 0, tzinfo=UTC))
    newer = _make_completed_job(
        42,
        tmp_path / "newer.md",
        datetime(2026, 5, 1, 11, 0, tzinfo=UTC),
        video_id="L9awVwLDH18",
    )
    repo.save(older)
    repo.save(newer)
    history_search_service.results = [
        HistorySearchResult(
            job_id=older.job_id,
            title="Título\nprivado",
            video_id="dQw4w9WgXcQ",
            completed_at="2026-05-01 10:00",
            snippet="cookie=segredo privacidade encontrada",
        )
    ]

    await adapter.handle_message(chat_id=1, user_id=42, text="/search privacidade")

    assert history_search_service.calls == [(42, "privacidade")]
    message = client.sent[-1][1]
    assert "2. Título privado — dQw4w9WgXcQ — 2026-05-01 10:00" in message
    assert "cookie=[REDACTED]" in message


@pytest.mark.asyncio
async def test_search_telegram_result_uses_source_label_without_video_identity(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    history_search_service: FakeHistorySearchService,
    repo: FakeRepo,
    tmp_path: Path,
) -> None:
    telegram_job = _make_completed_job(
        42, tmp_path / "telegram.md", datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    )
    telegram_job.video_id = None
    telegram_job.media_source = MediaSource.telegram_audio("private-file-id")
    repo.save(telegram_job)
    history_search_service.results = [
        HistorySearchResult(
            job_id=telegram_job.job_id,
            title="Mensagem de voz",
            video_id=None,
            source_label="Telegram (mídia privada)",
            completed_at="2026-05-01 10:00",
            snippet="privacidade encontrada",
        )
    ]

    await adapter.handle_command_search(chat_id=1, user_id=42, text="/search privacidade")

    message = client.sent[-1][1]
    assert "Telegram (mídia privada)" in message
    assert "dQw4w9WgXcQ" not in message


@pytest.mark.asyncio
async def test_search_ignores_unauthorized_user(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    history_search_service: FakeHistorySearchService,
) -> None:
    await adapter.handle_command_search(chat_id=1, user_id=7, text="/search privacidade")

    assert history_search_service.calls == []
    assert client.sent == []


@pytest.mark.asyncio
async def test_list_prefers_batch_metadata_lookup_when_available(
    settings: AppSettings,
    client: FakeBotClient,
    repo: FakeRepo,
    export_service: TranscriptExportService,
    summary_service: FakeSummaryService,
    video_subtitle_service: FakeVideoSubtitleExportService,
    healthcheck_service: FakeHealthCheckService,
    lasterror_service: FakeLastErrorService,
    tmp_path: Path,
) -> None:
    class BatchAwareRenameService:
        def __init__(self) -> None:
            self.batch_calls: list[tuple[str, ...]] = []
            self.single_calls: list[str] = []

        def metadata_for_many(self, slugs: tuple[str, ...]) -> dict[str, VideoMetadata]:
            self.batch_calls.append(slugs)
            return {
                slug: VideoMetadata(
                    video_id=VideoId("dQw4w9WgXcQ"),
                    title=f"Título {slug}",
                    channel="Canal Exemplo",
                    duration=Duration.from_seconds(60),
                    upload_date=date(2024, 1, 1),
                    original_language=Language("pt"),
                )
                for slug in slugs
            }

        def metadata_for(self, slug: str) -> VideoMetadata | None:
            self.single_calls.append(slug)
            return None

    rename_service = BatchAwareRenameService()
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,  # type: ignore[arg-type]
        use_case=MagicMock(),
        repository=repo,  # type: ignore[arg-type]
        rename_service=rename_service,  # type: ignore[arg-type]
        export_service=export_service,
        summary_service=summary_service,  # type: ignore[arg-type]
        video_subtitle_export_service=video_subtitle_service,  # type: ignore[arg-type]
        healthcheck_service=healthcheck_service,  # type: ignore[arg-type]
        lasterror_service=lasterror_service,  # type: ignore[arg-type]
        models_dir=tmp_path / "models",
    )
    await adapter.start()
    try:
        first_md = tmp_path / "first-video.md"
        second_md = tmp_path / "second-video.md"
        first_md.write_text("# first")
        second_md.write_text("# second")
        repo.save(_make_completed_job(42, first_md, datetime(2026, 5, 1, 10, 0, tzinfo=UTC)))
        repo.save(_make_completed_job(42, second_md, datetime(2026, 5, 1, 11, 0, tzinfo=UTC)))

        await adapter.handle_command_list(chat_id=1, user_id=42)
    finally:
        await adapter.stop()

    assert rename_service.batch_calls == [("second-video", "first-video")]
    assert rename_service.single_calls == []
    text = client.sent[-1][1]
    assert "1. Título second-video" in text
    assert "2. Título first-video" in text


# --------------------------------------------------------------------
# /healthcheck e /lasterror
# --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_healthcheck_sends_report(adapter: TelegramBotAdapter, client: FakeBotClient) -> None:
    await adapter.handle_command_healthcheck(chat_id=1, user_id=42)

    assert any("Healthcheck" in text for _, text, *_ in client.sent)
    assert any("LM Studio" in text for _, text, *_ in client.sent)


@pytest.mark.asyncio
async def test_healthcheck_fallback_text_command(
    adapter: TelegramBotAdapter, client: FakeBotClient
) -> None:
    await adapter.handle_message(chat_id=1, user_id=42, text="/healthcheck")

    assert any("Healthcheck" in text for _, text, *_ in client.sent)


@pytest.mark.asyncio
async def test_lasterror_sends_latest_error_report(
    adapter: TelegramBotAdapter, client: FakeBotClient, lasterror_service: FakeLastErrorService
) -> None:
    await adapter.handle_command_lasterror(chat_id=1, user_id=42)

    assert lasterror_service.calls == [42]
    assert any("Nenhum erro recente" in text for _, text, *_ in client.sent)


@pytest.mark.asyncio
async def test_lasterror_fallback_text_command(
    adapter: TelegramBotAdapter, client: FakeBotClient
) -> None:
    await adapter.handle_message(chat_id=1, user_id=42, text="/lasterror")

    assert any("Nenhum erro recente" in text for _, text, *_ in client.sent)


# --------------------------------------------------------------------
# /last
# --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_last_empty(adapter: TelegramBotAdapter, client: FakeBotClient) -> None:
    await adapter.handle_command_last(chat_id=1, user_id=42)
    assert any("Sem transcrições" in t for _, t, *_ in client.sent)


@pytest.mark.asyncio
async def test_last_sends_md(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    tmp_path: Path,
) -> None:
    md = tmp_path / "hello.md"
    md.write_text("# hello")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))
    await adapter.handle_command_last(chat_id=1, user_id=42)
    assert md in client.docs


@pytest.mark.asyncio
async def test_last_when_md_file_missing(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    tmp_path: Path,
) -> None:
    md = tmp_path / "ghost.md"
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))
    await adapter.handle_command_last(chat_id=1, user_id=42)
    assert any("removido ou movido" in t for _, t, *_ in client.sent)


# --------------------------------------------------------------------
# /rename
# --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rename_when_no_jobs(adapter: TelegramBotAdapter, client: FakeBotClient) -> None:
    await adapter.handle_command_rename(chat_id=1, user_id=42)
    assert any("Sem transcrições concluídas" in t for _, t, *_ in client.sent)


@pytest.mark.asyncio
async def test_rename_full_flow(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    tmp_path: Path,
) -> None:
    md = tmp_path / "hello.md"
    md.write_text("# placeholder")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))
    _populate_snapshot(snapshots, "hello")

    # Início do diálogo
    await adapter.handle_command_rename(chat_id=1, user_id=42)
    assert any("Falantes detectados" in t for _, t, *_ in client.sent)

    # Envia o mapeamento como texto
    await adapter.handle_message(chat_id=1, user_id=42, text="SPEAKER_00=João, SPEAKER_01=Maria")
    # MD deve ser reenviado
    assert md in client.docs
    # Conteúdo regenerado
    new_content = md.read_text()
    assert "João" in new_content
    assert "Maria" in new_content
    # speaker_renames foi persistido
    job = repo.jobs[-1]
    assert job.speaker_renames == {"SPEAKER_00": "João", "SPEAKER_01": "Maria"}


@pytest.mark.asyncio
async def test_rename_invalid_input_keeps_dialog_open(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    tmp_path: Path,
) -> None:
    md = tmp_path / "hello.md"
    md.write_text("# x")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))
    _populate_snapshot(snapshots, "hello")

    await adapter.handle_command_rename(chat_id=1, user_id=42)
    await adapter.handle_message(chat_id=1, user_id=42, text="lixo qualquer")
    assert any("Formato inválido" in t for _, t, *_ in client.sent)


@pytest.mark.asyncio
async def test_rename_cancel_aborts_dialog(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    tmp_path: Path,
) -> None:
    md = tmp_path / "hello.md"
    md.write_text("# x")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))
    _populate_snapshot(snapshots, "hello")

    await adapter.handle_command_rename(chat_id=1, user_id=42)
    await adapter.handle_command_cancel(chat_id=1, user_id=42)
    assert any("Renomeação cancelada" in t for _, t, *_ in client.sent)


# --------------------------------------------------------------------
# /clearcache
# --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clearcache_removes_files(
    adapter: TelegramBotAdapter, client: FakeBotClient, tmp_path: Path
) -> None:
    models = tmp_path / "models"
    models.mkdir()
    (models / "model.bin").write_bytes(b"x" * 100)
    (models / "subdir").mkdir()
    (models / "subdir" / "weights.pt").write_bytes(b"y" * 200)
    await adapter.handle_command_clearcache(chat_id=1, user_id=42)
    assert any("Cache limpo" in t for _, t, *_ in client.sent)
    assert not (models / "model.bin").exists()
    assert not (models / "subdir" / "weights.pt").exists()


# --------------------------------------------------------------------
# _parse_rename_mapping (unitário puro)
# --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("SPEAKER_00=João", {"SPEAKER_00": "João"}),
        ("SPEAKER_00=João, SPEAKER_01=Maria", {"SPEAKER_00": "João", "SPEAKER_01": "Maria"}),
        ("SPEAKER_00=João\nSPEAKER_01=Maria", {"SPEAKER_00": "João", "SPEAKER_01": "Maria"}),
        ("  SPEAKER_00 = João  ", {"SPEAKER_00": "João"}),
        ("lixo", {}),
        ("", {}),
        ("SPEAKER_00=", {}),
        ("=João", {}),
        ("ABCD=foo", {}),  # não é SPEAKER_*
    ],
)
def test_parse_rename_mapping(text: str, expected: dict[str, str]) -> None:
    assert _parse_rename_mapping(text) == expected


# --------------------------------------------------------------------
# /redo
# --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redo_requires_link(settings: AppSettings, client: FakeBotClient) -> None:
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,  # type: ignore[arg-type]
        use_case=MagicMock(),
    )
    await adapter.handle_command_redo(chat_id=1, user_id=42, text="/redo")
    assert any("Uso: /redo" in text for _, text, *_ in client.sent)


@pytest.mark.asyncio
async def test_redo_enqueues_fresh_processing(
    settings: AppSettings,
    client: FakeBotClient,
    repo: FakeRepo,
) -> None:
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,  # type: ignore[arg-type]
        use_case=MagicMock(),
        repository=repo,  # type: ignore[arg-type]
    )
    await adapter.handle_command_redo(
        chat_id=1,
        user_id=42,
        text="/redo https://youtu.be/dQw4w9WgXcQ",
    )
    redo_messages = [text for _, text, *_ in client.sent if "Reprocessando" in text]
    assert redo_messages
    assert any("\n🌐 Idioma: automático\nEnfileirando…" in text for text in redo_messages)
    assert all("\\n" not in text for text in redo_messages)


@pytest.mark.asyncio
async def test_clearcache_refuses_unconfigured_directory(
    settings: AppSettings,
    client: FakeBotClient,
    tmp_path: Path,
) -> None:
    unsafe_dir = tmp_path / "not-the-configured-models-dir"
    unsafe_dir.mkdir()
    protected = unsafe_dir / "keep.bin"
    protected.write_bytes(b"x")
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,  # type: ignore[arg-type]
        use_case=MagicMock(),
        models_dir=unsafe_dir,
    )
    await adapter.handle_command_clearcache(chat_id=1, user_id=42)
    assert protected.exists()
    assert any("Operação recusada" in text for _, text, *_ in client.sent)


# --------------------------------------------------------------------
# Histórico numerado: /list, /last n e /rename n
# --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_numbers_completed_jobs_in_newest_first_order(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    tmp_path: Path,
) -> None:
    old_md = tmp_path / "old-video.md"
    new_md = tmp_path / "new-video.md"
    old_md.write_text("# old")
    new_md.write_text("# new")
    repo.save(
        _make_completed_job(
            42,
            old_md,
            datetime(2026, 5, 1, 10, 0, tzinfo=UTC),
            video_id="L9awVwLDH18",
        )
    )
    repo.save(
        _make_completed_job(
            42,
            new_md,
            datetime(2026, 5, 1, 11, 0, tzinfo=UTC),
            video_id="YFDp-smGYqQ",
        )
    )

    await adapter.handle_command_list(chat_id=1, user_id=42)

    text = client.sent[-1][1]
    assert "1. new-video" in text
    assert "2. old-video" in text
    assert text.index("1. new-video") < text.index("2. old-video")
    assert "/last n" in text
    assert "/rename n" in text


@pytest.mark.asyncio
async def test_last_with_index_sends_penultimate_completed_markdown(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    tmp_path: Path,
) -> None:
    old_md = tmp_path / "old-video.md"
    new_md = tmp_path / "new-video.md"
    old_md.write_text("# old")
    new_md.write_text("# new")
    repo.save(
        _make_completed_job(
            42,
            old_md,
            datetime(2026, 5, 1, 10, 0, tzinfo=UTC),
            video_id="L9awVwLDH18",
        )
    )
    repo.save(
        _make_completed_job(
            42,
            new_md,
            datetime(2026, 5, 1, 11, 0, tzinfo=UTC),
            video_id="YFDp-smGYqQ",
        )
    )

    await adapter.handle_command_last(chat_id=1, user_id=42, text="/last 2")

    assert old_md in client.docs
    assert new_md not in client.docs


@pytest.mark.asyncio
async def test_last_with_out_of_range_index_explains_to_use_list(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    tmp_path: Path,
) -> None:
    md = tmp_path / "only-video.md"
    md.write_text("# only")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))

    await adapter.handle_command_last(chat_id=1, user_id=42, text="/last 2")

    assert any("Use /list" in text for _, text, *_ in client.sent)
    assert client.docs == []


@pytest.mark.asyncio
async def test_rename_with_index_targets_penultimate_job_not_latest(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    tmp_path: Path,
) -> None:
    old_md = tmp_path / "old-video.md"
    new_md = tmp_path / "new-video.md"
    old_md.write_text("# old placeholder")
    new_md.write_text("# new placeholder")
    old_job = _make_completed_job(
        42,
        old_md,
        datetime(2026, 5, 1, 10, 0, tzinfo=UTC),
        video_id="L9awVwLDH18",
    )
    new_job = _make_completed_job(
        42,
        new_md,
        datetime(2026, 5, 1, 11, 0, tzinfo=UTC),
        video_id="YFDp-smGYqQ",
    )
    repo.save(old_job)
    repo.save(new_job)
    _populate_snapshot(snapshots, "old-video")
    _populate_snapshot(snapshots, "new-video")

    await adapter.handle_command_rename(chat_id=1, user_id=42, text="/rename 2")
    assert any("transcrição #2" in text and "Hello" in text for _, text, *_ in client.sent)

    await adapter.handle_message(chat_id=1, user_id=42, text="SPEAKER_00=João, SPEAKER_01=Maria")

    assert old_md in client.docs
    assert new_md not in client.docs
    assert "João" in old_md.read_text()
    assert new_md.read_text() == "# new placeholder"
    saved_old = repo.get_by_id(old_job.job_id)
    saved_new = repo.get_by_id(new_job.job_id)
    assert saved_old is not None
    assert saved_new is not None
    assert saved_old.speaker_renames == {"SPEAKER_00": "João", "SPEAKER_01": "Maria"}
    assert saved_new.speaker_renames == {}


@pytest.mark.asyncio
async def test_rename_with_out_of_range_index_does_not_open_dialog(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    tmp_path: Path,
) -> None:
    md = tmp_path / "only-video.md"
    md.write_text("# only")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))

    await adapter.handle_command_rename(chat_id=1, user_id=42, text="/rename 2")
    await adapter.handle_message(chat_id=1, user_id=42, text="SPEAKER_00=João")

    assert any("Use /list" in text for _, text, *_ in client.sent)
    assert any("link do YouTube" in text for _, text, *_ in client.sent)
    assert client.docs == []


# --------------------------------------------------------------------
# Interface regressions requested in 2026-05-03 review
# --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_prefers_video_title_from_snapshot(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    tmp_path: Path,
) -> None:
    md = tmp_path / "titled-video.md"
    md.write_text("# placeholder")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, 12, 30, tzinfo=UTC)))
    _populate_snapshot(snapshots, "titled-video")
    await adapter.handle_command_list(chat_id=1, user_id=42)
    msg = client.sent[-1][1]
    assert "Hello" in msg
    assert "executado em 2026-05-01 12:30" in msg


@pytest.mark.asyncio
async def test_list_falls_back_to_slug_when_snapshot_missing(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    tmp_path: Path,
) -> None:
    md = tmp_path / "fallback-video.md"
    md.write_text("# placeholder")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, 12, 30, tzinfo=UTC)))
    await adapter.handle_command_list(chat_id=1, user_id=42)
    msg = client.sent[-1][1]
    assert "fallback-video" in msg
    assert "executado em 2026-05-01 12:30" in msg


@pytest.mark.asyncio
async def test_rename_command_sends_inline_buttons(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    tmp_path: Path,
) -> None:
    md = tmp_path / "buttons.md"
    md.write_text("# placeholder")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))
    _populate_snapshot(snapshots, "buttons")
    await adapter.handle_command_rename(chat_id=1, user_id=42)
    _, text, reply_markup = client.sent[-1]
    assert "Toque em um falante" in text
    assert reply_markup is not None
    callbacks = [button.callback_data for row in reply_markup for button in row]
    assert "rename:speaker:SPEAKER_00" in callbacks
    assert "rename:merge" in callbacks
    assert "rename:done" in callbacks


@pytest.mark.asyncio
async def test_inline_button_rename_single_speaker(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    tmp_path: Path,
) -> None:
    md = tmp_path / "inline.md"
    md.write_text("# placeholder")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))
    _populate_snapshot(snapshots, "inline")
    await adapter.handle_command_rename(chat_id=1, user_id=42)
    await adapter.handle_callback_query(chat_id=1, user_id=42, data="rename:speaker:SPEAKER_00")
    assert any("Qual nome" in text for _, text, *_ in client.sent)
    await adapter.handle_message(chat_id=1, user_id=42, text="João")
    assert md in client.docs
    assert "João" in md.read_text()


@pytest.mark.asyncio
async def test_inline_button_rename_multiple_speakers_keeps_dialog_open(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    tmp_path: Path,
) -> None:
    md = tmp_path / "inline-multi.md"
    md.write_text("# placeholder")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))
    _populate_snapshot(snapshots, "inline-multi")

    await adapter.handle_command_rename(chat_id=1, user_id=42)
    await adapter.handle_callback_query(chat_id=1, user_id=42, data="rename:speaker:SPEAKER_00")
    await adapter.handle_message(chat_id=1, user_id=42, text="João")
    await adapter.handle_callback_query(chat_id=1, user_id=42, data="rename:speaker:SPEAKER_01")
    await adapter.handle_message(chat_id=1, user_id=42, text="Maria")

    assert md in client.docs
    content = md.read_text()
    assert "João" in content
    assert "Maria" in content
    saved = repo.jobs[-1]
    assert saved.speaker_renames == {"SPEAKER_00": "João", "SPEAKER_01": "Maria"}


@pytest.mark.asyncio
async def test_inline_button_rename_can_merge_multiple_speakers_by_same_name(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    tmp_path: Path,
) -> None:
    md = tmp_path / "inline-merge-two.md"
    md.write_text("# placeholder")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))
    _populate_snapshot(snapshots, "inline-merge-two")

    await adapter.handle_command_rename(chat_id=1, user_id=42)
    await adapter.handle_callback_query(chat_id=1, user_id=42, data="rename:speaker:SPEAKER_00")
    await adapter.handle_message(chat_id=1, user_id=42, text="Maria")
    await adapter.handle_callback_query(chat_id=1, user_id=42, data="rename:speaker:SPEAKER_01")
    await adapter.handle_message(chat_id=1, user_id=42, text="Maria")

    content = md.read_text()
    assert content.count("**Maria**") == 1
    assert "### [00:00:00 — 00:00:06] Maria" in content
    assert "Olá" in content
    assert "Tudo bem?" in content
    saved = repo.jobs[-1]
    assert saved.speaker_renames == {"SPEAKER_00": "Maria", "SPEAKER_01": "Maria"}


@pytest.mark.asyncio
async def test_inline_merge_button_guides_user(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    tmp_path: Path,
) -> None:
    md = tmp_path / "merge.md"
    md.write_text("# placeholder")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))
    _populate_snapshot(snapshots, "merge")
    await adapter.handle_command_rename(chat_id=1, user_id=42)
    await adapter.handle_callback_query(chat_id=1, user_id=42, data="rename:merge")
    assert any("mesclar falantes" in text for _, text, *_ in client.sent)


@pytest.mark.asyncio
async def test_inline_done_button_closes_rename_dialog(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    tmp_path: Path,
) -> None:
    md = tmp_path / "done.md"
    md.write_text("# placeholder")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))
    _populate_snapshot(snapshots, "done")
    await adapter.handle_command_rename(chat_id=1, user_id=42)
    await adapter.handle_callback_query(chat_id=1, user_id=42, data="rename:done")
    await adapter.handle_message(chat_id=1, user_id=42, text="João")
    assert any("Renomeação concluída" in text for _, text, *_ in client.sent)
    assert any("link do YouTube" in text for _, text, *_ in client.sent)


# --------------------------------------------------------------------
# /summary
# --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_latest_generates_and_sends_markdown(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    summary_service: FakeSummaryService,
    tmp_path: Path,
) -> None:
    md = tmp_path / "hello.md"
    md.write_text("# placeholder")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))
    _populate_snapshot(snapshots, "hello")

    await adapter.handle_command_summary(chat_id=1, user_id=42, text="/summary")

    assert summary_service.calls
    assert summary_service.calls[0]["slug"] == "hello"


@pytest.mark.asyncio
async def test_summary_accepts_telegram_media_without_video_id(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    summary_service: FakeSummaryService,
    tmp_path: Path,
) -> None:
    md = tmp_path / "telegram-summary.md"
    md.write_text("# placeholder")
    job = Job.new(
        None,
        user_id=42,
        media_source=MediaSource.telegram_audio("private-file-id"),
    )
    job.md_path = str(md)
    job.canonical_transcript_ref = "telegram-summary"
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
    repo.save(job)
    _populate_snapshot(snapshots, "telegram-summary")

    await adapter.handle_command_summary(chat_id=1, user_id=42, text="/summary")

    assert summary_service.calls[0]["slug"] == "telegram-summary"
    assert "apenas para transcrições do YouTube" not in client.sent[-1][1]
    assert "on_progress" in summary_service.calls[0]
    assert summary_service.output_path in client.docs
    assert any("Gerando resumo" in text for _, text, *_ in client.sent)
    assert any("Transcrição preparada" in text for *_, text in client.edits)
    assert any("Resumo gerado" in text for *_, text in client.edits)


@pytest.mark.asyncio
async def test_summary_index_selects_penultimate_job(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    summary_service: FakeSummaryService,
    tmp_path: Path,
) -> None:
    latest = tmp_path / "latest.md"
    previous = tmp_path / "previous.md"
    latest.write_text("# latest")
    previous.write_text("# previous")
    _populate_snapshot(snapshots, "latest")
    _populate_snapshot(snapshots, "previous")
    repo.save(_make_completed_job(42, previous, datetime(2026, 5, 1, 11, 0, tzinfo=UTC)))
    repo.save(_make_completed_job(42, latest, datetime(2026, 5, 1, 12, 0, tzinfo=UTC)))

    await adapter.handle_command_summary(chat_id=1, user_id=42, text="/summary 2")

    assert summary_service.calls[0]["slug"] == "previous"


@pytest.mark.asyncio
async def test_summary_unavailable_explains_configuration(
    settings: AppSettings, client: FakeBotClient, repo: FakeRepo
) -> None:
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,  # type: ignore[arg-type]
        use_case=MagicMock(),
        repository=repo,  # type: ignore[arg-type]
    )

    await adapter.handle_command_summary(chat_id=1, user_id=42, text="/summary")

    assert any("Sumarização indisponível" in text for _, text, *_ in client.sent)


@pytest.mark.asyncio
async def test_summary_fallback_text_command(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    summary_service: FakeSummaryService,
    tmp_path: Path,
) -> None:
    md = tmp_path / "fallback-summary.md"
    md.write_text("# placeholder")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))
    _populate_snapshot(snapshots, "fallback-summary")

    await adapter.handle_message(chat_id=1, user_id=42, text="/summary")

    assert summary_service.calls[0]["slug"] == "fallback-summary"
    assert summary_service.output_path in client.docs


# --------------------------------------------------------------------
# /export json|srt|vtt [n]
# --------------------------------------------------------------------


# --------------------------------------------------------------------
# /text [n]
# --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_text_latest_exports_snapshot_and_sends_reusable_document(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    plain_text_export_service: FakePlainTextExportService,
    tmp_path: Path,
) -> None:
    md = tmp_path / "latest.md"
    md.write_text("# placeholder")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))
    _populate_snapshot(snapshots, "latest")
    adapter._plain_text_export_service = plain_text_export_service  # type: ignore[attr-defined]

    await adapter.handle_command_text(chat_id=1, user_id=42, text="/text")  # type: ignore[attr-defined]

    assert plain_text_export_service.calls[0]["slug"] == "latest"
    assert plain_text_export_service.calls[0]["speaker_aliases"] == {}
    assert plain_text_export_service.output_path in client.docs
    assert any("texto" in text.lower() for _, text, *_ in client.sent)


@pytest.mark.asyncio
async def test_text_index_selects_penultimate_completed_job(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    plain_text_export_service: FakePlainTextExportService,
    tmp_path: Path,
) -> None:
    old_md = tmp_path / "old.md"
    new_md = tmp_path / "new.md"
    old_md.write_text("# old")
    new_md.write_text("# new")
    old_job = _make_completed_job(42, old_md, datetime(2026, 5, 1, 10, 0, tzinfo=UTC))
    old_job.speaker_renames = {"SPEAKER_00": "Maria"}
    repo.save(old_job)
    repo.save(_make_completed_job(42, new_md, datetime(2026, 5, 1, 11, 0, tzinfo=UTC)))
    adapter._plain_text_export_service = plain_text_export_service  # type: ignore[attr-defined]

    await adapter.handle_command_text(chat_id=1, user_id=42, text="/text 2")  # type: ignore[attr-defined]

    assert plain_text_export_service.calls[0]["slug"] == "old"
    assert plain_text_export_service.calls[0]["speaker_aliases"] == {"SPEAKER_00": "Maria"}
    assert plain_text_export_service.output_path in client.docs


@pytest.mark.asyncio
async def test_text_invalid_index_reuses_history_error(
    adapter: TelegramBotAdapter, client: FakeBotClient
) -> None:
    await adapter.handle_command_text(chat_id=1, user_id=42, text="/text 0")  # type: ignore[attr-defined]

    assert client.sent[-1][1] == "Use um número positivo. Exemplo: /last 2 ou /rename 2."


@pytest.mark.asyncio
async def test_text_missing_snapshot_is_sanitized_and_not_sent(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    plain_text_export_service: FakePlainTextExportService,
    tmp_path: Path,
) -> None:
    md = tmp_path / "expired.md"
    md.write_text("# expired")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))
    plain_text_export_service.error = FileNotFoundError("Snapshot inexistente: expired")
    adapter._plain_text_export_service = plain_text_export_service  # type: ignore[attr-defined]

    await adapter.handle_command_text(chat_id=1, user_id=42, text="/text")  # type: ignore[attr-defined]

    assert client.docs == []
    assert client.sent[-1][1] == "Snapshot dessa transcrição expirou. Reprocesse o vídeo."


@pytest.mark.asyncio
async def test_text_unavailable_and_unauthorized_do_not_export(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    plain_text_export_service: FakePlainTextExportService,
) -> None:
    await adapter.handle_command_text(chat_id=1, user_id=42, text="/text")  # type: ignore[attr-defined]
    assert client.sent[-1][1] == "Exportação de texto indisponível neste bot."

    adapter._plain_text_export_service = plain_text_export_service  # type: ignore[attr-defined]
    sent_before = list(client.sent)
    await adapter.handle_command_text(chat_id=1, user_id=7, text="/text")  # type: ignore[attr-defined]
    assert client.sent == sent_before
    assert plain_text_export_service.calls == []


@pytest.mark.asyncio
async def test_export_requires_format(adapter: TelegramBotAdapter, client: FakeBotClient) -> None:
    await adapter.handle_command_export(chat_id=1, user_id=42, text="/export")
    assert any("Uso: /export json|srt|vtt" in text for _, text, *_ in client.sent)


@pytest.mark.asyncio
async def test_export_invalid_format_shows_usage(
    adapter: TelegramBotAdapter, client: FakeBotClient
) -> None:
    await adapter.handle_command_export(chat_id=1, user_id=42, text="/export pdf")
    assert any("Uso: /export json|srt|vtt" in text for _, text, *_ in client.sent)


@pytest.mark.asyncio
async def test_export_srt_latest_generates_and_sends_file(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    tmp_path: Path,
) -> None:
    md = tmp_path / "hello.md"
    md.write_text("# placeholder")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))
    _populate_snapshot(snapshots, "hello")

    await adapter.handle_command_export(chat_id=1, user_id=42, text="/export srt")

    srt = tmp_path / "hello.srt"
    assert srt in client.docs
    assert "00:00:00,000 --> 00:00:03,000" in srt.read_text()
    assert any("Exportação SRT" in text for _, text, *_ in client.sent)


@pytest.mark.asyncio
async def test_export_json_with_index_uses_penultimate_and_speaker_aliases(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    tmp_path: Path,
) -> None:
    old_md = tmp_path / "old-video.md"
    new_md = tmp_path / "new-video.md"
    old_md.write_text("# old")
    new_md.write_text("# new")
    old_job = _make_completed_job(
        42,
        old_md,
        datetime(2026, 5, 1, 10, 0, tzinfo=UTC),
        video_id="L9awVwLDH18",
    )
    old_job.speaker_renames = {"SPEAKER_00": "Waldemar"}
    repo.save(old_job)
    repo.save(
        _make_completed_job(
            42,
            new_md,
            datetime(2026, 5, 1, 11, 0, tzinfo=UTC),
            video_id="YFDp-smGYqQ",
        )
    )
    _populate_snapshot(snapshots, "old-video")
    _populate_snapshot(snapshots, "new-video")

    await adapter.handle_command_export(chat_id=1, user_id=42, text="/export json 2")

    old_json = tmp_path / "old-video.json"
    new_json = tmp_path / "new-video.json"
    assert old_json in client.docs
    assert not new_json.exists()
    payload = json.loads(old_json.read_text())
    assert payload["transcript"]["segments"][0]["speaker"] == "Waldemar"


@pytest.mark.asyncio
async def test_export_with_out_of_range_index_explains_to_use_list(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    tmp_path: Path,
) -> None:
    md = tmp_path / "only-video.md"
    md.write_text("# only")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))

    await adapter.handle_command_export(chat_id=1, user_id=42, text="/export vtt 2")

    assert any("Use /list" in text for _, text, *_ in client.sent)
    assert client.docs == []


# --------------------------------------------------------------------
# /video_subs
# --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_video_subs_sends_soft_subtitled_mp4(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    video_subtitle_service: FakeVideoSubtitleExportService,
    tmp_path: Path,
) -> None:
    md = tmp_path / "video.md"
    md.write_text("# video")
    _populate_snapshot(snapshots, "video")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, 12, 0, tzinfo=UTC)))

    await adapter.handle_command_video_subs(chat_id=1, user_id=42, text="/video_subs")

    assert video_subtitle_service.calls
    assert video_subtitle_service.calls[0]["slug"] == "video"
    assert client.videos
    assert client.videos[0][0].name == "video.mp4"
    assert "legenda selecionável" in (client.videos[0][1] or "")


@pytest.mark.asyncio
async def test_video_subs_rejects_telegram_media_without_synthetic_video_id(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    video_subtitle_service: FakeVideoSubtitleExportService,
    tmp_path: Path,
) -> None:
    job = Job.new(
        None,
        user_id=42,
        media_source=MediaSource.telegram_audio("private-file-id"),
    )
    job.md_path = str(tmp_path / "telegram.md")
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
    repo.save(job)

    await adapter.handle_command_video_subs(chat_id=1, user_id=42, text="/video_subs")

    assert video_subtitle_service.calls == []
    assert "apenas para transcrições do YouTube" in client.sent[-1][1]


@pytest.mark.asyncio
async def test_video_subs_index_selects_penultimate_job(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    video_subtitle_service: FakeVideoSubtitleExportService,
    tmp_path: Path,
) -> None:
    latest = tmp_path / "latest.md"
    previous = tmp_path / "previous.md"
    latest.write_text("# latest")
    previous.write_text("# previous")
    _populate_snapshot(snapshots, "latest")
    _populate_snapshot(snapshots, "previous")
    repo.save(_make_completed_job(42, previous, datetime(2026, 5, 1, 11, 0, tzinfo=UTC)))
    repo.save(_make_completed_job(42, latest, datetime(2026, 5, 1, 12, 0, tzinfo=UTC)))

    await adapter.handle_command_video_subs(chat_id=1, user_id=42, text="/video_subs 2")

    assert video_subtitle_service.calls[0]["slug"] == "previous"


@pytest.mark.asyncio
async def test_summary_llm_failure_is_recorded_for_lasterror(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    summary_service: FakeSummaryService,
    lasterror_service: FakeLastErrorService,
    tmp_path: Path,
) -> None:
    md = tmp_path / "summary-fails.md"
    md.write_text("# placeholder")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))
    _populate_snapshot(snapshots, "summary-fails")
    summary_service.error = ChatCompletionError("LM Studio recusou conexão")

    await adapter.handle_command_summary(chat_id=1, user_id=42, text="/summary")

    assert any("Falha ao chamar a LLM" in text for _, text, *_ in client.sent)
    assert lasterror_service.recorded
    record = lasterror_service.recorded[-1]
    assert record["user_id"] == 42
    assert record["operation"] == "summary"
    assert record["stage"] == "llm"
    assert record["error"] is not None
    assert "LM Studio recusou conexão" in str(record["message"])
    assert record["context"]


@pytest.mark.asyncio
async def test_export_snapshot_failure_is_recorded_for_lasterror(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    lasterror_service: FakeLastErrorService,
    tmp_path: Path,
) -> None:
    md = tmp_path / "missing-snapshot.md"
    md.write_text("# placeholder")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))

    await adapter.handle_command_export(chat_id=1, user_id=42, text="/export srt")

    assert any("Snapshot dessa transcrição expirou" in text for _, text, *_ in client.sent)
    assert lasterror_service.recorded
    record = lasterror_service.recorded[-1]
    assert record["operation"] == "export"
    assert record["stage"] == "snapshot"
    assert record["error"] is not None
    assert record["context"]


@pytest.mark.asyncio
async def test_video_subs_failure_is_recorded_for_lasterror(
    adapter: TelegramBotAdapter,
    client: FakeBotClient,
    repo: FakeRepo,
    snapshots: TranscriptSnapshotRepository,
    video_subtitle_service: FakeVideoSubtitleExportService,
    lasterror_service: FakeLastErrorService,
    tmp_path: Path,
) -> None:
    md = tmp_path / "video-fails.md"
    md.write_text("# placeholder")
    _populate_snapshot(snapshots, "video-fails")
    repo.save(_make_completed_job(42, md, datetime(2026, 5, 1, tzinfo=UTC)))
    video_subtitle_service.error = VideoSubtitleExportError("ffmpeg falhou")

    await adapter.handle_command_video_subs(chat_id=1, user_id=42, text="/video_subs")

    assert any("Falha ao gerar vídeo legendado" in text for _, text, *_ in client.sent)
    assert lasterror_service.recorded
    record = lasterror_service.recorded[-1]
    assert record["operation"] == "video_subs"
    assert record["stage"] == "ffmpeg"
    assert record["error"] is not None
    assert "ffmpeg falhou" in str(record["message"])
