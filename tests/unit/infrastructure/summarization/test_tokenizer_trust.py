"""Supply-chain and tokenizer trust regressions."""

from __future__ import annotations

import builtins
import sys
from types import SimpleNamespace

import pytest

from yt_transcriber_bot.infrastructure.summarization.transcript_summarizer import (
    SummaryError,
    _make_tokenizer,
)


def test_auto_tokenizer_has_explicit_estimated_fallback_when_transformers_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def guarded_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "transformers":
            raise ImportError("transformers unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    tokenizer = _make_tokenizer(backend="auto", model="approved/model", chars_per_token=2.5)
    assert tokenizer.is_exact is False

    with pytest.raises(SummaryError, match="tokenizer Hugging Face local"):
        _make_tokenizer(backend="hf", model="approved/model", chars_per_token=2.5)


def test_local_hf_loading_preserves_model_identity_and_remote_code_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeCodec:
        def encode(self, text: str, *, add_special_tokens: bool = False) -> list[int]:
            return [1] if text else []

        def decode(
            self,
            token_ids: list[int],
            *,
            skip_special_tokens: bool = True,
            clean_up_tokenization_spaces: bool = False,
        ) -> str:
            return "decoded"

    class FakeAutoTokenizer:
        @staticmethod
        def from_pretrained(model: str, **kwargs: object) -> FakeCodec:
            calls.append((model, kwargs))
            return FakeCodec()

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(AutoTokenizer=FakeAutoTokenizer),
    )

    tokenizer = _make_tokenizer(
        backend="hf",
        model="approved/model",
        chars_per_token=2.5,
        trust_remote_code=False,
    )

    assert tokenizer.is_exact is True
    assert calls == [
        (
            "approved/model",
            {"local_files_only": True, "trust_remote_code": False},
        )
    ]
