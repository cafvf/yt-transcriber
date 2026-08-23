# Production readiness

Estado operacional atual para produção privada/single-operator em Linux.

## Contrato instalado

```text
EnvironmentFile=/etc/yt-transcriber-bot/env
WorkingDirectory=/var/lib/yt-transcriber-bot
StateDirectory=yt-transcriber-bot
ExecStart=/opt/yt-transcriber-bot/venv/bin/yt-transcriber-bot
```

O pacote é importado de `site-packages`; checkout, `uv`, pytest, Ruff, mypy e pre-commit não são requisitos de runtime.

## Preflight de distribuição

`yt-transcriber-bot --preflight` e `yt-transcriber-bot --preflight --json` validam Python 3.11/3.12, metadata instalada, credenciais, módulos/binários, `yt-dlp-ejs` e Deno >= 2.3.0 ou Node >= 22.0.0. O preflight é offline/read-only: não inicia Telegram, LM Studio, SQLite ou modelos.

## Readiness online

Depois do start, `/healthcheck` complementa o preflight com filesystem, SQLite, espaço, cookies e serviços configurados. `/lasterror` apresenta o último erro sanitizado.

## Comportamentos que o readiness deve refletir

- fila de execução **em memória**, sequencial;
- `pending` elegível pode ser recuperado após reinício;
- estados ativos interrompidos são reconciliados para falha;
- `JobStatus.DELIVERING` representa entrega em andamento;
- `JobStatus.DELIVERY_FAILED`/`delivery_failed` é persistido e aparece em `/lasterror`;
- entrega pode registrar `transcribe_delivery`;
- `/search`, `/text` e `/redo <link>` são atuais;
- `/translate` não é atual;
- não existem tabelas ORM separadas `speakers` ou `queue`.

## Checklist

- [ ] Python 3.11/3.12.
- [ ] `ffmpeg`/`ffprobe`.
- [ ] Deno >= 2.3 ou Node >= 22.
- [ ] distribuição em `/opt/yt-transcriber-bot/venv`.
- [ ] `/etc/yt-transcriber-bot/env` restritivo e válido.
- [ ] `PATH` inclui `/opt/yt-transcriber-bot/venv/bin`.
- [ ] unit corresponde ao template versionado.
- [ ] `yt-transcriber-bot --preflight` passa.
- [ ] serviço inicia sem crash loop.
- [ ] `/healthcheck`, `/status` e `/list` funcionam.
- [ ] transcrição curta conclui.
- [ ] backup credential-free planejado.

Ausências como multiusuário, alertas externos, Docker Compose, busca semântica, tradução e checkpoint interno não devem ser descritas como capacidades existentes.
