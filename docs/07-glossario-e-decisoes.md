# Glossário e decisões vigentes

Este documento registra apenas conceitos e decisões que descrevem o código atual. Histórico de implementação pertence ao Git e às `specs/`; não é orientação operacional.

## Glossário

**ASR** — reconhecimento automático de fala; o caminho atual usa WhisperX/faster-whisper quando necessário.

**Diarização** — “quem falou quando”; o runtime usa WhisperX/pyannote e o contrato atual exige `HF_TOKEN`.

**Artefato canônico** — representação preservada como fonte de verdade. Markdown é a representação humana canônica; snapshots estruturados sustentam operações derivadas.

**Job** — unidade persistida de trabalho. Status/metadados ficam no SQLite; a fila continua em memória.

**Preflight** — `yt-transcriber-bot --preflight`, verificação local offline/read-only da distribuição instalada.

**Healthcheck** — diagnóstico operacional via Telegram, mais amplo que preflight; `/lasterror` expõe o último erro sanitizado para investigação.

**Composition root** — `composition_root.py`, onde adapters concretos são ligados às portas; `__main__.py` não é o lugar para wiring direto de infraestrutura.

## Decisões vigentes

### DEC-001 — Single operator e private chat
O produto autoriza um único `TELEGRAM_ALLOWED_USER_ID`; não há modelo multiusuário.

### DEC-002 — Distribuição instalada é o runtime de produção

```text
WorkingDirectory=/var/lib/yt-transcriber-bot
StateDirectory=yt-transcriber-bot
EnvironmentFile=/etc/yt-transcriber-bot/env
ExecStart=/opt/yt-transcriber-bot/venv/bin/yt-transcriber-bot
```

`uv`, `python -m yt_transcriber_bot` e checkout não são dependências de runtime.

### DEC-003 — Configuração privada pertence à borda
Systemd injeta `/etc/yt-transcriber-bot/env`. `.env` é conveniência de desenvolvimento apenas quando o módulo executa do próprio checkout. `YT_TRANSCRIBER_ENV_FILE` é a seleção explícita alternativa.

### DEC-004 — Identidade de mídia é source-neutral
Entrada Telegram não inventa `video_id`/URL YouTube. Compatibilidades físicas podem permanecer legíveis sem redefinir o domínio.

### DEC-005 — Fila sequencial em memória com reconciliação persistida
`pending` elegível pode ser re-enfileirado no reinício; estado ativo interrompido vira `failed`; `delivering` vira `delivery_failed`. Não existe checkpoint no meio de ASR/diarização.

### DEC-006 — Canônico antes de derivados
Histórico, rename, exportações e resumo usam representações persistidas; não reprocessam mídia por padrão.

### DEC-007 — Resumo é opcional e endpoint-explicit
`openai_compatible` usa endpoint/modelo configurado pelo operador; `SUMMARY_BACKEND=disabled` não bloqueia transcrição.

### DEC-008 — Sanitização reduz exposição, não torna dado público
Tokens, cookies, prompts, corpos de API e transcrições não devem ser ecoados; paths/títulos continuam potencialmente privados.

### DEC-009 — Compatibilidade não redefine o nome canônico
`MAX_MEDIA_DURATION_MIN` é canônico; `MAX_VIDEO_DURATION_MIN` é compatibilidade. Veja [deprecações](12-deprecacoes-e-compatibilidade.md).
