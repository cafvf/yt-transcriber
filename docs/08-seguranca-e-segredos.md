# Segurança e segredos

Segredos e dados de runtime ficam fora do Git. Produção usa `/etc/yt-transcriber-bot/env`, normalmente modo `0600`, lido pelo systemd e injetado no processo. `.env` é somente conveniência de checkout de desenvolvimento.

## Não versionar

- `.env` real ou `/etc/yt-transcriber-bot/env`;
- cookies do YouTube/browser;
- tokens Telegram/Hugging Face/API;
- SQLite, mídia, transcrições, modelos, caches e logs privados;
- backups do operador.

## Credenciais atuais

`TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_ID` e `HF_TOKEN` são obrigatórios no startup/preflight atual. Cookies são condicionais; `SUMMARY_API_KEY` depende do endpoint.

Use privilégios mínimos. Cookies autenticados equivalem a material de sessão.

## Sanitização

`/healthcheck`, `/lasterror`, mensagens de erro e logs usam sanitização central para reduzir exposição de tokens, cookies, `Authorization`, prompts, corpos de API e transcrições ecoadas. Saída sanitizada continua privada porque pode conter paths, títulos, IDs e nomes de modelos.

## Dados persistidos

Estado de produção vive sob `/var/lib/yt-transcriber-bot`. SQLite, Markdown, snapshots, resumos, auditoria e erros são privados. Retenção pode remover mídia/logs reconstruíveis, mas artefatos canônicos sustentam histórico/exportações/rename.

## Sumarização

`SUMMARY_BASE_URL` define o destino da transcrição quando `/summary` é usado. Endpoint externo é disclosure explícito. Para operação local, use endpoint local confiável ou `SUMMARY_BACKEND=disabled`. Mantenha `SUMMARY_TOKENIZER_TRUST_REMOTE_CODE=false` salvo decisão deliberada.

## Desenvolvimento

Ferramentas de desenvolvimento não pertencem à instalação de produção:

```bash
uv sync --dev
uv run pre-commit run --all-files
uv run python scripts/security/scan_secrets.py --all
uv run python scripts/security/gitleaks_if_available.py --all
```

`requirements-dev.txt` é fallback de tooling de desenvolvimento.

## Credencial exposta

Revogue/rotacione, gere substituta com menor privilégio, atualize somente a fonte privada e remova cópias desnecessárias. Apagar/mascarar mensagem não substitui rotação.

## Backup

O backup padrão é credential-free: inclua dados duráveis necessários à recuperação, mas exclua `/etc/yt-transcriber-bot/env`, `.env`, cookies, tokens/API keys, modelos/caches reconstruíveis e mídia temporária dispensável. Credenciais são reprovisionadas separadamente.
