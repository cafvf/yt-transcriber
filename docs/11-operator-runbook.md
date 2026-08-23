# Runbook do operador

## Topologia

```text
WorkingDirectory=/var/lib/yt-transcriber-bot
StateDirectory=yt-transcriber-bot
EnvironmentFile=/etc/yt-transcriber-bot/env
ExecStart=/opt/yt-transcriber-bot/venv/bin/yt-transcriber-bot
```

## Rotina básica

```bash
sudo systemctl status yt-transcriber-bot --no-pager
journalctl -u yt-transcriber-bot -n 120 --no-pager
sudo systemctl restart yt-transcriber-bot
```

No Telegram: `/healthcheck`, `/status`, `/queue`, `/lasterror`.

## Manutenção e reinício

Não existe checkpoint no meio de ASR/diarização. Após reinício, `pending` elegível pode ser re-enfileirado; estado ativo interrompido vira `failed`; `delivering` interrompido vira `delivery_failed`.

Para manutenção deliberada, pare primeiro o serviço.

## Preflight de host/systemd

A partir de checkout de manutenção, `scripts/ops/systemd_host_preflight.py` verifica host/unit sem imprimir valores do env. Resolva Python nesta ordem: `.venv/bin/python`, depois `python3`. Esse helper não é dependência do serviço; o preflight primário é o console instalado.

## Backup credential-free

Com defaults de produção, preserve `/var/lib/yt-transcriber-bot/data/jobs.db` e artefatos canônicos em `/var/lib/yt-transcriber-bot/data/`. Não inclua `/etc/yt-transcriber-bot/env`, cookies ou credenciais.

Backup frio recomendado: pare o serviço, use `sqlite3.Connection.backup()` através de `/opt/yt-transcriber-bot/venv/bin/python`, valide `PRAGMA integrity_check`, arquive Markdown/snapshots canônicos com permissões restritivas e reinicie.

## Restore

Com serviço parado: preserve o estado atual, restaure SQLite/artefatos escolhidos, confirme ownership/permissões, valide `PRAGMA integrity_check`, inicie e rode `/healthcheck`, `/status`, `/list`. Credenciais/cookies são reprovisionados separadamente.

## Atualização

Use checkout apenas como fonte de instalação:

```bash
sudo systemctl stop yt-transcriber-bot
/opt/yt-transcriber-bot/venv/bin/pip install --upgrade .
PATH="/opt/yt-transcriber-bot/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
YT_TRANSCRIBER_ENV_FILE=/etc/yt-transcriber-bot/env \
/opt/yt-transcriber-bot/venv/bin/yt-transcriber-bot --preflight
sudo systemctl start yt-transcriber-bot
```

Valide `/healthcheck`, `/status` e um job curto.

## Rollback

Pare o serviço, selecione no checkout uma revisão previamente conhecida, reinstale no venv de `/opt`, rode preflight e inicie. Dados não são revertidos automaticamente com código; restore de dados exige backup explicitamente escolhido.

## `delivery_failed`

Use `/lasterror` e `/list`. Artefatos podem existir localmente mesmo quando envio Telegram falha. Não há reenvio automático universal; recupere/reprocesse deliberadamente.

## Cookies e YouTube

Em 401/403/429/challenge: confirme Deno/Node, `yt-dlp`/`yt-dlp-ejs`, permissões/validade dos cookies e reinicie após correção. Nunca compartilhe cookies.

## Encerramento de incidente

Serviço `active`, `/healthcheck` sem bloqueio relevante, `/status` funcional, histórico acessível, smoke curto concluído e nenhuma credencial exposta na evidência coletada.
