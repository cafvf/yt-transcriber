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
)
from yt_transcriber_bot.infrastructure.summarization.transcript_summarizer import (
    TranscriptSummaryService,
)


class FakeChatClient:
    model = "qwen3.5-9b"

    def __init__(self, responses: list[str] | None = None) -> None:
        self.requests: list[ChatCompletionRequest] = []
        self._responses = responses or ["## Resumo executivo\nResumo final."]

    def complete(self, request: ChatCompletionRequest) -> str:
        self.requests.append(request)
        if len(self.requests) <= len(self._responses):
            return self._responses[len(self.requests) - 1]
        return self._responses[-1]


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
        TranscriptSegment(i * 2, i * 2 + 1, "texto " + ("x" * 180), "SPEAKER_00")
        for i in range(80)
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
