"""Factory real para ``yt_dlp.YoutubeDL`` e fetcher de legendas.

Mantém a importação preguiçosa para que módulos que não precisem do
yt-dlp possam ser testados sem ele.
"""

from __future__ import annotations

import urllib.request
from typing import Any, cast

from yt_transcriber_bot.infrastructure.text.normalization import (
    normalize_artifact_text,
    unresolved_text_corruption_score,
)


def real_ydl_factory(params: dict[str, Any]) -> Any:
    """Cria um ``yt_dlp.YoutubeDL`` real com os parâmetros fornecidos."""
    from yt_dlp import YoutubeDL

    return YoutubeDL(params)


def real_subtitle_fetcher(url: str, ext: str) -> str:
    """Baixa o conteúdo de uma legenda diretamente. ``ext`` apenas para log."""
    with urllib.request.urlopen(url, timeout=30) as resp:
        raw = cast(bytes, resp.read())
        charset = resp.headers.get_content_charset()
        candidates = _ordered_decode_candidates(charset)
        decoded_candidates: list[tuple[str, str]] = []
        for encoding in candidates:
            try:
                decoded_candidates.append((encoding, raw.decode(encoding)))
            except UnicodeDecodeError:
                continue
        if decoded_candidates:
            return max(decoded_candidates, key=_decode_candidate_score)[1]
        return raw.decode("utf-8", errors="replace")


def _ordered_decode_candidates(charset: str | None) -> tuple[str, ...]:
    ordered = [charset, "utf-8", "utf-8-sig", "cp1252", "latin-1"]
    seen: set[str] = set()
    candidates: list[str] = []
    for encoding in ordered:
        if not encoding:
            continue
        normalized = encoding.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        candidates.append(encoding)
    return tuple(candidates)


def _decode_candidate_score(candidate: tuple[str, str]) -> tuple[int, int, int]:
    encoding, text = candidate
    normalized = normalize_artifact_text(text)
    corruption_penalty = -unresolved_text_corruption_score(normalized)
    replacement_penalty = -normalized.count("�")
    encoding_priority = {
        "utf-8": 4,
        "utf-8-sig": 3,
        "cp1252": 2,
        "latin-1": 1,
    }.get(encoding.lower(), 5)
    return (corruption_penalty, replacement_penalty, encoding_priority)
