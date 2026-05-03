# Patch notes — 2026-05-02

## Motivo

Correção de falha observada em produção ao enviar um link do YouTube ao bot:

```text
ERROR: [youtube] <video_id>: Requested format is not available. Use --list-formats for a list of available formats
```

A falha ocorria ainda na etapa de `fetch_metadata`, antes do download de áudio e antes do WhisperX.

## Correções

- `YtDlpDownloader.fetch_metadata()` agora passa um seletor de formato permissivo para o `yt-dlp`, evitando que a extração de metadados dependa do seletor padrão ou de configurações externas.
- `YtDlpDownloader.list_subtitles()` recebeu a mesma proteção, pois também usa extração sem download.
- `_common_params()` agora usa `ignoreconfig=True`, impedindo que um `~/.config/yt-dlp/config` ou `/etc/yt-dlp.conf` injete `-f` incompatível com o fluxo do bot. Cookies continuam sendo passados pelas variáveis/configurações próprias do projeto.
- `_extract_info()` faz uma segunda tentativa ainda mais permissiva (`best/worst`) quando a chamada sem download falha especificamente por formato indisponível.
- `download_audio()` mantém preferência por áudio-only e faixa original quando disponível, mas agora inclui fallbacks muxados com áudio para vídeos em que não exista pista `bestaudio` separada.
- Corrigido também um bug independente no parser VTT/SRT que duplicava o último bloco de legenda.

## Validação feita neste ambiente

```bash
python -m compileall -q src tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src pytest -q tests/unit/infrastructure/youtube/test_yt_dlp_downloader.py
```

Resultado do teste direcionado: `37 passed`.

A suíte completa ainda requer as dependências de projeto instaladas (`python-slugify`, `sqlalchemy`, `python-telegram-bot`, etc.).
