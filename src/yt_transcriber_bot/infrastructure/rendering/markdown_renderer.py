"""Renderiza o ``Transcript`` em Markdown segundo o template aprovado.

O template foi acordado no contrato funcional (§ Renderização) e contém:
- Cabeçalho com URL, canal, duração, datas, modelo, idioma e contagem de
  falantes (auditoria).
- Resumo da diarização (tempo total e percentual por falante).
- Transcrição em blocos por **turno de fala**: ``[start - end] LABEL`` +
  texto.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from yt_transcriber_bot.domain.entities.transcript import Transcript
from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.infrastructure.text.normalization import normalize_artifact_text


@dataclass(frozen=True)
class RenderContext:
    """Metadados de execução incluídos no cabeçalho do MD."""

    rendered_at: datetime
    whisper_model: str
    diarization_model: str  # ex.: "pyannote/speaker-diarization-3.1"
    transcription_source: str  # whisperx | youtube_manual | youtube_auto


class MarkdownTranscriptRenderer:
    """Converte (VideoMetadata, Transcript, RenderContext) em string Markdown.

    A saída é otimizada para leitura humana, não apenas para arquivamento:
    turnos muito longos são quebrados em blocos menores e o texto é
    paragraphizado por pontuação. Isso evita Markdown com blocos de vários
    minutos quando a diarização identifica apenas um falante.
    """

    max_block_duration_s = 90.0
    max_block_chars = 1200
    max_paragraph_chars = 520

    def render(
        self,
        metadata: VideoMetadata,
        transcript: Transcript,
        context: RenderContext,
        *,
        speaker_aliases: Mapping[str, str] | None = None,
    ) -> str:
        aliases = dict(speaker_aliases or {})
        parts: list[str] = []
        parts.append(self._render_header(metadata, transcript, context, aliases))
        parts.append("")
        parts.append("---")
        parts.append("")
        parts.append(self._render_diarization_summary(transcript, aliases))
        parts.append("")
        parts.append("---")
        parts.append("")
        parts.append("## Transcrição")
        parts.append("")
        parts.extend(self._render_turns(transcript, aliases))
        return "\n".join(parts).rstrip() + "\n"

    # ------------------------------------------------------------------
    # Cabeçalho
    # ------------------------------------------------------------------

    def _render_header(
        self,
        metadata: VideoMetadata,
        transcript: Transcript,
        context: RenderContext,
        aliases: Mapping[str, str] | None = None,
    ) -> str:
        upload = metadata.upload_date.isoformat() if metadata.upload_date else "desconhecida"
        rendered = context.rendered_at.strftime("%Y-%m-%d %H:%M (%Z)").strip()
        aliases = dict(aliases or {})
        speaker_labels = transcript.speaker_labels()
        speakers = len(speaker_labels)
        display_speakers = len({self._display_speaker(label, aliases) for label in speaker_labels})
        confidence_pct = f"{transcript.language_confidence * 100:.1f}%"
        source_label = {
            "whisperx": "WhisperX",
            "youtube_manual": "Legendas manuais do YouTube",
            "youtube_auto": "Legendas automáticas do YouTube",
        }.get(transcript.source, transcript.source)

        lines = [
            f"# Transcrição — {metadata.title}",
            "",
            f"**URL**: {metadata.canonical_url()}",
            f"**Canal**: {metadata.channel}",
            f"**Duração**: {metadata.duration.to_hms()}",
            f"**Data do vídeo**: {upload}",
            f"**Data da transcrição**: {rendered}",
            f"**Fonte da transcrição**: {source_label}",
            f"**Modelo Whisper**: {context.whisper_model}",
            f"**Modelo de diarização**: {context.diarization_model}",
            f"**Idioma detectado**: {transcript.language.code} (confiança: {confidence_pct})",
            f"**Falantes identificados**: {speakers}",
        ]
        if aliases and display_speakers != speakers:
            lines.append(f"**Falantes após renomeação/mesclagem**: {display_speakers}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Resumo da diarização
    # ------------------------------------------------------------------

    def _render_diarization_summary(
        self,
        transcript: Transcript,
        aliases: Mapping[str, str],
    ) -> str:
        speaking_time = transcript.speaker_speaking_time()
        if not speaking_time:
            return "## Resumo da diarização\n\n*Sem falantes identificados.*"

        # Agrega por nome exibido, não apenas pelo label cru. Assim,
        # SPEAKER_00=Maria e SPEAKER_02=Maria passam a ser uma única pessoa.
        merged: dict[str, float] = {}
        for label, dur in speaking_time.items():
            display = self._display_speaker(label, aliases)
            merged[display] = merged.get(display, 0.0) + dur.total_seconds

        total_seconds = sum(merged.values())
        lines: list[str] = ["## Resumo da diarização", ""]
        for display, seconds in sorted(merged.items(), key=lambda x: x[1], reverse=True):
            dur = Duration.from_seconds(seconds)
            pct = (seconds / total_seconds) * 100 if total_seconds > 0 else 0
            lines.append(f"- **{display}**: {dur.to_hms()} ({pct:.1f}%)")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Turnos de fala
    # ------------------------------------------------------------------

    def _render_turns(
        self,
        transcript: Transcript,
        aliases: Mapping[str, str],
    ) -> list[str]:
        turns = self._readable_turns(transcript)
        if not turns:
            return ["*Nenhum turno de fala disponível.*"]
        # Modo compacto de continuidade: blocos consecutivos com o mesmo nome
        # exibido compartilham um cabeçalho. Isso cobre tanto quebras por
        # tamanho/duração quanto a mesclagem manual de falantes por alias igual.
        out: list[str] = []
        i = 0
        while i < len(turns):
            run_start = turns[i]
            run_display = self._display_speaker(run_start.speaker_label, aliases)
            run_end = run_start
            j = i + 1
            while j < len(turns):
                current_display = self._display_speaker(turns[j].speaker_label, aliases)
                if current_display != run_display:
                    break
                run_end = turns[j]
                j += 1

            start = Duration.from_seconds(run_start.start_seconds).to_hms()
            end = Duration.from_seconds(run_end.end_seconds).to_hms()
            out.append(f"### [{start} — {end}] {run_display}")
            out.append("")
            for turn in turns[i:j]:
                out.extend(self._paragraphize(turn.text))
                out.append("")
            i = j
        return out

    def _readable_turns(self, transcript: Transcript) -> tuple[object, ...]:
        """Agrupa por falante, mas quebra blocos longos para leitura.

        ``Transcript.to_speaker_turns`` é correto semanticamente, mas pode gerar
        um único bloco de 10+ minutos quando só há um falante. Aqui usamos os
        segmentos originais para limitar duração/tamanho de cada bloco.
        """
        valid_segments = tuple(
            seg
            for seg in transcript.segments
            if seg.text.strip() and seg.end_seconds > seg.start_seconds
        )
        if not valid_segments:
            return ()

        from yt_transcriber_bot.domain.entities.transcript import SpeakerTurn

        turns: list[SpeakerTurn] = []
        current_label = valid_segments[0].speaker_label
        current_start = valid_segments[0].start_seconds
        current_end = valid_segments[0].end_seconds
        current_parts: list[str] = [valid_segments[0].text]

        def flush() -> None:
            nonlocal current_start, current_end, current_label, current_parts
            text = self._normalize_text(" ".join(current_parts))
            if text:
                turns.append(
                    SpeakerTurn(
                        start_seconds=current_start,
                        end_seconds=current_end,
                        speaker_label=current_label,
                        text=text,
                    )
                )

        for seg in valid_segments[1:]:
            current_text = self._normalize_text(" ".join(current_parts))
            would_exceed_duration = (seg.end_seconds - current_start) > self.max_block_duration_s
            would_exceed_chars = (len(current_text) + 1 + len(seg.text)) > self.max_block_chars
            speaker_changed = seg.speaker_label != current_label

            if speaker_changed or would_exceed_duration or would_exceed_chars:
                flush()
                current_label = seg.speaker_label
                current_start = seg.start_seconds
                current_end = seg.end_seconds
                current_parts = [seg.text]
            else:
                current_end = seg.end_seconds
                current_parts.append(seg.text)

        flush()
        return tuple(turns)

    @staticmethod
    def _display_speaker(label: str, aliases: Mapping[str, str]) -> str:
        """Nome exibido para um falante.

        Aliases iguais representam uma mesclagem manual de falantes.
        Ex.: SPEAKER_00=Maria, SPEAKER_02=Maria.
        """
        alias = aliases.get(label, "").strip()
        return alias or label

    @staticmethod
    def _normalize_text(text: str) -> str:
        return normalize_artifact_text(text)

    def _paragraphize(self, text: str) -> list[str]:
        """Quebra texto em parágrafos curtos por fim de frase."""
        text = self._normalize_text(text)
        if not text:
            return []
        sentences = self._split_sentences(text)
        paragraphs: list[str] = []
        current: list[str] = []
        current_len = 0
        for sentence in sentences:
            sentence_len = len(sentence)
            if current and current_len + 1 + sentence_len > self.max_paragraph_chars:
                paragraphs.append(" ".join(current).strip())
                current = [sentence]
                current_len = sentence_len
            else:
                current.append(sentence)
                current_len += sentence_len + (1 if current_len else 0)
        if current:
            paragraphs.append(" ".join(current).strip())
        return paragraphs or [text]

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        # Mantém a pontuação final na frase. O padrão é propositalmente simples
        # para não depender de modelos NLP.
        pieces = re.split(r"(?<=[.!?])\s+", text)
        return [p.strip() for p in pieces if p.strip()]
