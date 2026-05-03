"""Extrai URLs do YouTube de mensagens de texto do Telegram.

Decisão da Dúvida 24: o bot busca URL no texto da mensagem; se não houver,
responde com aviso. Este módulo isola a lógica de detecção de URL para que
seja testável sem mockar o Telegram.
"""

from __future__ import annotations

import re

# Padrão tolerante: youtube.com/watch?v=, youtu.be/, youtube.com/shorts/,
# youtube.com/embed/, m.youtube.com etc. O VideoId.from_url valida o formato
# canônico do ID e levanta erro caso algo passe por aqui mas não seja válido.
# Aceita host: [sub.]youtube.com ou youtu.be IMEDIATAMENTE após // (não dentro
# de querystrings de outros sites). Sub-domínios permitidos: www, m, music.
_URL_PATTERN = re.compile(
    r"(https?://(?:[\w-]+\.)*(?:youtube\.com|youtu\.be)(?:/[^\s]*)?)",
    flags=re.IGNORECASE,
)


def extract_first_youtube_url(text: str) -> str | None:
    """Devolve a primeira URL do YouTube encontrada no texto, ou None.

    A função é deliberadamente permissiva: aceita variantes (m.youtube.com,
    music.youtube.com, com query strings extra, com fragmentos). A validação
    estrita do ID fica a cargo de ``VideoId.from_url`` no domínio.
    """
    if not text:
        return None
    match = _URL_PATTERN.search(text)
    if match is None:
        return None
    url = match.group(1)
    # Remove pontuação trailing comum em mensagens.
    url = url.rstrip(".,;:!?)\"'")
    return url
