"""Testes do MarkdownTranscriptRenderer."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from yt_transcriber_bot.domain.entities.transcript import (
    Transcript,
    TranscriptSegment,
)
from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.rendering.markdown_renderer import (
    MarkdownTranscriptRenderer,
    RenderContext,
)


def _meta() -> VideoMetadata:
    return VideoMetadata(
        video_id=VideoId(value="dQw4w9WgXcQ"),
        title="Entrevista com Fulano",
        channel="Canal Exemplo",
        duration=Duration.from_seconds(2533),  # 42min 13s
        upload_date=date(2024, 3, 15),
        original_language=Language(code="pt"),
    )


def _ctx() -> RenderContext:
    return RenderContext(
        rendered_at=datetime(2026, 5, 1, 14, 32, tzinfo=UTC),
        whisper_model="small",
        diarization_model="pyannote/speaker-diarization-3.1",
        transcription_source="whisperx",
    )


def _transcript_two_speakers() -> Transcript:
    segs = (
        TranscriptSegment(
            start_seconds=0.0,
            end_seconds=14.0,
            text="Olá pessoal, sejam bem-vindos.",
            speaker_label="SPEAKER_00",
        ),
        TranscriptSegment(
            start_seconds=14.0,
            end_seconds=31.0,
            text="Obrigado pelo convite.",
            speaker_label="SPEAKER_01",
        ),
        TranscriptSegment(
            start_seconds=31.0,
            end_seconds=45.0,
            text="Vamos começar então.",
            speaker_label="SPEAKER_00",
        ),
    )
    return Transcript(
        segments=segs,
        language=Language(code="pt"),
        language_confidence=0.98,
        source="whisperx",
    )


class TestHeader:
    def test_includes_canonical_url(self) -> None:
        md = MarkdownTranscriptRenderer().render(_meta(), _transcript_two_speakers(), _ctx())
        assert "https://www.youtube.com/watch?v=dQw4w9WgXcQ" in md

    def test_includes_title_in_h1(self) -> None:
        md = MarkdownTranscriptRenderer().render(_meta(), _transcript_two_speakers(), _ctx())
        assert md.startswith("# Transcrição — Entrevista com Fulano")

    def test_includes_channel(self) -> None:
        md = MarkdownTranscriptRenderer().render(_meta(), _transcript_two_speakers(), _ctx())
        assert "**Canal**: Canal Exemplo" in md

    def test_includes_duration_hms(self) -> None:
        md = MarkdownTranscriptRenderer().render(_meta(), _transcript_two_speakers(), _ctx())
        assert "**Duração**: 00:42:13" in md

    def test_includes_speaker_count(self) -> None:
        md = MarkdownTranscriptRenderer().render(_meta(), _transcript_two_speakers(), _ctx())
        assert "**Falantes identificados**: 2" in md

    def test_includes_language_with_confidence(self) -> None:
        md = MarkdownTranscriptRenderer().render(_meta(), _transcript_two_speakers(), _ctx())
        assert "**Idioma da transcrição**: pt (confiança: 98.0%)" in md

    def test_includes_models(self) -> None:
        md = MarkdownTranscriptRenderer().render(_meta(), _transcript_two_speakers(), _ctx())
        assert "**Modelo Whisper**: small" in md
        assert "**Modelo de diarização**: pyannote/speaker-diarization-3.1" in md

    def test_includes_source_friendly_label(self) -> None:
        ctx = RenderContext(
            rendered_at=datetime(2026, 1, 1, tzinfo=UTC),
            whisper_model="small",
            diarization_model="pyannote/x",
            transcription_source="youtube_manual",
        )
        t = Transcript(
            segments=(
                TranscriptSegment(
                    start_seconds=0,
                    end_seconds=2,
                    text="oi",
                    speaker_label="SPEAKER_00",
                ),
            ),
            language=Language(code="pt"),
            language_confidence=1.0,
            source="youtube_manual",
        )
        md = MarkdownTranscriptRenderer().render(_meta(), t, ctx)
        assert "Legendas manuais do YouTube" in md

    def test_unknown_upload_date(self) -> None:
        meta = VideoMetadata(
            video_id=VideoId(value="dQw4w9WgXcQ"),
            title="X",
            channel="Y",
            duration=Duration.from_seconds(60),
            upload_date=None,
            original_language=Language(code="pt"),
        )
        md = MarkdownTranscriptRenderer().render(meta, _transcript_two_speakers(), _ctx())
        assert "**Data do vídeo**: desconhecida" in md


class TestDiarizationSummary:
    def test_includes_per_speaker_summary(self) -> None:
        md = MarkdownTranscriptRenderer().render(_meta(), _transcript_two_speakers(), _ctx())
        assert "## Resumo da diarização" in md
        # SPEAKER_00 fala 14 + 14 = 28s, SPEAKER_01 fala 17s
        assert "**SPEAKER_00**" in md
        assert "**SPEAKER_01**" in md

    def test_summary_sorted_by_speaking_time_desc(self) -> None:
        md = MarkdownTranscriptRenderer().render(_meta(), _transcript_two_speakers(), _ctx())
        idx_00 = md.find("**SPEAKER_00**")
        idx_01 = md.find("**SPEAKER_01**")
        assert idx_00 < idx_01

    def test_summary_with_aliases(self) -> None:
        md = MarkdownTranscriptRenderer().render(
            _meta(),
            _transcript_two_speakers(),
            _ctx(),
            speaker_aliases={"SPEAKER_00": "Maria", "SPEAKER_01": "João"},
        )
        assert "**Maria**" in md
        assert "**João**" in md

    def test_empty_transcript_safely_renders(self) -> None:
        t = Transcript(
            segments=(),
            language=Language(code="pt"),
            language_confidence=0.0,
            source="whisperx",
        )
        md = MarkdownTranscriptRenderer().render(_meta(), t, _ctx())
        assert "Sem falantes identificados" in md


class TestTurns:
    def test_groups_consecutive_same_speaker_segments(self) -> None:
        segs = (
            TranscriptSegment(
                start_seconds=0.0,
                end_seconds=2.0,
                text="Olá.",
                speaker_label="A",
            ),
            TranscriptSegment(
                start_seconds=2.0,
                end_seconds=4.0,
                text="Como vai?",
                speaker_label="A",
            ),
            TranscriptSegment(
                start_seconds=4.0,
                end_seconds=6.0,
                text="Bem.",
                speaker_label="B",
            ),
        )
        t = Transcript(
            segments=segs,
            language=Language(code="pt"),
            language_confidence=0.9,
            source="whisperx",
        )
        md = MarkdownTranscriptRenderer().render(_meta(), t, _ctx())
        # Devem haver dois cabeçalhos de turno: A e B
        assert md.count("### [") == 2
        assert "Olá. Como vai?" in md
        assert "Bem." in md

    def test_turn_text_repairs_common_mojibake(self) -> None:
        t = Transcript(
            segments=(
                TranscriptSegment(
                    start_seconds=0,
                    end_seconds=2,
                    text="VocÃª nÃ£o tem aÃ§Ã£o.",
                    speaker_label="SPEAKER_00",
                ),
            ),
            language=Language(code="pt"),
            language_confidence=0.9,
            source="whisperx",
        )

        md = MarkdownTranscriptRenderer().render(_meta(), t, _ctx())

        assert "Você não tem ação." in md
        assert "VocÃª" not in md

    def test_turn_uses_aliases(self) -> None:
        md = MarkdownTranscriptRenderer().render(
            _meta(),
            _transcript_two_speakers(),
            _ctx(),
            speaker_aliases={"SPEAKER_00": "Ana"},
        )
        assert "### [00:00:00 — 00:00:14] Ana" in md

    def test_timestamps_in_hms(self) -> None:
        md = MarkdownTranscriptRenderer().render(_meta(), _transcript_two_speakers(), _ctx())
        assert "[00:00:00 —" in md
        assert "00:00:14]" in md

    def test_empty_transcript_message(self) -> None:
        t = Transcript(
            segments=(),
            language=Language(code="pt"),
            language_confidence=0.0,
            source="whisperx",
        )
        md = MarkdownTranscriptRenderer().render(_meta(), t, _ctx())
        assert "Nenhum turno de fala disponível" in md

    def test_normalizes_html_entities(self) -> None:
        t = Transcript(
            segments=(
                TranscriptSegment(
                    start_seconds=0.0,
                    end_seconds=2.0,
                    text="Ol&aacute;&nbsp;mundo &amp;#39;teste&amp;#39;",
                    speaker_label="SPEAKER_00",
                ),
            ),
            language=Language(code="pt"),
            language_confidence=1.0,
            source="youtube_manual",
        )
        md = MarkdownTranscriptRenderer().render(_meta(), t, _ctx())
        assert "Olá mundo 'teste'" in md
        assert "&nbsp;" not in md


class TestStructuralIntegrity:
    def test_ends_with_newline(self) -> None:
        md = MarkdownTranscriptRenderer().render(_meta(), _transcript_two_speakers(), _ctx())
        assert md.endswith("\n")

    def test_has_two_horizontal_rules(self) -> None:
        md = MarkdownTranscriptRenderer().render(_meta(), _transcript_two_speakers(), _ctx())
        assert md.count("\n---\n") == 2

    @pytest.mark.parametrize("source", ["whisperx", "youtube_manual", "youtube_auto"])
    def test_round_trip_for_all_sources(self, source: str) -> None:
        ctx = RenderContext(
            rendered_at=datetime(2026, 1, 1, tzinfo=UTC),
            whisper_model="small",
            diarization_model="pyannote/x",
            transcription_source=source,
        )
        t = Transcript(
            segments=(
                TranscriptSegment(
                    start_seconds=0,
                    end_seconds=2,
                    text="oi",
                    speaker_label="SPEAKER_00",
                ),
            ),
            language=Language(code="pt"),
            language_confidence=1.0,
            source=source,
        )
        md = MarkdownTranscriptRenderer().render(_meta(), t, ctx)
        assert "## Transcrição" in md
        assert "## Resumo da diarização" in md


def test_renderer_splits_long_single_speaker_transcript_into_readable_blocks() -> None:
    segs = tuple(
        TranscriptSegment(
            start_seconds=float(i * 45),
            end_seconds=float((i + 1) * 45),
            text=(
                "Esta é uma frase de teste para simular uma fala longa. "
                "Ela deve ser quebrada em blocos menores para leitura."
            ),
            speaker_label="SPEAKER_00",
        )
        for i in range(5)
    )
    t = Transcript(
        segments=segs,
        language=Language(code="pt"),
        language_confidence=1.0,
        source="youtube_auto",
    )
    md = MarkdownTranscriptRenderer().render(_meta(), t, _ctx())
    # O renderer mantém o texto em parágrafos legíveis, mas não repete o
    # cabeçalho quando a mesma pessoa continua falando bloco após bloco.
    assert md.count("### [") == 1
    assert "### [00:00:00 — 00:03:45] SPEAKER_00" in md
    assert md.count("Esta é uma frase de teste") == 5


def test_renderer_does_not_re_normalize_accumulated_turn_text_unnecessarily(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    original = MarkdownTranscriptRenderer._normalize_text

    def counting_normalize(text: str) -> str:
        nonlocal calls
        calls += 1
        return original(text)

    monkeypatch.setattr(
        MarkdownTranscriptRenderer,
        "_normalize_text",
        staticmethod(counting_normalize),
    )

    transcript = Transcript(
        segments=tuple(
            TranscriptSegment(
                start_seconds=float(i),
                end_seconds=float(i + 1),
                text=f"Trecho {i}.",
                speaker_label="SPEAKER_00",
            )
            for i in range(4)
        ),
        language=Language(code="pt"),
        language_confidence=1.0,
        source="whisperx",
    )

    MarkdownTranscriptRenderer().render(_meta(), transcript, _ctx())

    assert calls <= len(transcript.segments)
