from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, cast

from yt_transcriber_bot.application.ports.text_generation import TextTokenizer
from yt_transcriber_bot.application.services.transcript_summary import (
    SummaryError,
    _EstimatedTokenizer,
)


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


class _HuggingFaceTokenizer(TextTokenizer):
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
        return len(self._tokenizer.encode(text, add_special_tokens=False)) if text else 0

    def split(self, text: str, max_tokens: int) -> list[str]:
        ids = list(self._tokenizer.encode(text, add_special_tokens=False))
        if len(ids) <= max_tokens:
            return [text]
        return [
            str(
                self._tokenizer.decode(
                    ids[start : start + max_tokens],
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=False,
                )
            ).strip()
            for start in range(0, len(ids), max_tokens)
            if ids[start : start + max_tokens]
        ]


def make_text_tokenizer(
    *,
    backend: str,
    model: str,
    chars_per_token: float,
    trust_remote_code: bool = False,
) -> TextTokenizer:
    backend = backend.strip().lower() or "auto"
    if backend in {"estimate", "estimated"}:
        return _EstimatedTokenizer(chars_per_token=chars_per_token)
    if backend not in {"auto", "hf", "huggingface"}:
        raise SummaryError("SUMMARY_TOKENIZER_BACKEND inválido. Use auto, hf ou estimate.")
    try:
        from transformers import AutoTokenizer

        factory = cast(Callable[..., _TokenizerCodec], AutoTokenizer.from_pretrained)
        tokenizer = factory(
            model,
            local_files_only=True,
            trust_remote_code=trust_remote_code,
        )
        return _HuggingFaceTokenizer(model=model, tokenizer=tokenizer)
    except Exception as exc:
        if backend in {"hf", "huggingface"}:
            raise SummaryError(
                f"Não foi possível carregar o tokenizer Hugging Face local ({model!r}). Detalhe: {exc}"
            ) from exc
        return _EstimatedTokenizer(chars_per_token=chars_per_token)


_make_tokenizer = make_text_tokenizer
