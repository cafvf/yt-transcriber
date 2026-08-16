from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from yt_transcriber_bot.application.ports.canonical_transcript import CanonicalTranscriptStore
from yt_transcriber_bot.application.ports.text_generation import TextGenerationClient, TextTokenizer
from yt_transcriber_bot.application.services.transcript_summary import (
    SummaryError,
    SummaryProgress,
)
from yt_transcriber_bot.application.services.transcript_summary import (
    TranscriptSummaryService as ApplicationTranscriptSummaryService,
)
from yt_transcriber_bot.infrastructure.summarization.tokenizer import (
    _make_tokenizer,
    make_text_tokenizer,
)


@dataclass(frozen=True)
class SummaryResult:
    path: Path
    chunks: int
    model: str


class TranscriptSummaryService:
    def __init__(
        self,
        *,
        snapshots: CanonicalTranscriptStore,
        chat_client: TextGenerationClient,
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
        self._output_dir = output_dir
        resolved = tokenizer or make_text_tokenizer(
            backend=tokenizer_backend,
            model=tokenizer_model.strip() or chat_client.model,
            chars_per_token=chars_per_token,
            trust_remote_code=tokenizer_trust_remote_code,
        )
        self._policy = ApplicationTranscriptSummaryService(
            snapshots=snapshots,
            chat_client=chat_client,
            output_dir=output_dir,
            max_chars_per_chunk=max_chars_per_chunk,
            max_input_tokens=max_input_tokens,
            chars_per_token=chars_per_token,
            partial_max_tokens=partial_max_tokens,
            final_max_tokens=final_max_tokens,
            timeout_split_retries=timeout_split_retries,
            output_language=output_language,
            disable_thinking=disable_thinking,
            tokenizer_backend=tokenizer_backend,
            tokenizer_model=tokenizer_model,
            tokenizer_trust_remote_code=tokenizer_trust_remote_code,
            tokenizer=resolved,
            deduplicate_transcript=deduplicate_transcript,
            merge_same_speaker_gap_s=merge_same_speaker_gap_s,
            min_overlap_words=min_overlap_words,
        )

    def summarize(
        self,
        *,
        slug: str,
        output_base_path: Path,
        speaker_aliases: Mapping[str, str] | None = None,
        on_progress: Callable[[SummaryProgress], None] | None = None,
    ) -> SummaryResult:
        result = self._policy.summarize(
            slug=slug,
            output_base_path=output_base_path,
            speaker_aliases=speaker_aliases,
            on_progress=on_progress,
        )
        name = (
            f"{output_base_path.stem}.summary.md" if output_base_path.name else f"{slug}.summary.md"
        )
        path = self._output_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result.content, encoding="utf-8")
        return SummaryResult(path=path, chunks=result.chunks, model=result.model)


__all__ = [
    "SummaryError",
    "SummaryProgress",
    "SummaryResult",
    "TextTokenizer",
    "TranscriptSummaryService",
    "_make_tokenizer",
    "make_text_tokenizer",
]
