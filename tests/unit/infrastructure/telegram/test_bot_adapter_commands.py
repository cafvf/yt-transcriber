"""Testes dos novos handlers de Gate 6: /list, /last, /rename, /clearcache."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from yt_transcriber_bot.application.config import AppSettings
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
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
    TranscriptSnapshot,
    TranscriptSnapshotRepository,
)
from yt_transcriber_bot.infrastructure.rendering.markdown_renderer import (
    MarkdownTranscriptRenderer,
    RenderContext,
)
from yt_transcriber_bot.infrastructure.telegram.bot_adapter import (
    TelegramBotAdapter,
    _parse_rename_mapping,
)

# --------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------


class FakeBotClient:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []
        self.docs: list[Path] = []
        self.audios: list[Path] = []
        self.edits: list[tuple[int, int, str]] = []

    async def send_message(self, chat_id: int, text: str, reply_markup: object | None = None) -> int:
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
    return RenameSpeakersService(snapshots, MarkdownTranscriptRenderer())


@pytest.fixture
def client() -> FakeBotClient:
    return FakeBotClient()


@pytest.fixture
async def adapter(
    settings: AppSettings,
    client: FakeBotClient,
    repo: FakeRepo,
    rename_service: RenameSpeakersService,
    tmp_path: Path,
) -> TelegramBotAdapter:
    a = TelegramBotAdapter(
        settings=settings,
        client=client,  # type: ignore[arg-type]
        use_case=MagicMock(),
        repository=repo,  # type: ignore[arg-type]
        rename_service=rename_service,
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
    job.transition_to(JobStatus.COMPLETED)
    object.__setattr__(job, "updated_at", requested_at)
    job.md_path = str(md_path)
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
async def test_redo_enqueues_fresh_processing(settings: AppSettings, client: FakeBotClient) -> None:
    adapter = TelegramBotAdapter(
        settings=settings,
        client=client,  # type: ignore[arg-type]
        use_case=MagicMock(),
    )
    await adapter.handle_command_redo(
        chat_id=1,
        user_id=42,
        text="/redo https://youtu.be/dQw4w9WgXcQ",
    )
    assert any("Reprocessando" in text and "Enfileirando" in text for _, text, *_ in client.sent)


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
