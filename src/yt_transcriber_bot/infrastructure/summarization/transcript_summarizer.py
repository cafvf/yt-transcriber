"""Sumarização de transcrições persistidas em snapshots.

O serviço não reprocessa áudio. Ele carrega o snapshot JSON já salvo, reconstrói
um texto limpo com timestamps e chama uma LLM local/remota via um cliente de
chat completion. Para transcrições longas, usa uma estratégia simples de
map-reduce: resume blocos e depois sintetiza os resumos parciais.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast

from yt_transcriber_bot.domain.entities.transcript import TranscriptSegment
from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
    TranscriptSnapshot,
    TranscriptSnapshotRepository,
)
from yt_transcriber_bot.infrastructure.summarization.openai_compatible_client import (
    ChatCompletionError,
    ChatCompletionRequest,
    ChatCompletionTimeoutError,
)
from yt_transcriber_bot.infrastructure.text.normalization import normalize_artifact_text


class SummaryError(RuntimeError):
    """Falha de sumarização ou configuração."""


class ChatCompletionClient(Protocol):
    """Contrato mínimo necessário para gerar resumos."""

    @property
    def model(self) -> str: ...

    def complete(self, request: ChatCompletionRequest) -> str: ...


class TextTokenizer(Protocol):
    """Contador/divisor de tokens usado para montar chunks de entrada."""

    @property
    def description(self) -> str: ...

    @property
    def is_exact(self) -> bool: ...

    def count(self, text: str) -> int: ...

    def split(self, text: str, max_tokens: int) -> list[str]: ...


class _TokenizerCodec(Protocol):
    def encode(
        self, text: str, *, add_special_tokens: bool = False
    ) -> list[int] | tuple[int, ...]: ...

    def decode(
        self,
        token_ids: list[int],
        *,
        skip_special_tokens: bool = True,
        clean_up_tokenization_spaces: bool = False,
    ) -> str: ...


@dataclass(frozen=True)
class SummaryResult:
    """Resultado de geração do resumo."""

    path: Path
    chunks: int
    model: str


@dataclass(frozen=True)
class SummaryProgress:
    """Evento de progresso emitido durante a sumarização."""

    kind: str
    current: int
    total: int
    message: str


@dataclass
class _SummaryTurn:
    start_seconds: float
    end_seconds: float
    speaker: str
    text: str


class TranscriptSummaryService:
    """Gera um resumo estruturado em Markdown a partir de um snapshot."""

    def __init__(
        self,
        *,
        snapshots: TranscriptSnapshotRepository,
        chat_client: ChatCompletionClient,
        output_dir: Path,
        max_chars_per_chunk: int = 18_000,
        max_input_tokens: int = 6_000,
        chars_per_token: float = 2.5,
        partial_max_tokens: int = 512,
        final_max_tokens: int = 1024,
        timeout_split_retries: int = 2,
        output_language: str = "auto",
        disable_thinking: bool = True,
        tokenizer_backend: str = "auto",
        tokenizer_model: str = "",
        tokenizer_trust_remote_code: bool = False,
        tokenizer: TextTokenizer | None = None,
        deduplicate_transcript: bool = True,
        merge_same_speaker_gap_s: float = 2.0,
        min_overlap_words: int = 6,
    ) -> None:
        self._snapshots = snapshots
        self._chat_client = chat_client
        self._output_dir = output_dir
        self._max_chars_per_chunk = max(1_000, max_chars_per_chunk)
        self._max_input_tokens = max(512, max_input_tokens)
        self._chars_per_token = max(1.0, chars_per_token)
        self._partial_max_tokens = max(1, partial_max_tokens)
        self._final_max_tokens = max(1, final_max_tokens)
        self._timeout_split_retries = max(0, timeout_split_retries)
        self._output_language = output_language.strip().lower() or "auto"
        self._disable_thinking = disable_thinking
        self._tokenizer_backend = tokenizer_backend.strip().lower() or "auto"
        self._tokenizer_model = tokenizer_model.strip() or chat_client.model
        self._tokenizer_trust_remote_code = tokenizer_trust_remote_code
        self._tokenizer = tokenizer or _make_tokenizer(
            backend=self._tokenizer_backend,
            model=self._tokenizer_model,
            chars_per_token=self._chars_per_token,
            trust_remote_code=self._tokenizer_trust_remote_code,
        )
        self._deduplicate_transcript = deduplicate_transcript
        self._merge_same_speaker_gap_s = max(0.0, merge_same_speaker_gap_s)
        self._min_overlap_words = max(2, min_overlap_words)

    def summarize(
        self,
        *,
        slug: str,
        output_base_path: Path,
        speaker_aliases: Mapping[str, str] | None = None,
        on_progress: Callable[[SummaryProgress], None] | None = None,
    ) -> SummaryResult:
        snap = self._snapshots.load(slug)
        if snap is None:
            raise FileNotFoundError(f"Snapshot inexistente: {slug}")
        transcript_text = _snapshot_to_text(
            snap,
            speaker_aliases or {},
            deduplicate=self._deduplicate_transcript,
            merge_same_speaker_gap_s=self._merge_same_speaker_gap_s,
            min_overlap_words=self._min_overlap_words,
        )
        chunks = _chunk_text(
            transcript_text,
            max_chars_per_chunk=self._max_chars_per_chunk,
            max_input_tokens=self._max_input_tokens,
            chars_per_token=self._chars_per_token,
            tokenizer=self._tokenizer,
        )
        if not chunks:
            raise SummaryError("Snapshot não contém texto suficiente para sumarizar.")
        _emit_summary_progress(
            on_progress,
            kind="planned",
            current=0,
            total=len(chunks),
            message=(
                f"Transcrição preparada em {len(chunks)} bloco(s). "
                f"Tokenizer: {self._tokenizer.description}."
            ),
        )
        effective_chunks = len(chunks)
        try:
            if len(chunks) == 1:
                _emit_summary_progress(
                    on_progress,
                    kind="single_started",
                    current=1,
                    total=1,
                    message="Enviando transcrição completa para a LLM.",
                )
                try:
                    summary_body = self._summarize_single(snap, chunks[0])
                except ChatCompletionTimeoutError:
                    if self._timeout_split_retries <= 0:
                        raise
                    _emit_summary_progress(
                        on_progress,
                        kind="chunk_split",
                        current=1,
                        total=1,
                        message=(
                            "A chamada única excedeu o timeout. "
                            "Dividindo a transcrição e tentando novamente."
                        ),
                    )
                    retry_chunks = self._split_chunk_after_timeout(chunks[0])
                    if len(retry_chunks) <= 1:
                        raise
                    retry_partials: list[str] = []
                    for sub_index, retry_chunk in enumerate(retry_chunks, 1):
                        retry_partials.extend(
                            self._summarize_chunk_adaptively(
                                snap=snap,
                                chunk=retry_chunk,
                                label=f"1.{sub_index}",
                                current=1,
                                total=1,
                                retries_left=self._timeout_split_retries - 1,
                                on_progress=on_progress,
                            )
                        )
                    effective_chunks = len(retry_partials)
                    _emit_summary_progress(
                        on_progress,
                        kind="synthesis_started",
                        current=effective_chunks,
                        total=effective_chunks,
                        message="Subdivisões resumidas. Gerando síntese final.",
                    )
                    summary_body = self._synthesize_partials_adaptively(
                        snap, retry_partials, self._timeout_split_retries, on_progress
                    )
                    _emit_summary_progress(
                        on_progress,
                        kind="synthesis_completed",
                        current=effective_chunks,
                        total=effective_chunks,
                        message="Síntese final concluída.",
                    )
                else:
                    _emit_summary_progress(
                        on_progress,
                        kind="single_completed",
                        current=1,
                        total=1,
                        message="Resumo em passagem única concluído.",
                    )
            else:
                partials: list[str] = []
                for i, chunk in enumerate(chunks, 1):
                    partials.extend(
                        self._summarize_chunk_adaptively(
                            snap=snap,
                            chunk=chunk,
                            label=str(i),
                            current=i,
                            total=len(chunks),
                            retries_left=self._timeout_split_retries,
                            on_progress=on_progress,
                        )
                    )
                effective_chunks = len(partials)
                _emit_summary_progress(
                    on_progress,
                    kind="synthesis_started",
                    current=effective_chunks,
                    total=effective_chunks,
                    message="Resumos parciais concluídos. Gerando síntese final.",
                )
                summary_body = self._synthesize_partials_adaptively(
                    snap, partials, self._timeout_split_retries, on_progress
                )
                _emit_summary_progress(
                    on_progress,
                    kind="synthesis_completed",
                    current=effective_chunks,
                    total=effective_chunks,
                    message="Síntese final concluída.",
                )
        except ChatCompletionError:
            raise
        except Exception as exc:  # pragma: no cover - camada defensiva
            raise SummaryError(f"Falha inesperada na sumarização: {exc}") from exc
        cleaned_summary_body = _clean_summary_markdown(summary_body)
        output_path = self._output_path(slug, output_base_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            _wrap_summary_markdown(
                snap,
                cleaned_summary_body,
                model=self._chat_client.model,
                chunks=effective_chunks,
                tokenizer_description=self._tokenizer.description,
                deduplicated=self._deduplicate_transcript,
            ),
            encoding="utf-8",
        )
        return SummaryResult(
            path=output_path, chunks=effective_chunks, model=self._chat_client.model
        )

    def _summarize_chunk_adaptively(
        self,
        *,
        snap: TranscriptSnapshot,
        chunk: str,
        label: str,
        current: int,
        total: int,
        retries_left: int,
        on_progress: Callable[[SummaryProgress], None] | None,
    ) -> list[str]:
        estimated_tokens = self._tokenizer.count(chunk)
        _emit_summary_progress(
            on_progress,
            kind="chunk_started",
            current=current,
            total=total,
            message=(
                f"Iniciando resumo parcial {label}/{total} "
                f"(~{estimated_tokens} tokens de transcrição)."
            ),
        )
        try:
            partial = self._summarize_chunk(snap, chunk, label, total)
        except ChatCompletionTimeoutError:
            if retries_left <= 0:
                raise
            subchunks = self._split_chunk_after_timeout(chunk)
            if len(subchunks) <= 1:
                raise
            _emit_summary_progress(
                on_progress,
                kind="chunk_split",
                current=current,
                total=total,
                message=(
                    f"Resumo parcial {label}/{total} excedeu o timeout. "
                    f"Subdividindo em {len(subchunks)} parte(s) menores."
                ),
            )
            partials: list[str] = []
            for sub_index, subchunk in enumerate(subchunks, 1):
                partials.extend(
                    self._summarize_chunk_adaptively(
                        snap=snap,
                        chunk=subchunk,
                        label=f"{label}.{sub_index}",
                        current=current,
                        total=total,
                        retries_left=retries_left - 1,
                        on_progress=on_progress,
                    )
                )
            return partials
        _emit_summary_progress(
            on_progress,
            kind="chunk_completed",
            current=current,
            total=total,
            message=f"Resumo parcial {label}/{total} concluído.",
        )
        return [partial]

    def _split_chunk_after_timeout(self, chunk: str) -> list[str]:
        """Divide um chunk problemático de forma conservadora após timeout.

        A divisão usa aproximadamente metade do orçamento atual. Isso reduz o
        tempo de ingestão do prompt e de geração sem alterar globalmente a
        configuração do operador durante a execução em andamento.
        """

        current_tokens = max(1, self._tokenizer.count(chunk))
        retry_transcript_tokens = max(256, current_tokens // 2)
        retry_input_tokens = max(512, retry_transcript_tokens + _PROMPT_TOKEN_RESERVE)
        retry_chars = max(500, min(self._max_chars_per_chunk // 2, len(chunk) // 2 + 1))
        subchunks = _chunk_text(
            chunk,
            max_chars_per_chunk=retry_chars,
            max_input_tokens=retry_input_tokens,
            chars_per_token=self._chars_per_token,
            tokenizer=self._tokenizer,
        )
        if len(subchunks) <= 1 and len(chunk) > 500:
            midpoint = len(chunk) // 2
            split_at = chunk.rfind("\n", 0, midpoint)
            if split_at <= 0:
                split_at = chunk.rfind(". ", 0, midpoint)
            if split_at <= 0:
                split_at = midpoint
            subchunks = [chunk[:split_at].strip(), chunk[split_at:].strip()]
        return [part for part in subchunks if part.strip()]

    def _synthesize_partials_adaptively(
        self,
        snap: TranscriptSnapshot,
        partials: list[str],
        retries_left: int,
        on_progress: Callable[[SummaryProgress], None] | None,
    ) -> str:
        try:
            return self._synthesize_partials(snap, partials)
        except ChatCompletionTimeoutError:
            if retries_left <= 0 or len(partials) <= 1:
                raise
            midpoint = max(1, len(partials) // 2)
            _emit_summary_progress(
                on_progress,
                kind="synthesis_split",
                current=len(partials),
                total=len(partials),
                message=(
                    "A síntese final excedeu o timeout. "
                    "Sintetizando os resumos parciais em grupos menores."
                ),
            )
            left = self._synthesize_partials_adaptively(
                snap, partials[:midpoint], retries_left - 1, on_progress
            )
            right = self._synthesize_partials_adaptively(
                snap, partials[midpoint:], retries_left - 1, on_progress
            )
            return self._synthesize_partials_adaptively(
                snap, [left, right], retries_left - 1, on_progress
            )

    def _summarize_single(self, snap: TranscriptSnapshot, transcript_text: str) -> str:
        return self._chat_client.complete(
            ChatCompletionRequest(
                system_prompt=_system_prompt(
                    self._output_language, _transcript_language_code(snap), self._disable_thinking
                ),
                user_prompt=_single_pass_prompt(snap, transcript_text),
                max_tokens=self._final_max_tokens,
            )
        )

    def _summarize_chunk(
        self, snap: TranscriptSnapshot, chunk: str, index: str | int, total: str | int
    ) -> str:
        return self._chat_client.complete(
            ChatCompletionRequest(
                system_prompt=_system_prompt(
                    self._output_language, _transcript_language_code(snap), self._disable_thinking
                ),
                user_prompt=_chunk_prompt(snap, chunk, index, total),
                max_tokens=self._partial_max_tokens,
            )
        )

    def _synthesize_partials(self, snap: TranscriptSnapshot, partials: list[str]) -> str:
        joined = "\n\n---\n\n".join(partials)
        return self._chat_client.complete(
            ChatCompletionRequest(
                system_prompt=_system_prompt(
                    self._output_language, _transcript_language_code(snap), self._disable_thinking
                ),
                user_prompt=_synthesis_prompt(snap, joined),
                max_tokens=self._final_max_tokens,
            )
        )

    def _output_path(self, slug: str, output_base_path: Path) -> Path:
        if output_base_path.name:
            filename = f"{output_base_path.stem}.summary.md"
        else:
            filename = f"{slug}.summary.md"
        return self._output_dir / filename


def _emit_summary_progress(
    callback: Callable[[SummaryProgress], None] | None,
    *,
    kind: str,
    current: int,
    total: int,
    message: str,
) -> None:
    if callback is None:
        return
    callback(SummaryProgress(kind=kind, current=current, total=total, message=message))


def _system_prompt(
    output_language: str, transcript_language: str, disable_thinking: bool = True
) -> str:
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
        f'Gere um resumo estruturado do vídeo "{snap.metadata.title}".\n\n'
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


def _chunk_prompt(snap: TranscriptSnapshot, chunk: str, index: str | int, total: str | int) -> str:
    return (
        f'Este é o bloco {index}/{total} da transcrição do vídeo "{snap.metadata.title}".\n'
        "Resuma apenas este bloco, preservando timestamps úteis e sem concluir além do trecho recebido.\n"
        "Use seções curtas: Tópicos, Timestamps importantes, Conceitos, Pontos de atenção.\n\n"
        f"Bloco {index}/{total}:\n{chunk}"
    )


def _synthesis_prompt(snap: TranscriptSnapshot, partials: str) -> str:
    return (
        f'A seguir estão resumos parciais do vídeo "{snap.metadata.title}".\n'
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


def _snapshot_to_text(
    snap: TranscriptSnapshot,
    aliases: Mapping[str, str],
    *,
    deduplicate: bool = True,
    merge_same_speaker_gap_s: float = 2.0,
    min_overlap_words: int = 6,
) -> str:
    turns: list[_SummaryTurn] = []
    previous_text = ""
    for segment in snap.transcript.segments:
        if segment.end_seconds <= segment.start_seconds:
            continue
        text = _clean_text(segment.text)
        if not text:
            continue
        if deduplicate:
            text = _deduplicate_text(
                previous_text=previous_text,
                current_text=text,
                min_overlap_words=min_overlap_words,
            )
        if not text:
            continue
        speaker = _speaker(segment, aliases)
        if _can_merge_with_previous_turn(turns, speaker, segment, merge_same_speaker_gap_s):
            previous = turns[-1]
            previous.end_seconds = max(previous.end_seconds, segment.end_seconds)
            previous.text = _join_turn_text(previous.text, text)
        else:
            turns.append(
                _SummaryTurn(
                    start_seconds=segment.start_seconds,
                    end_seconds=segment.end_seconds,
                    speaker=speaker,
                    text=text,
                )
            )
        previous_text = _clean_text(segment.text)
    return "\n".join(
        f"[{_hms(turn.start_seconds)} — {_hms(turn.end_seconds)}] {turn.speaker}: {turn.text}"
        for turn in turns
    )


def _can_merge_with_previous_turn(
    turns: list[_SummaryTurn], speaker: str, segment: TranscriptSegment, max_gap_s: float
) -> bool:
    if not turns:
        return False
    previous = turns[-1]
    gap_s = max(0.0, segment.start_seconds - previous.end_seconds)
    return previous.speaker == speaker and gap_s <= max_gap_s


def _join_turn_text(left: str, right: str) -> str:
    if not left:
        return right
    if not right:
        return left
    separator = "" if left.endswith((" ", "\n")) else " "
    return f"{left}{separator}{right}".strip()


def _speaker(segment: TranscriptSegment, aliases: Mapping[str, str]) -> str:
    alias = aliases.get(segment.speaker_label, "").strip()
    return alias or segment.speaker_label


def _clean_text(text: str) -> str:
    return normalize_artifact_text(text)


def _clean_summary_markdown(text: str) -> str:
    """Repara mojibake/unicode preservando a estrutura Markdown.

    Não usa ``normalize_artifact_text`` no documento inteiro porque essa função
    colapsa whitespace e destruiria quebras de linha, listas e títulos.
    """

    cleaned_lines: list[str] = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            cleaned_lines.append(line.rstrip())
            continue
        if in_fence or not stripped:
            cleaned_lines.append(line.rstrip())
            continue
        leading = line[: len(line) - len(line.lstrip())]
        trailing = line[len(line.rstrip()) :]
        cleaned_lines.append(f"{leading}{normalize_artifact_text(stripped)}{trailing}")
    return "\n".join(cleaned_lines).strip()


_PROMPT_TOKEN_RESERVE = 900


class _EstimatedTokenizer:
    def __init__(self, *, chars_per_token: float) -> None:
        self._chars_per_token = max(1.0, chars_per_token)

    @property
    def description(self) -> str:
        return f"estimativa por caracteres ({self._chars_per_token:.2f} chars/token)"

    @property
    def is_exact(self) -> bool:
        return False

    def count(self, text: str) -> int:
        if not text:
            return 0
        return max(1, math.ceil(len(text) / self._chars_per_token))

    def split(self, text: str, max_tokens: int) -> list[str]:
        max_chars = max(200, int(max_tokens * self._chars_per_token))
        return _split_text_by_chars(text, max_chars)


class _HuggingFaceTokenizer:
    def __init__(self, *, model: str, tokenizer: _TokenizerCodec) -> None:
        self._model = model
        self._tokenizer = tokenizer

    @property
    def description(self) -> str:
        return f"Hugging Face tokenizer local ({self._model})"

    @property
    def is_exact(self) -> bool:
        return True

    def count(self, text: str) -> int:
        if not text:
            return 0
        return len(self._encode(text))

    def split(self, text: str, max_tokens: int) -> list[str]:
        token_ids = self._encode(text)
        if len(token_ids) <= max_tokens:
            return [text]
        parts: list[str] = []
        for start in range(0, len(token_ids), max_tokens):
            part_ids = token_ids[start : start + max_tokens]
            decoded = self._decode(part_ids).strip()
            if decoded:
                parts.append(decoded)
        return parts

    def _encode(self, text: str) -> list[int]:
        encoded = self._tokenizer.encode(text, add_special_tokens=False)
        return list(encoded)

    def _decode(self, token_ids: list[int]) -> str:
        return str(
            self._tokenizer.decode(
                token_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )
        )


def _make_tokenizer(
    *, backend: str, model: str, chars_per_token: float, trust_remote_code: bool = False
) -> TextTokenizer:
    backend = backend.strip().lower() or "auto"
    if backend not in {"auto", "hf", "huggingface", "estimate", "estimated"}:
        raise SummaryError(
            "SUMMARY_TOKENIZER_BACKEND inválido. Use auto, hf ou estimate. "
            f"Valor recebido: {backend!r}."
        )
    if backend in {"estimate", "estimated"}:
        return _EstimatedTokenizer(chars_per_token=chars_per_token)

    try:
        from transformers import AutoTokenizer

        from_pretrained = cast(Callable[..., _TokenizerCodec], AutoTokenizer.from_pretrained)
        tokenizer = from_pretrained(
            model,
            local_files_only=True,
            trust_remote_code=trust_remote_code,
        )
        return _HuggingFaceTokenizer(model=model, tokenizer=tokenizer)
    except Exception as exc:
        if backend in {"hf", "huggingface"}:
            raise SummaryError(
                "Não foi possível carregar o tokenizer Hugging Face local para SUMMARY_TOKENIZER_MODEL "
                f"ou SUMMARY_MODEL ({model!r}). Baixe/cacheie o tokenizer localmente ou use "
                "SUMMARY_TOKENIZER_BACKEND=estimate. Detalhe: "
                f"{exc}"
            ) from exc
        return _EstimatedTokenizer(chars_per_token=chars_per_token)


def _effective_chunk_tokens(max_input_tokens: int) -> int:
    return max(256, max_input_tokens - _PROMPT_TOKEN_RESERVE)


def _effective_chunk_chars(
    *, max_chars_per_chunk: int, max_input_tokens: int, chars_per_token: float
) -> int:
    """Retorna o limite de caracteres usado pelo fallback estimado."""

    transcript_token_budget = _effective_chunk_tokens(max_input_tokens)
    token_based_chars = int(transcript_token_budget * chars_per_token)
    return max(500, min(max_chars_per_chunk, token_based_chars))


def _chunk_text(
    text: str,
    max_chars: int | None = None,
    *,
    max_chars_per_chunk: int | None = None,
    max_input_tokens: int | None = None,
    chars_per_token: float = 2.0,
    tokenizer: TextTokenizer | None = None,
) -> list[str]:
    if max_chars is not None:
        effective_max_chars = max_chars
        tokenizer = _EstimatedTokenizer(chars_per_token=chars_per_token)
        token_budget = max(256, math.ceil(effective_max_chars / max(1.0, chars_per_token)))
    else:
        if max_chars_per_chunk is None or max_input_tokens is None:
            raise TypeError("Informe max_chars ou max_chars_per_chunk + max_input_tokens.")
        tokenizer = tokenizer or _EstimatedTokenizer(chars_per_token=chars_per_token)
        token_budget = _effective_chunk_tokens(max_input_tokens)
        effective_max_chars = _effective_chunk_chars(
            max_chars_per_chunk=max_chars_per_chunk,
            max_input_tokens=max_input_tokens,
            chars_per_token=chars_per_token,
        )
    lines = [line for line in text.splitlines() if line.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0
    current_chars = 0
    for line in lines:
        line_tokens = tokenizer.count(line) + 1
        line_size = len(line) + 1
        exceeds_token_budget = current and current_tokens + line_tokens > token_budget
        exceeds_char_budget = current and current_chars + line_size > effective_max_chars
        if exceeds_token_budget or exceeds_char_budget:
            chunks.append("\n".join(current))
            current = []
            current_tokens = 0
            current_chars = 0
        if line_tokens > token_budget or line_size > effective_max_chars:
            if current:
                chunks.append("\n".join(current))
                current = []
                current_tokens = 0
                current_chars = 0
            chunks.extend(
                _split_long_line(
                    line,
                    max_chars=effective_max_chars,
                    max_tokens=token_budget,
                    tokenizer=tokenizer,
                )
            )
            continue
        current.append(line)
        current_tokens += line_tokens
        current_chars += line_size
    if current:
        chunks.append("\n".join(current))
    return chunks


def _split_long_line(
    line: str,
    max_chars: int,
    *,
    max_tokens: int | None = None,
    tokenizer: TextTokenizer | None = None,
) -> list[str]:
    if len(line) <= max_chars and (
        tokenizer is None or max_tokens is None or tokenizer.count(line) <= max_tokens
    ):
        return [line]
    prefix = ""
    body = line
    match = re.match(r"^(\[[^\]]+\]\s+[^:]+:\s+)(.*)$", line)
    if match:
        prefix = match.group(1)
        body = match.group(2)
    available_chars = max(200, max_chars - len(prefix) - 20)
    if tokenizer is not None and max_tokens is not None:
        available_tokens = max(64, max_tokens - tokenizer.count(prefix) - 8)
        body_parts = tokenizer.split(body, available_tokens)
        parts: list[str] = []
        for body_part in body_parts:
            parts.extend(_split_text_by_chars(body_part, available_chars))
        return [f"{prefix}{part}" if prefix else part for part in parts if part.strip()]
    return [
        f"{prefix}{part}" if prefix else part
        for part in _split_text_by_chars(body, available_chars)
    ]


def _split_text_by_chars(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text.strip()] if text.strip() else []
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        if end < len(text):
            split_at = text.rfind(". ", start, end)
            if split_at <= start:
                split_at = text.rfind(" ", start, end)
            if split_at > start:
                end = split_at + 1
        chunk = text[start:end].strip()
        if chunk:
            parts.append(chunk)
        start = max(end, start + 1)
    return parts


def _deduplicate_text(*, previous_text: str, current_text: str, min_overlap_words: int) -> str:
    current_text = _drop_adjacent_duplicate_sentences(current_text)
    if not previous_text:
        return current_text
    if _normalized_words(previous_text) == _normalized_words(current_text):
        return ""
    return _remove_repeated_prefix(
        previous_text=previous_text,
        current_text=current_text,
        min_overlap_words=min_overlap_words,
    )


def _drop_adjacent_duplicate_sentences(text: str) -> str:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    if len(sentences) <= 1:
        return text
    kept: list[str] = []
    previous_key: tuple[str, ...] = ()
    for sentence in sentences:
        key = _normalized_words(sentence)
        if key and key == previous_key:
            continue
        kept.append(sentence)
        previous_key = key
    return " ".join(kept).strip()


def _remove_repeated_prefix(
    *, previous_text: str, current_text: str, min_overlap_words: int
) -> str:
    previous_words = _word_spans(previous_text)
    current_words = _word_spans(current_text)
    if len(previous_words) < min_overlap_words or len(current_words) < min_overlap_words:
        return current_text
    previous_keys = [word for word, _, _ in previous_words]
    current_keys = [word for word, _, _ in current_words]
    max_overlap = min(len(previous_keys), len(current_keys), 80)
    for overlap in range(max_overlap, min_overlap_words - 1, -1):
        if previous_keys[-overlap:] == current_keys[:overlap]:
            cut_at = current_words[overlap - 1][2]
            return re.sub(r"^[ ,.;:\u2014\u2013-]+", "", current_text[cut_at:])
    return current_text


def _normalized_words(text: str) -> tuple[str, ...]:
    return tuple(word for word, _, _ in _word_spans(text))


def _word_spans(text: str) -> list[tuple[str, int, int]]:
    return [
        (match.group(0).lower(), match.start(), match.end())
        for match in re.finditer(r"[\wÀ-ÿ]+", text, flags=re.UNICODE)
    ]


def _transcript_language_code(snap: TranscriptSnapshot) -> str:
    """Retorna o idioma conhecido sem fabricar um fato ausente."""

    return snap.transcript.language.code if snap.transcript.language else "desconhecido"


def _wrap_summary_markdown(
    snap: TranscriptSnapshot,
    body: str,
    *,
    model: str,
    chunks: int,
    tokenizer_description: str = "estimativa por caracteres",
    deduplicated: bool = True,
) -> str:
    m = snap.metadata
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    duration = m.duration.to_hms() if m.duration else "desconhecida"
    language = _transcript_language_code(snap)
    source_line = (
        f"**URL**: {m.canonical_url()}\n"
        if m.source_label == "YouTube"
        else f"**Origem**: {m.source_label}\n"
    )
    return (
        f"# Resumo — {m.title}\n\n"
        f"{source_line}"
        f"**Canal**: {m.channel}\n"
        f"**Duração**: {duration}\n"
        f"**Idioma da transcrição**: {language}\n"
        f"**Fonte da transcrição**: {snap.context.transcription_source}\n"
        f"**Modelo de transcrição**: {snap.context.whisper_model}\n"
        f"**Modelo de sumarização**: {model}\n"
        f"**Blocos usados na sumarização**: {chunks}\n"
        f"**Tokenização para chunking**: {tokenizer_description}\n"
        f"**Deduplicação pré-resumo**: {'ativada' if deduplicated else 'desativada'}\n"
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
