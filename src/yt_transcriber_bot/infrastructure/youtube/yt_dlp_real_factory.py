"""Factory real para ``yt_dlp.YoutubeDL`` e fetcher de legendas.

Mantém a importação preguiçosa para que módulos que não precisem do
yt-dlp possam ser testados sem ele.
"""

from __future__ import annotations

import urllib.request
from typing import Any


def real_ydl_factory(params: dict[str, Any]) -> Any:
    """Cria um ``yt_dlp.YoutubeDL`` real com os parâmetros fornecidos."""
    from yt_dlp import YoutubeDL  # type: ignore[import-untyped]

    return YoutubeDL(params)


def real_subtitle_fetcher(url: str, ext: str) -> str:
    """Baixa o conteúdo de uma legenda diretamente. ``ext`` apenas para log."""
    with urllib.request.urlopen(url, timeout=30) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset()
        candidates = [c for c in (charset, "utf-8", "utf-8-sig") if c]
        for encoding in candidates:
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")
