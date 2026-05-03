"""Sumarização de transcrições persistidas em snapshots.

O serviço não reprocessa áudio. Ele carrega o snapshot JSON já salvo, reconstrói
um texto limpo com timestamps e chama uma LLM local/remota via um cliente de
chat completion. Para transcrições longas, usa uma estratégia simples de
map-reduce: resume blocos e depois sintetiza os resumos parciais.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Protocol
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from yt_transcriber_bot.domain.entities.transcript import TranscriptSegment
from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
    TranscriptSnapshot,
    TranscriptSnapshotRepository,
)
from yt_transcriber_bot.infrastructure.summarization.openai_compatible_client import (
    ChatCompletionError,
    ChatCompletionRequest,
)


class SummaryError(RuntimeError):
    """Falha de sumarização ou configuração."""


class ChatCompletionClient(Protocol):
    """Contrato mínimo necessário para gerar resumos."""

    @property
    def model(self) -> str: ...

    def complete(self, request: ChatCompletionRequest) -> str: ...


@dataclass(frozen=True)
class SummaryResult:
    """Resultado de geração do resumo."""

    path: Path
    chunks: int
    model: str


class TranscriptSummaryService:
    """Gera um resumo estruturado em Markdown a partir de um snapshot."""

    def __init__(
        self,
        *,
        snapshots: TranscriptSnapshotRepository,
        chat_client: ChatCompletionClient,
        output_dir: Path,
        max_chars_per_chunk: int = 4_000,
        max_input_tokens: int = 2_500,
        chars_per_token: float = 2.0,
        output_language: str = "auto",
        disable_thinking: bool = True,
    ) -> None:
        self._snapshots = snapshots
        self._chat_client = chat_client
        self._output_dir = output_dir
        self._max_chars_per_chunk = max(1_000, max_chars_per_chunk)
        self._max_input_tokens = max(512, max_input_tokens)
        self._chars_per_token = max(1.0, chars_per_token)
        self._output_language = output_language.strip().lower() or "auto"
        self._disable_thinking = disable_thinking

    def summarize(
        self,
        *,
        slug: str,
        output_base_path: Path,
        speaker_aliases: Mapping[str, str] | None = None,
    ) -> SummaryResult:
        snap = self._snapshots.load(slug)
        if snap is None:
            raise FileNotFoundError(f"Snapshot inexistente: {slug}")
        transcript_text = _snapshot_to_text(snap, speaker_aliases or {})
        effective_max_chars = _effective_chunk_chars(
            max_chars_per_chunk=self._max_chars_per_chunk,
            max_input_tokens=self._max_input_tokens,
            chars_per_token=self._chars_per_token,
        )
        chunks = _chunk_text(transcript_text, effective_max_chars)
        if not chunks:
            raise SummaryError("Snapshot não contém texto suficiente para sumarizar.")
        try:
            if len(chunks) == 1:
                summary_body = self._summarize_single(snap, chunks[0])
            else:
                partials = [self._summarize_chunk(snap, chunk, i, len(chunks)) for i, chunk in enumerate(chunks, 1)]
                summary_body = self._synthesize_partials(snap, partials)
        except ChatCompletionError:
            raise
        except Exception as exc:  # pragma: no cover - camada defensiva
            raise SummaryError(f"Falha inesperada na sumarização: {exc}") from exc
        output_path = self._output_path(slug, output_base_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            _wrap_summary_markdown(snap, summary_body, model=self._chat_client.model, chunks=len(chunks)),
            encoding="utf-8",
        )
        return SummaryResult(path=output_path, chunks=len(chunks), model=self._chat_client.model)

    def _summarize_single(self, snap: TranscriptSnapshot, transcript_text: str) -> str:
        return self._chat_client.complete(
            ChatCompletionRequest(
                system_prompt=_system_prompt(self._output_language, snap.transcript.language.code, self._disable_thinking),
                user_prompt=_single_pass_prompt(snap, transcript_text),
            )
        )

    def _summarize_chunk(
        self, snap: TranscriptSnapshot, chunk: str, index: int, total: int
    ) -> str:
        return self._chat_client.complete(
            ChatCompletionRequest(
                system_prompt=_system_prompt(self._output_language, snap.transcript.language.code, self._disable_thinking),
                user_prompt=_chunk_prompt(snap, chunk, index, total),
            )
        )

    def _synthesize_partials(self, snap: TranscriptSnapshot, partials: list[str]) -> str:
        joined = "\n\n---\n\n".join(partials)
        return self._chat_client.complete(
            ChatCompletionRequest(
                system_prompt=_system_prompt(self._output_language, snap.transcript.language.code, self._disable_thinking),
                user_prompt=_synthesis_prompt(snap, joined),
            )
        )

    def _output_path(self, slug: str, output_base_path: Path) -> Path:
        if output_base_path.name:
            filename = f"{output_base_path.stem}.summary.md"
        else:
            filename = f"{slug}.summary.md"
        return self._output_dir / filename


def _system_prompt(output_language: str, transcript_language: str, disable_thinking: bool = True) -> str:
    language_instruction = (
        "Responda no mesmo idioma predominante da transcrição."
        if output_language == "auto"
        else f"Responda em {output_language}."
    )
    no_thinking_instruction = (
        "Responda diretamente. Não gere cadeia de raciocínio, não inclua análise interna "
        "e não use blocos <think>. "
        if disable_thinking
        else ""
    )
    return (
        "Você é um assistente acadêmico-técnico especializado em resumir transcrições de vídeos. "
        f"{no_thinking_instruction}"
        "Não invente informações ausentes. Diferencie explicitamente o que foi dito no vídeo de inferências. "
        "Preserve timestamps quando mencionar trechos específicos. "
        "Use Markdown claro e útil para revisão humana. "
        f"Idioma da transcrição: {transcript_language}. {language_instruction}"
    )


def _single_pass_prompt(snap: TranscriptSnapshot, transcript_text: str) -> str:
    return (
        f"Gere um resumo estruturado do vídeo \"{snap.metadata.title}\".\n\n"
        "A saída deve conter exatamente estas seções:\n"
        "## Resumo executivo\n"
        "## Tese ou ideia central\n"
        "## Tópicos principais\n"
        "## Índice temático com timestamps\n"
        "## Conceitos e termos técnicos\n"
        "## Pontos acionáveis\n"
        "## Trechos que merecem revisão humana\n"
        "## Limitações do resumo\n\n"
        "Transcrição com timestamps:\n"
        f"{transcript_text}"
    )


def _chunk_prompt(snap: TranscriptSnapshot, chunk: str, index: int, total: int) -> str:
    return (
        f"Este é o bloco {index}/{total} da transcrição do vídeo \"{snap.metadata.title}\".\n"
        "Resuma apenas este bloco, preservando timestamps úteis e sem concluir além do trecho recebido.\n"
        "Use seções curtas: Tópicos, Timestamps importantes, Conceitos, Pontos de atenção.\n\n"
        f"Bloco {index}/{total}:\n{chunk}"
    )


def _synthesis_prompt(snap: TranscriptSnapshot, partials: str) -> str:
    return (
        f"A seguir estão resumos parciais do vídeo \"{snap.metadata.title}\".\n"
        "Sintetize em um resumo final sem duplicar tópicos. Preserve timestamps úteis.\n\n"
        "A saída deve conter exatamente estas seções:\n"
        "## Resumo executivo\n"
        "## Tese ou ideia central\n"
        "## Tópicos principais\n"
        "## Índice temático com timestamps\n"
        "## Conceitos e termos técnicos\n"
        "## Pontos acionáveis\n"
        "## Trechos que merecem revisão humana\n"
        "## Limitações do resumo\n\n"
        f"Resumos parciais:\n{partials}"
    )


def _snapshot_to_text(snap: TranscriptSnapshot, aliases: Mapping[str, str]) -> str:
    lines: list[str] = []
    for segment in snap.transcript.segments:
        text = _clean_text(segment.text)
        if not text:
            continue
        speaker = _speaker(segment, aliases)
        lines.append(f"[{_hms(segment.start_seconds)} — {_hms(segment.end_seconds)}] {speaker}: {text}")
    return "\n".join(lines)


def _speaker(segment: TranscriptSegment, aliases: Mapping[str, str]) -> str:
    alias = aliases.get(segment.speaker_label, "").strip()
    return alias or segment.speaker_label


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


_PROMPT_TOKEN_RESERVE = 900


def _effective_chunk_chars(
    *, max_chars_per_chunk: int, max_input_tokens: int, chars_per_token: float
) -> int:
    """Retorna um limite conservador de caracteres por bloco.

    LM Studio/llama.cpp valida a quantidade de tokens do prompt contra
    ``n_ctx_slot`` antes de começar a gerar. Como nem sempre temos o tokenizer
    exato do modelo local, usamos uma estimativa conservadora. Para Qwen e
    português/inglês técnico, ``2.0`` caracteres/token é intencionalmente
    prudente.

    ``max_input_tokens`` é o orçamento total estimado do prompt. Reservamos
    parte dele para instruções, metadados e cabeçalhos, deixando o restante para
    a transcrição propriamente dita.
    """

    transcript_token_budget = max(256, max_input_tokens - _PROMPT_TOKEN_RESERVE)
    token_based_chars = int(transcript_token_budget * chars_per_token)
    return max(500, min(max_chars_per_chunk, token_based_chars))


def _chunk_text(text: str, max_chars: int) -> list[str]:
    lines = [line for line in text.splitlines() if line.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for line in lines:
        line_size = len(line) + 1
        if current and current_size + line_size > max_chars:
            chunks.append("\n".join(current))
            current = []
            current_size = 0
        # Se uma única linha ultrapassar o orçamento, divida preservando o
        # timestamp/falante quando possível. Isso evita prompts enormes quando
        # a transcrição tem um segmento muito longo.
        if line_size > max_chars:
            if current:
                chunks.append("\n".join(current))
                current = []
                current_size = 0
            chunks.extend(_split_long_line(line, max_chars))
            continue
        current.append(line)
        current_size += line_size
    if current:
        chunks.append("\n".join(current))
    return chunks


def _split_long_line(line: str, max_chars: int) -> list[str]:
    if len(line) <= max_chars:
        return [line]
    prefix = ""
    body = line
    match = re.match(r"^(\[[^\]]+\]\s+[^:]+:\s+)(.*)$", line)
    if match:
        prefix = match.group(1)
        body = match.group(2)
    available = max(200, max_chars - len(prefix) - 20)
    parts: list[str] = []
    start = 0
    while start < len(body):
        end = min(len(body), start + available)
        if end < len(body):
            split_at = body.rfind(". ", start, end)
            if split_at <= start:
                split_at = body.rfind(" ", start, end)
            if split_at > start:
                end = split_at + 1
        chunk = body[start:end].strip()
        if chunk:
            parts.append(f"{prefix}{chunk}" if prefix else chunk)
        start = end
    return parts


def _wrap_summary_markdown(
    snap: TranscriptSnapshot, body: str, *, model: str, chunks: int
) -> str:
    m = snap.metadata
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    return (
        f"# Resumo — {m.title}\n\n"
        f"**URL**: {m.canonical_url()}\n"
        f"**Canal**: {m.channel}\n"
        f"**Duração**: {m.duration.to_hms()}\n"
        f"**Idioma da transcrição**: {snap.transcript.language.code}\n"
        f"**Fonte da transcrição**: {snap.context.transcription_source}\n"
        f"**Modelo de transcrição**: {snap.context.whisper_model}\n"
        f"**Modelo de sumarização**: {model}\n"
        f"**Blocos usados na sumarização**: {chunks}\n"
        f"**Data do resumo**: {generated_at}\n\n"
        "---\n\n"
        f"{body.strip()}\n\n"
        "---\n\n"
        "> Resumo gerado automaticamente a partir da transcrição. "
        "Consulte a transcrição original em caso de dúvida.\n"
    )


def _hms(seconds: float) -> str:
    total = max(0, int(seconds))
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"
