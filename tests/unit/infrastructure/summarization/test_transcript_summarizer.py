from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from yt_transcriber_bot.domain.entities.transcript import Transcript, TranscriptSegment
from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
    TranscriptSnapshot,
    TranscriptSnapshotRepository,
)
from yt_transcriber_bot.infrastructure.rendering.markdown_renderer import RenderContext
from yt_transcriber_bot.infrastructure.summarization.openai_compatible_client import (
    ChatCompletionRequest,
    ChatCompletionTimeoutError,
)
from yt_transcriber_bot.infrastructure.summarization.transcript_summarizer import (
    SummaryProgress,
    TranscriptSummaryService,
)


class FakeChatClient:
    model = "qwen3.5-9b"

    def __init__(self, responses: list[str | BaseException] | None = None) -> None:
        self.requests: list[ChatCompletionRequest] = []
        self._responses = responses or ["## Resumo executivo\nResumo final."]

    def complete(self, request: ChatCompletionRequest) -> str:
        self.requests.append(request)
        if len(self.requests) <= len(self._responses):
            response = self._responses[len(self.requests) - 1]
        else:
            response = self._responses[-1]
        if isinstance(response, BaseException):
            raise response
        return response


def _snapshot_repo(tmp_path: Path) -> TranscriptSnapshotRepository:
    repo = TranscriptSnapshotRepository(tmp_path / "segments")
    repo.save(
        "video",
        TranscriptSnapshot(
            metadata=VideoMetadata(
                video_id=VideoId("dQw4w9WgXcQ"),
                title="Vídeo de Teste",
                channel="Canal",
                duration=Duration.from_seconds(65),
                upload_date=date(2026, 5, 1),
                original_language=Language("pt"),
            ),
            transcript=Transcript(
                segments=(
                    TranscriptSegment(0, 3, "Olá mundo", "SPEAKER_00"),
                    TranscriptSegment(3, 8, "Falamos sobre testes.", "SPEAKER_01"),
                ),
                language=Language("pt"),
                language_confidence=0.95,
                source="whisperx",
            ),
            context=RenderContext(
                rendered_at=datetime(2026, 5, 1, tzinfo=UTC),
                whisper_model="inesc-id/WhisperLv3-X-PT-All",
                diarization_model="pyannote/speaker-diarization-community-1",
                transcription_source="whisperx",
            ),
        ),
    )
    return repo


def test_summary_service_generates_markdown_with_metadata_and_aliases(tmp_path: Path) -> None:
    fake = FakeChatClient(["## Resumo executivo\nConteúdo resumido."])
    service = TranscriptSummaryService(
        snapshots=_snapshot_repo(tmp_path),
        chat_client=fake,
        output_dir=tmp_path / "summaries",
        max_chars_per_chunk=12000,
        output_language="pt",
    )

    result = service.summarize(
        slug="video",
        output_base_path=tmp_path / "video.md",
        speaker_aliases={"SPEAKER_00": "Apresentador"},
    )

    assert result.path == tmp_path / "summaries" / "video.summary.md"
    content = result.path.read_text()
    assert "# Resumo — Vídeo de Teste" in content
    assert "**Modelo de sumarização**: qwen3.5-9b" in content
    assert "Conteúdo resumido" in content
    assert "Consulte a transcrição original" in content
    assert "Apresentador: Olá mundo" in fake.requests[0].user_prompt


def test_summary_service_normalizes_entities_and_skips_zero_duration_segments(
    tmp_path: Path,
) -> None:
    repo = TranscriptSnapshotRepository(tmp_path / "segments")
    repo.save(
        "video",
        TranscriptSnapshot(
            metadata=VideoMetadata(
                video_id=VideoId("dQw4w9WgXcQ"),
                title="Vídeo de Teste",
                channel="Canal",
                duration=Duration.from_seconds(65),
                upload_date=date(2026, 5, 1),
                original_language=Language("pt"),
            ),
            transcript=Transcript(
                segments=(
                    TranscriptSegment(0, 0, "Ghost", "UNKNOWN"),
                    TranscriptSegment(0, 3, "Ol&aacute;&nbsp;mundo", "SPEAKER_00"),
                ),
                language=Language("pt"),
                language_confidence=0.95,
                source="youtube_manual",
            ),
            context=RenderContext(
                rendered_at=datetime(2026, 5, 1, tzinfo=UTC),
                whisper_model="inesc-id/WhisperLv3-X-PT-All",
                diarization_model="pyannote/speaker-diarization-community-1",
                transcription_source="youtube_manual",
            ),
        ),
    )
    fake = FakeChatClient(["## Resumo executivo\nConteúdo resumido."])
    service = TranscriptSummaryService(
        snapshots=repo,
        chat_client=fake,
        output_dir=tmp_path / "summaries",
    )

    service.summarize(slug="video", output_base_path=tmp_path / "video.md")

    prompt = fake.requests[0].user_prompt
    assert "Olá mundo" in prompt
    assert "&nbsp;" not in prompt
    assert "UNKNOWN" not in prompt
    assert "[00:00:00 — 00:00:00]" not in prompt


def test_summary_service_uses_map_reduce_for_long_transcript(tmp_path: Path) -> None:
    repo = _snapshot_repo(tmp_path)
    snap = repo.load("video")
    assert snap is not None
    long_segments = tuple(
        TranscriptSegment(i * 2, i * 2 + 1, f"Trecho longo {i} " + "x" * 120, "SPEAKER_00")
        for i in range(30)
    )
    repo.save(
        "video",
        TranscriptSnapshot(
            metadata=snap.metadata,
            transcript=Transcript(long_segments, Language("pt"), 0.9, "whisperx"),
            context=snap.context,
        ),
    )
    fake = FakeChatClient(["parcial 1", "parcial 2", "## Resumo executivo\nfinal"])
    service = TranscriptSummaryService(
        snapshots=repo,
        chat_client=fake,
        output_dir=tmp_path / "summaries",
        max_chars_per_chunk=2000,
    )

    result = service.summarize(slug="video", output_base_path=tmp_path / "video.md")

    assert result.chunks > 1
    assert len(fake.requests) == result.chunks + 1
    assert "Resumos parciais" in fake.requests[-1].user_prompt
    assert "final" in result.path.read_text()


def test_summary_service_uses_partial_and_final_token_budgets(tmp_path: Path) -> None:
    repo = _snapshot_repo(tmp_path)
    snap = repo.load("video")
    assert snap is not None
    long_segments = tuple(
        TranscriptSegment(i * 2, i * 2 + 1, f"Trecho longo {i} " + "x" * 120, "SPEAKER_00")
        for i in range(30)
    )
    repo.save(
        "video",
        TranscriptSnapshot(
            metadata=snap.metadata,
            transcript=Transcript(long_segments, Language("pt"), 0.9, "whisperx"),
            context=snap.context,
        ),
    )
    fake = FakeChatClient(["parcial 1", "parcial 2", "## Resumo executivo\nfinal"])
    service = TranscriptSummaryService(
        snapshots=repo,
        chat_client=fake,
        output_dir=tmp_path / "summaries",
        max_chars_per_chunk=2000,
        partial_max_tokens=333,
        final_max_tokens=777,
    )

    result = service.summarize(slug="video", output_base_path=tmp_path / "video.md")

    assert result.chunks > 1
    assert {request.max_tokens for request in fake.requests[:-1]} == {333}
    assert fake.requests[-1].max_tokens == 777


def test_summary_service_uses_final_token_budget_for_single_pass(tmp_path: Path) -> None:
    fake = FakeChatClient(["## Resumo executivo\nConteúdo resumido."])
    service = TranscriptSummaryService(
        snapshots=_snapshot_repo(tmp_path),
        chat_client=fake,
        output_dir=tmp_path / "summaries",
        max_chars_per_chunk=12000,
        final_max_tokens=888,
    )

    service.summarize(slug="video", output_base_path=tmp_path / "video.md")

    assert len(fake.requests) == 1
    assert fake.requests[0].max_tokens == 888


def test_summary_service_emits_progress_events_for_map_reduce(tmp_path: Path) -> None:
    repo = _snapshot_repo(tmp_path)
    snap = repo.load("video")
    assert snap is not None
    long_segments = tuple(
        TranscriptSegment(i * 2, i * 2 + 1, f"Trecho {i} " + "x" * 120, "SPEAKER_00")
        for i in range(30)
    )
    repo.save(
        "video",
        TranscriptSnapshot(
            metadata=snap.metadata,
            transcript=Transcript(long_segments, Language("pt"), 0.9, "whisperx"),
            context=snap.context,
        ),
    )
    fake = FakeChatClient(["parcial", "parcial", "## Resumo executivo\nfinal"])
    events: list[SummaryProgress] = []
    service = TranscriptSummaryService(
        snapshots=repo,
        chat_client=fake,
        output_dir=tmp_path / "summaries",
        max_chars_per_chunk=2000,
    )

    result = service.summarize(
        slug="video",
        output_base_path=tmp_path / "video.md",
        on_progress=events.append,
    )

    assert result.chunks > 1
    kinds = [event.kind for event in events]
    assert kinds[0] == "planned"
    assert "chunk_started" in kinds
    assert "chunk_completed" in kinds
    assert "synthesis_started" in kinds
    assert kinds[-1] == "synthesis_completed"


def test_summary_service_splits_single_pass_after_timeout(tmp_path: Path) -> None:
    repo = _snapshot_repo(tmp_path)
    snap = repo.load("video")
    assert snap is not None
    repo.save(
        "video",
        TranscriptSnapshot(
            metadata=snap.metadata,
            transcript=Transcript(
                (TranscriptSegment(0, 60, "texto " * 1200, "SPEAKER_00"),),
                Language("pt"),
                0.9,
                "whisperx",
            ),
            context=snap.context,
        ),
    )
    fake = FakeChatClient(
        [
            ChatCompletionTimeoutError("timeout da passagem única"),
            "parcial 1",
            "parcial 2",
            "## Resumo executivo\nfinal",
        ]
    )
    events: list[SummaryProgress] = []
    service = TranscriptSummaryService(
        snapshots=repo,
        chat_client=fake,
        output_dir=tmp_path / "summaries",
        max_chars_per_chunk=100000,
        max_input_tokens=20000,
        timeout_split_retries=2,
        deduplicate_transcript=False,
    )

    result = service.summarize(
        slug="video",
        output_base_path=tmp_path / "video.md",
        on_progress=events.append,
    )

    assert result.chunks > 1
    assert (
        len(fake.requests) == result.chunks + 2
    )  # tentativa única com timeout + parciais + síntese
    assert fake.requests[0].max_tokens == 1024
    assert {request.max_tokens for request in fake.requests[1:-1]} == {512}
    assert fake.requests[-1].max_tokens == 1024
    assert "final" in result.path.read_text()
    assert "chunk_split" in [event.kind for event in events]


def test_summary_service_reraises_timeout_when_adaptive_split_is_disabled(tmp_path: Path) -> None:
    fake = FakeChatClient([ChatCompletionTimeoutError("timeout")])
    service = TranscriptSummaryService(
        snapshots=_snapshot_repo(tmp_path),
        chat_client=fake,
        output_dir=tmp_path / "summaries",
        timeout_split_retries=0,
    )

    with pytest.raises(ChatCompletionTimeoutError):
        service.summarize(slug="video", output_base_path=tmp_path / "video.md")


def test_summary_service_raises_for_missing_snapshot(tmp_path: Path) -> None:
    service = TranscriptSummaryService(
        snapshots=TranscriptSnapshotRepository(tmp_path / "segments"),
        chat_client=FakeChatClient(),
        output_dir=tmp_path / "summaries",
    )
    with pytest.raises(FileNotFoundError):
        service.summarize(slug="missing", output_base_path=tmp_path / "missing.md")


def test_summary_service_caps_chunks_by_input_token_budget(tmp_path: Path) -> None:
    repo = _snapshot_repo(tmp_path)
    snap = repo.load("video")
    assert snap is not None
    long_segments = tuple(
        TranscriptSegment(i * 2, i * 2 + 1, "texto " + ("x" * 180), "SPEAKER_00") for i in range(80)
    )
    repo.save(
        "video",
        TranscriptSnapshot(
            metadata=snap.metadata,
            transcript=Transcript(long_segments, Language("pt"), 0.9, "whisperx"),
            context=snap.context,
        ),
    )
    fake = FakeChatClient(["parcial", "## Resumo executivo\nfinal"])
    service = TranscriptSummaryService(
        snapshots=repo,
        chat_client=fake,
        output_dir=tmp_path / "summaries",
        max_chars_per_chunk=12000,
        max_input_tokens=2500,
        chars_per_token=2.0,
        deduplicate_transcript=False,
    )

    result = service.summarize(slug="video", output_base_path=tmp_path / "video.md")

    assert result.chunks > 1
    for request in fake.requests[:-1]:
        # 2500 tokens - reserva de 900 = 1600 tokens de transcrição; com 2 chars/token,
        # nenhum prompt de chunk deve se aproximar de 12k chars.
        assert len(request.user_prompt) < 4500


def test_summary_service_splits_single_very_long_segment(tmp_path: Path) -> None:
    repo = _snapshot_repo(tmp_path)
    snap = repo.load("video")
    assert snap is not None
    repo.save(
        "video",
        TranscriptSnapshot(
            metadata=snap.metadata,
            transcript=Transcript(
                (TranscriptSegment(0, 60, "a " * 5000, "SPEAKER_00"),),
                Language("pt"),
                0.9,
                "whisperx",
            ),
            context=snap.context,
        ),
    )
    fake = FakeChatClient(["parcial", "## Resumo executivo\nfinal"])
    service = TranscriptSummaryService(
        snapshots=repo,
        chat_client=fake,
        output_dir=tmp_path / "summaries",
        max_chars_per_chunk=12000,
        max_input_tokens=2000,
        chars_per_token=2.0,
        deduplicate_transcript=False,
    )

    result = service.summarize(slug="video", output_base_path=tmp_path / "video.md")

    assert result.chunks > 1
    for request in fake.requests[:-1]:
        assert len(request.user_prompt) < 3500


def test_summary_service_prompt_disables_thinking_by_default(tmp_path: Path) -> None:
    fake = FakeChatClient(["## Resumo executivo\nResumo final."])
    service = TranscriptSummaryService(
        snapshots=_snapshot_repo(tmp_path),
        chat_client=fake,
        output_dir=tmp_path / "summaries",
        output_language="pt",
    )

    service.summarize(slug="video", output_base_path=tmp_path / "video.md")

    prompt = fake.requests[0].system_prompt
    assert "Responda diretamente" in prompt
    assert "não use blocos <think>" in prompt


def test_summary_service_can_allow_thinking_instruction_to_be_omitted(tmp_path: Path) -> None:
    fake = FakeChatClient(["## Resumo executivo\nResumo final."])
    service = TranscriptSummaryService(
        snapshots=_snapshot_repo(tmp_path),
        chat_client=fake,
        output_dir=tmp_path / "summaries",
        output_language="pt",
        disable_thinking=False,
    )

    service.summarize(slug="video", output_base_path=tmp_path / "video.md")

    assert "Responda diretamente" not in fake.requests[0].system_prompt


class FakeWordTokenizer:
    description = "fake word tokenizer"
    is_exact = True

    def count(self, text: str) -> int:
        return len(text.split())

    def split(self, text: str, max_tokens: int) -> list[str]:
        words = text.split()
        return [" ".join(words[i : i + max_tokens]) for i in range(0, len(words), max_tokens)]


def test_summary_service_can_chunk_with_model_tokenizer(tmp_path: Path) -> None:
    repo = _snapshot_repo(tmp_path)
    snap = repo.load("video")
    assert snap is not None
    long_segments = tuple(
        TranscriptSegment(
            i * 2,
            i * 2 + 1,
            " ".join(f"palavra{i}_{j}" for j in range(30)),
            "SPEAKER_00",
        )
        for i in range(25)
    )
    repo.save(
        "video",
        TranscriptSnapshot(
            metadata=snap.metadata,
            transcript=Transcript(long_segments, Language("pt"), 0.9, "whisperx"),
            context=snap.context,
        ),
    )
    fake = FakeChatClient(["parcial", "## Resumo executivo\nfinal"])
    service = TranscriptSummaryService(
        snapshots=repo,
        chat_client=fake,
        output_dir=tmp_path / "summaries",
        max_chars_per_chunk=100000,
        max_input_tokens=1000,
        tokenizer=FakeWordTokenizer(),
        deduplicate_transcript=False,
    )

    result = service.summarize(slug="video", output_base_path=tmp_path / "video.md")

    assert result.chunks > 1
    assert "**Tokenização para chunking**: fake word tokenizer" in result.path.read_text()


def test_summary_service_deduplicates_repeated_adjacent_segments(tmp_path: Path) -> None:
    repo = _snapshot_repo(tmp_path)
    snap = repo.load("video")
    assert snap is not None
    segments = (
        TranscriptSegment(0, 2, "alpha beta gamma delta", "SPEAKER_00"),
        TranscriptSegment(2, 4, "alpha beta gamma delta", "SPEAKER_00"),
        TranscriptSegment(4, 6, "gamma delta epsilon zeta", "SPEAKER_00"),
    )
    repo.save(
        "video",
        TranscriptSnapshot(
            metadata=snap.metadata,
            transcript=Transcript(segments, Language("pt"), 0.9, "whisperx"),
            context=snap.context,
        ),
    )
    fake = FakeChatClient(["## Resumo executivo\nResumo final."])
    service = TranscriptSummaryService(
        snapshots=repo,
        chat_client=fake,
        output_dir=tmp_path / "summaries",
        min_overlap_words=2,
    )

    service.summarize(slug="video", output_base_path=tmp_path / "video.md")

    prompt = fake.requests[0].user_prompt
    assert prompt.count("SPEAKER_00:") == 1
    assert prompt.count("alpha beta gamma delta") == 1
    assert "epsilon zeta" in prompt
