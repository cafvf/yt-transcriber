# Manual de instalação

Este manual descreve o contrato atual de instalação privada/single-operator. A distribuição instalada é executada de `/opt`; configuração privada fica em `/etc`; estado mutável fica em `/var/lib`. O checkout serve para construir/atualizar a distribuição, não para executar o serviço.

## Pré-requisitos

Use Linux com Python 3.11 ou 3.12, `ffmpeg`/`ffprobe` e Deno >= 2.3.0 ou Node.js >= 22.0.0. O pacote instala `yt-dlp[default]`/`yt-dlp-ejs`, Telegram, SQLAlchemy e a stack ML como dependências de produção. Ruff, mypy, pytest e pre-commit são desenvolvimento.

## Instalação

```bash
git clone https://github.com/cafvf/yt-transcriber.git
cd yt-transcriber
if command -v python3.12 >/dev/null 2>&1; then PYTHON_BIN="$(command -v python3.12)"; else PYTHON_BIN="$(command -v python3.11)"; fi
sudo install -d -m 0755 -o "$USER" -g "$(id -gn)" /opt/yt-transcriber-bot
"$PYTHON_BIN" -m venv /opt/yt-transcriber-bot/venv
/opt/yt-transcriber-bot/venv/bin/pip install --upgrade pip
/opt/yt-transcriber-bot/venv/bin/pip install .
```

Confirme que `yt_transcriber_bot.__file__` aponta para `site-packages` do venv de `/opt`, não para `src/` do checkout.

## Credenciais

O contrato atual exige `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_ID` > 0 e `HF_TOKEN`. Cookies do YouTube são condicionais. `SUMMARY_API_KEY` depende do endpoint de resumo.

## Configuração privada

```bash
sudo install -d -m 0755 /etc/yt-transcriber-bot
sudo install -m 0600 -o "$USER" -g "$(id -gn)" deploy/yt-transcriber-bot.environment.example /etc/yt-transcriber-bot/env
${EDITOR:-nano} /etc/yt-transcriber-bot/env
```

Systemd injeta o arquivo no ambiente do processo. `.env` só é descoberto automaticamente quando o próprio módulo roda de um checkout de desenvolvimento. `YT_TRANSCRIBER_ENV_FILE` seleciona explicitamente outro arquivo privado.

O nome canônico do limite é `MAX_MEDIA_DURATION_MIN`; `MAX_VIDEO_DURATION_MIN` é alias legado.

## systemd

A unit versionada define:

```text
WorkingDirectory=/var/lib/yt-transcriber-bot
StateDirectory=yt-transcriber-bot
EnvironmentFile=/etc/yt-transcriber-bot/env
ExecStart=/opt/yt-transcriber-bot/venv/bin/yt-transcriber-bot
```

```bash
sed -e "s/^User=SEU_USUARIO$/User=$USER/" -e "s/^Group=SEU_USUARIO$/Group=$(id -gn)/" deploy/yt-transcriber-bot.service | sudo tee /etc/systemd/system/yt-transcriber-bot.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable yt-transcriber-bot
```

O template de produção inclui `/opt/yt-transcriber-bot/venv/bin` no `PATH`, necessário para readiness localizar o `yt-dlp` instalado no venv.

## Preflight

```bash
PATH="/opt/yt-transcriber-bot/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
YT_TRANSCRIBER_ENV_FILE=/etc/yt-transcriber-bot/env \
/opt/yt-transcriber-bot/venv/bin/yt-transcriber-bot --preflight
```

O preflight é offline/read-only e não inicia Telegram, LM Studio, SQLite ou modelos. `scripts/ops/systemd_host_preflight.py` continua sendo helper de manutenção de host/unit a partir do checkout, não dependência de produção.

## Primeiro start

```bash
sudo systemctl start yt-transcriber-bot
sudo systemctl status yt-transcriber-bot --no-pager
journalctl -u yt-transcriber-bot -n 80 --no-pager
```

No Telegram, execute `/healthcheck` e `/status`, depois uma transcrição curta.

## Sumarização

`SUMMARY_BACKEND=openai_compatible` usa `SUMMARY_BASE_URL`/`SUMMARY_MODEL`. `SUMMARY_BACKEND=disabled` desabilita resumo sem bloquear transcrição. Mantenha `SUMMARY_TOKENIZER_TRUST_REMOTE_CODE=false` salvo decisão deliberada.

## Atualização e rollback

O checkout é apenas fonte de instalação. Pare o serviço, selecione explicitamente a revisão desejada no checkout e execute `/opt/yt-transcriber-bot/venv/bin/pip install --upgrade .`. Rode preflight antes de iniciar.

Rollback reinstala uma revisão previamente conhecida; não troca revisão “dentro do runtime”. Dados não são revertidos automaticamente com código. Restore de dados exige backup deliberadamente escolhido.

## Desenvolvimento

```bash
uv sync --dev
uv run pytest -p no:cacheprovider
uv run ruff check --no-cache .
uv run ruff format --check --no-cache .
uv run mypy src
```

Esse workflow de checkout é desenvolvimento, não o contrato do serviço instalado.
