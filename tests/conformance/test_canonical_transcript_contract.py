"""REQ-ARC-006 canonical transcript store/renderer contract evidence."""

from __future__ import annotations

import ast
import inspect
import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from yt_transcriber_bot.application.ports.canonical_transcript import (
    CanonicalTranscriptCorruptError,
    CanonicalTranscriptNotFoundError,
    CanonicalTranscriptRecord,
    CanonicalTranscriptStore,
    TranscriptRenderContext,
)
from yt_transcriber_bot.application.ports.transcript_renderer import (
    TranscriptRenderer,
    TranscriptRenderRequest,
)
from yt_transcriber_bot.application.services.rename_speakers import RenameSpeakersService
from yt_transcriber_bot.domain.entities.transcript import Transcript, TranscriptSegment
from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.provenance import ProcessingProvenance
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.exporting.transcript_exporter import (
    TranscriptExportService,
)
from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
    TranscriptSnapshotRepository,
)
from yt_transcriber_bot.infrastructure.rendering.markdown_renderer import (
    MarkdownTranscriptRenderer,
)
from yt_transcriber_bot.infrastructure.summarization.openai_compatible_client import (
    ChatCompletionRequest,
)
from yt_transcriber_bot.infrastructure.summarization.transcript_summarizer import (
    TranscriptSummaryService,
)

ROOT = Path(__file__).resolve().parents[2]
CONCRETE_STORE_MODULE = (
    "yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot"
)


@dataclass
class InMemoryCanonicalTranscriptStore(CanonicalTranscriptStore):
    records: dict[str, CanonicalTranscriptRecord] = field(default_factory=dict)

    def persist(self, reference: str, record: CanonicalTranscriptRecord) -> None:
        self.records[reference] = record

    def delete(self, reference: str) -> None:
        self.records.pop(reference, None)

    def load(self, reference: str) -> CanonicalTranscriptRecord | None:
        return self.records.get(reference)

    def load_metadata(self, reference: str) -> VideoMetadata | None:
        record = self.load(reference)
        return record.metadata if record is not None else None

    def load_metadata_many(
        self,
        references: tuple[str, ...],
    ) -> dict[str, VideoMetadata]:
        return {
            reference: record.metadata
            for reference in references
            if (record := self.load(reference)) is not None
        }


@dataclass
class FakeRenderer(TranscriptRenderer):
    requests: list[TranscriptRenderRequest] = field(default_factory=list)

    def render_transcript(self, request: TranscriptRenderRequest) -> str:
        self.requests.append(request)
        aliases = dict(request.speaker_aliases or {})
        names = [aliases.get(label, label) for label in request.record.transcript.speaker_labels()]
        return "# fake\n" + "\n".join(names) + "\n"


class FakeChatClient:
    model = "fake-model"

    def complete(self, request: ChatCompletionRequest) -> str:
        del request
        return "## Resumo executivo\nResumo."


class FakeTokenizer:
    description = "fake-tokenizer"
    is_exact = True

    def count(self, text: str) -> int:
        return max(1, len(text.split()))

    def split(self, text: str, max_tokens: int) -> list[str]:
        del max_tokens
        return [text]


def _record() -> CanonicalTranscriptRecord:
    return CanonicalTranscriptRecord(
        metadata=VideoMetadata(
            video_id=VideoId("dQw4w9WgXcQ"),
            title="Contrato canônico",
            channel="Canal",
            duration=Duration.from_seconds(30),
            upload_date=date(2026, 8, 16),
            original_language=Language("pt"),
        ),
        transcript=Transcript(
            segments=(
                TranscriptSegment(0.0, 3.0, "Olá.", "SPEAKER_00"),
                TranscriptSegment(3.0, 6.0, "Mundo.", "SPEAKER_01"),
            ),
            language=Language("pt"),
            language_confidence=0.95,
            source="whisperx",
        ),
        context=TranscriptRenderContext(
            rendered_at=datetime(2026, 8, 16, tzinfo=UTC),
            whisper_model="small",
            diarization_model="pyannote/model",
            transcription_source="whisperx",
        ),
        processing_fingerprint="fingerprint",
        processing_provenance=ProcessingProvenance(
            processing_path="audio_asr",
            transcription_backend="whisperx",
        ),
    )


def _absolute_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imports.add(node.module)
    return imports


def test_store_contract_is_reference_based_not_generic_filesystem() -> None:
    persist = inspect.signature(CanonicalTranscriptStore.persist).parameters
    load = inspect.signature(CanonicalTranscriptStore.load).parameters

    assert list(persist) == ["self", "reference", "record"]
    assert list(load) == ["self", "reference"]
    for forbidden in ("read_text", "write_text", "list_files_oldest_first", "path_for"):
        assert not hasattr(CanonicalTranscriptStore, forbidden)


def test_renderer_contract_accepts_structured_evidence_without_storage_methods() -> None:
    request = TranscriptRenderRequest(
        record=_record(),
        speaker_aliases={"SPEAKER_00": "Ana"},
    )
    assert request.record.processing_provenance.transcription_backend == "whisperx"
    assert list(inspect.signature(TranscriptRenderer.render_transcript).parameters) == [
        "self",
        "request",
    ]
    for forbidden in ("save", "persist", "delete", "write_text"):
        assert not hasattr(TranscriptRenderer, forbidden)


def test_concrete_store_round_trips_through_application_contract(tmp_path: Path) -> None:
    store: CanonicalTranscriptStore = TranscriptSnapshotRepository(tmp_path / "segments")
    expected = _record()

    store.persist("ref-1", expected)

    assert store.require("ref-1") == expected


def test_concrete_store_keeps_version_aware_legacy_decode(tmp_path: Path) -> None:
    store = TranscriptSnapshotRepository(tmp_path / "segments")
    store.path_for("legacy").parent.mkdir(parents=True, exist_ok=True)
    store.path_for("legacy").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "metadata": {
                    "video_id": "dQw4w9WgXcQ",
                    "title": "Legacy",
                    "channel": "Canal",
                    "duration_seconds": 30,
                    "upload_date": None,
                    "original_language": "pt",
                    "has_alternate_audio_tracks": False,
                    "alternate_languages": [],
                },
                "transcript": {
                    "language": "pt",
                    "language_confidence": 0.9,
                    "source": "whisperx",
                    "segments": [],
                },
                "context": {
                    "rendered_at": "2026-08-16T00:00:00+00:00",
                    "whisper_model": "small",
                    "diarization_model": "legacy-model",
                    "transcription_source": "whisperx",
                },
            }
        ),
        encoding="utf-8",
    )

    loaded = store.require("legacy")

    assert loaded.metadata.title == "Legacy"
    assert loaded.processing_fingerprint == ""
    assert loaded.processing_provenance == ProcessingProvenance.unknown()


def test_missing_evidence_has_explicit_application_error() -> None:
    with pytest.raises(CanonicalTranscriptNotFoundError, match="Snapshot inexistente"):
        InMemoryCanonicalTranscriptStore().require("missing")


def test_corrupt_json_has_explicit_application_error(tmp_path: Path) -> None:
    store = TranscriptSnapshotRepository(tmp_path / "segments")
    store.path_for("broken").parent.mkdir(parents=True, exist_ok=True)
    store.path_for("broken").write_text("{not-json", encoding="utf-8")

    with pytest.raises(CanonicalTranscriptCorruptError):
        store.load("broken")


def test_markdown_adapter_renders_application_record() -> None:
    rendered = MarkdownTranscriptRenderer().render_transcript(
        TranscriptRenderRequest(
            record=_record(),
            speaker_aliases={"SPEAKER_00": "Ana"},
        )
    )

    assert rendered.startswith("# Transcrição — Contrato canônico")
    assert "Ana" in rendered


def test_rename_workflow_runs_with_in_memory_store_and_fake_renderer(
    tmp_path: Path,
) -> None:
    store = InMemoryCanonicalTranscriptStore()
    store.persist("ref", _record())
    renderer = FakeRenderer()
    service = RenameSpeakersService(store, renderer)

    result = service.rename(
        "ref",
        {"SPEAKER_00": "Ana", "SPEAKER_99": "Ignorado"},
        tmp_path / "renamed.md",
    )

    assert result.speakers_renamed == 1
    assert result.md_path.read_text(encoding="utf-8").startswith("# fake")
    assert renderer.requests[0].record is store.records["ref"]


def test_export_consumer_runs_with_in_memory_store(tmp_path: Path) -> None:
    store = InMemoryCanonicalTranscriptStore()
    store.persist("ref", _record())

    result = TranscriptExportService(store).export(
        slug="ref",
        output_base_path=tmp_path / "ref.md",
        format="srt",
        speaker_aliases={"SPEAKER_00": "Ana"},
    )

    assert "Ana: Olá." in result.path.read_text(encoding="utf-8")


def test_summary_consumer_runs_with_in_memory_store(tmp_path: Path) -> None:
    store = InMemoryCanonicalTranscriptStore()
    store.persist("ref", _record())
    service = TranscriptSummaryService(
        snapshots=store,
        chat_client=FakeChatClient(),
        output_dir=tmp_path / "summaries",
        tokenizer=FakeTokenizer(),
    )

    result = service.summarize(
        slug="ref",
        output_base_path=tmp_path / "ref.md",
    )

    assert result.path.is_file()
    assert "Resumo" in result.path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "relative",
    [
        "src/yt_transcriber_bot/application/services/rename_speakers.py",
        "src/yt_transcriber_bot/application/services/history_search.py",
        "src/yt_transcriber_bot/infrastructure/summarization/transcript_summarizer.py",
        "src/yt_transcriber_bot/infrastructure/exporting/transcript_exporter.py",
        "src/yt_transcriber_bot/infrastructure/exporting/plain_text_exporter.py",
        "src/yt_transcriber_bot/infrastructure/exporting/video_subtitles_exporter.py",
        "src/yt_transcriber_bot/infrastructure/telegram/history.py",
    ],
)
def test_transcript_consumers_do_not_import_concrete_snapshot_repository(
    relative: str,
) -> None:
    imports = _absolute_imports(ROOT / relative)
    assert CONCRETE_STORE_MODULE not in imports
