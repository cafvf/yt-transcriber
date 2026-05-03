# Patch notes — 2026-05-02 — robust YouTube format fallback

## Contexto

Um vídeo do YouTube (`L9awVwLDH18`) continuava falhando no `download_audio()` com:

```text
Requested format is not available. Use --list-formats for a list of available formats
```

A falha já não ocorria mais na etapa de metadados; ela acontecia durante o download real pelo `yt-dlp`.

## Correção

O downloader agora usa uma estratégia em camadas:

1. tentativa rápida com seletor progressivo-first, priorizando formatos YouTube progressivos comuns (`18`, `22`) e formatos MP4 com áudio;
2. se o seletor falhar, o código extrai a lista de formatos sem baixar;
3. escolhe candidatos concretos com áudio por `format_id`;
4. tenta audio-only primeiro;
5. se audio-only falhar, tenta formatos progressivos com áudio, como MP4 360p;
6. como último recurso, deixa o `yt-dlp` escolher o formato sem seletor explícito.

Essa abordagem é mais robusta para vídeos em que `bestaudio` é anunciado, mas falha no download por restrições transitórias do YouTube/yt-dlp.

## Testes adicionados

Foi adicionado teste de regressão cobrindo:

- falha inicial com `Requested format is not available`;
- descoberta de formatos;
- falha em audio-only por HTTP 403;
- fallback bem-sucedido para formato progressivo `18`.

Validação local no sandbox:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src pytest -q tests/unit/infrastructure/youtube/test_yt_dlp_downloader.py
```

Resultado:

```text
38 passed
```
