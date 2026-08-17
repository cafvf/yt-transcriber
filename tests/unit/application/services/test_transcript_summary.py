from __future__ import annotations

from datetime import UTC, datetime

from yt_transcriber_bot.application.ports.canonical_transcript import (
    CanonicalTranscriptRecord,
    CanonicalTranscriptStore,
    TranscriptRenderContext,
)
from yt_transcriber_bot.application.ports.text_generation import TextGenerationRequest
from yt_transcriber_bot.application.services.transcript_summary import TranscriptSummaryService
from yt_transcriber_bot.domain.entities.transcript import Transcript, TranscriptSegment
from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata
from yt_transcriber_bot.domain.value_objects.language import Language


class CanonicalStore(CanonicalTranscriptStore):
    def __init__(self, record: CanonicalTranscriptRecord) -> None:
        self.record = record

    def persist(self, reference: str, record: CanonicalTranscriptRecord) -> None:
        _ = reference
        self.record = record

    def delete(self, reference: str) -> None:
        _ = reference

    def load(self, reference: str) -> CanonicalTranscriptRecord | None:
        return self.record if reference == "canonical" else None

    def load_metadata(self, reference: str) -> VideoMetadata | None:
        record = self.load(reference)
        return record.metadata if record else None

    def load_metadata_many(self, references: tuple[str, ...]) -> dict[str, VideoMetadata]:
        return {
            reference: self.record.metadata for reference in references if reference == "canonical"
        }


class Generator:
    model = "fake-model"

    def __init__(self) -> None:
        self.requests: list[TextGenerationRequest] = []

    def complete(self, request: TextGenerationRequest) -> str:
        self.requests.append(request)
        return "## Resumo executivo\nresultado"


class Tokenizer:
    description = "fake tokenizer"
    is_exact = True

    def count(self, text: str) -> int:
        return len(text.split())

    def split(self, text: str, max_tokens: int) -> list[str]:
        words = text.split()
        return [" ".join(words[i : i + max_tokens]) for i in range(0, len(words), max_tokens)]


def _record() -> CanonicalTranscriptRecord:
    return CanonicalTranscriptRecord(
        metadata=VideoMetadata(
            video_id=None,
            title="Áudio de teste",
            channel="Telegram",
            duration=None,
            upload_date=None,
            original_language=Language("pt"),
            source_label="Telegram (mídia privada)",
            source_reference="telegram:private-file",
        ),
        transcript=Transcript(
            segments=(TranscriptSegment(0.0, 2.0, "conteúdo canônico", "SPEAKER_00"),),
            language=Language("pt"),
            language_confidence=0.9,
            source="whisperx",
        ),
        context=TranscriptRenderContext(
            rendered_at=datetime(2026, 8, 16, tzinfo=UTC),
            whisper_model="test",
            diarization_model="test",
            transcription_source="whisperx",
        ),
    )


def test_application_summary_policy_runs_with_only_application_domain_fakes() -> None:
    generator = Generator()
    service = TranscriptSummaryService(
        snapshots=CanonicalStore(_record()),
        chat_client=generator,
        tokenizer=Tokenizer(),
        output_language="pt",
    )

    result = service.summarize(
        slug="canonical",
        speaker_aliases={"SPEAKER_00": "Pessoa"},
    )

    assert result.model == "fake-model"
    assert "resultado" in result.content
    assert "Pessoa: conteúdo canônico" in generator.requests[0].user_prompt
