from __future__ import annotations

import html
import re


def normalize_artifact_text(text: str) -> str:
    """Normaliza texto vindo de snapshots/subtitles para artefatos legíveis."""

    for _ in range(3):
        unescaped = html.unescape(text)
        if unescaped == text:
            break
        text = unescaped
    text = text.replace("\xa0", " ")
    text = text.replace("\u200b", "")
    text = text.replace("\ufeff", "")
    return re.sub(r"\s+", " ", text).strip()
