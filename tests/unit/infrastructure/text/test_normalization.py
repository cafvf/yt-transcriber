"""Text artifact normalization regressions."""

from __future__ import annotations

import pytest

from yt_transcriber_bot.infrastructure.text.normalization import normalize_artifact_text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("VocÃª nÃ£o tem aÃ§Ã£o", "Você não tem ação"),
        ("atÃ© amanhÃ£", "até amanhã"),
        ("coraÃ§Ã£o", "coração"),
        ("JoÃ£o", "João"),
        ("OlÃ¡Â! Tudo bemÂ?", "Olá! Tudo bem?"),
        ("Ele disse: â€œolÃ¡â€� e saiuâ€¦", "Ele disse: “olá” e saiu…"),
    ],
)
def test_repairs_common_brazilian_portuguese_mojibake(raw: str, expected: str) -> None:
    assert normalize_artifact_text(raw) == expected


def test_preserves_valid_utf8_portuguese_text() -> None:
    text = "Você não tem ação, João. Coração em português correto."
    assert normalize_artifact_text(text) == text


@pytest.mark.parametrize(
    "text",
    [
        "VocÃª nÃ£o tem aÃ§Ã£o",
        "Você não tem ação, João.",
        "A&nbsp;B\u200b C",
    ],
)
def test_normalization_is_idempotent(text: str) -> None:
    once = normalize_artifact_text(text)
    assert normalize_artifact_text(once) == once
