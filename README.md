# YT Transcriber Bot

Bot privado do Telegram para um único operador transcrever links do YouTube e mídia de áudio enviada pelo próprio usuário. O produto gera uma transcrição canônica em Markdown, mantém histórico local em SQLite, oferece exportações e busca textual, pode diarizar falantes e pode gerar resumos por um endpoint OpenAI-compatible configurado pelo operador.

O alvo de produção atual é **Linux, single-operator e private-chat-only**. Não é um serviço público, multiusuário ou hospedado.

## Capacidades atuais

- aceita URL do YouTube, áudio, mensagem de voz e documento de áudio no Telegram;
- prefere legendas aproveitáveis do YouTube e usa WhisperX quando ASR é necessário;
- usa ffmpeg/ffprobe para mídia e pyannote/WhisperX para diarização;
- produz Markdown e exporta TXT, JSON, SRT e VTT;
- gera MP4 com legenda selecionável para origens YouTube compatíveis;
- mantém histórico local, `/search <texto>`, `/rename`, `/summary`, `/healthcheck` e `/lasterror`;
- executa um job por vez; a fila é **em memória**, com estado mínimo persistido para reconciliação após reinício.

Aceita links do YouTube, áudio, mensagens de voz e documentos de áudio.

## Limitações importantes

- Python suportado: **3.11 ou 3.12**;
- produção suportada: Linux; WSL2 pode ser usado para operação local;
- existe apenas um usuário autorizado (`TELEGRAM_ALLOWED_USER_ID`);
- não há retomada no meio de ASR ou diarização: estados ativos interrompidos viram falha e `delivering` interrompido vira `delivery_failed`;
- `/redo <link>` reprocessa imediatamente e não pede confirmação inline;
- `/translate`, `/search semantic <texto>`, multiusuário, Docker Compose e checkpoints internos continuam fora do produto atual;
- sumarização depende do endpoint configurado e pode ser desabilitada sem impedir transcrição;
- cookies do YouTube podem ser necessários para conteúdo autenticado ou cenários anti-bot.

## Pré-requisitos

Para produção, instale Git para obter/atualizar a fonte de instalação, Python 3.11 ou 3.12 com `venv`, `ffmpeg`/`ffprobe` e ao menos um runtime JavaScript suportado: **Deno >= 2.3.0** ou **Node.js >= 22.0.0**. GPU NVIDIA é opcional.

A stack de ML é dependência de produção e é instalada junto com o pacote; não use um ambiente “mínimo” sem WhisperX/pyannote.

## Instalação de produção

O checkout é usado para construir/instalar a distribuição, mas **não faz parte do runtime de produção**.

```bash
git clone https://github.com/cafvf/yt-transcriber.git
cd yt-transcriber

if command -v python3.12 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3.12)"
elif command -v python3.11 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3.11)"
else
    echo "Python 3.11 ou 3.12 é obrigatório" >&2
    exit 1
fi

sudo install -d -m 0755 -o "$USER" -g "$(id -gn)" /opt/yt-transcriber-bot
"$PYTHON_BIN" -m venv /opt/yt-transcriber-bot/venv
/opt/yt-transcriber-bot/venv/bin/pip install --upgrade pip
/opt/yt-transcriber-bot/venv/bin/pip install .
```

Após a instalação, produção executa `/opt/yt-transcriber-bot/venv/bin/yt-transcriber-bot`. Produção não depende de `uv`, `python -m yt_transcriber_bot`, dependências de desenvolvimento ou presença do checkout em `sys.path`.

## Credenciais e configuração

| Item | Estado atual | Observação |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | obrigatório | Token do BotFather. |
| `TELEGRAM_ALLOWED_USER_ID` | obrigatório | ID numérico do único operador autorizado. |
| `HF_TOKEN` | obrigatório no startup/preflight atual | Usado pela diarização; o código atual recusa startup sem ele. |
| `YOUTUBE_COOKIES_FILE` | opcional/condicional | Use quando o YouTube exigir sessão autenticada. |
| `YOUTUBE_COOKIES_BROWSER` | opcional/condicional | Alternativa quando o browser está acessível no mesmo host. |
| `SUMMARY_API_KEY` | opcional | Depende do endpoint OpenAI-compatible. |

Crie a configuração privada de produção:

```bash
sudo install -d -m 0755 /etc/yt-transcriber-bot
sudo install -m 0600 -o "$USER" -g "$(id -gn)" \
  deploy/yt-transcriber-bot.environment.example /etc/yt-transcriber-bot/env
${EDITOR:-nano} /etc/yt-transcriber-bot/env
```

O contrato de produção é:

```text
EnvironmentFile=/etc/yt-transcriber-bot/env
WorkingDirectory=/var/lib/yt-transcriber-bot
StateDirectory=yt-transcriber-bot
ExecStart=/opt/yt-transcriber-bot/venv/bin/yt-transcriber-bot
```

Em checkout de desenvolvimento, `.env` continua sendo conveniência local. Uma distribuição instalada não procura `.env` no diretório corrente. Para uma execução explícita fora do systemd, use `YT_TRANSCRIBER_ENV_FILE=/caminho/privado/env`.

## Preflight antes do primeiro start

O preflight da distribuição é **offline e read-only**: não inicia polling Telegram, não chama LM Studio, não inicializa SQLite, não cria diretórios e não carrega/downloada modelos.

```bash
PATH="/opt/yt-transcriber-bot/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
YT_TRANSCRIBER_ENV_FILE=/etc/yt-transcriber-bot/env \
/opt/yt-transcriber-bot/venv/bin/yt-transcriber-bot --preflight
```

Para JSON, acrescente `--json`. O `PATH` inclui o `bin` do venv para que readiness encontre o console `yt-dlp` instalado pela própria distribuição.

## systemd e início do bot

```bash
sed \
  -e "s/^User=SEU_USUARIO$/User=$USER/" \
  -e "s/^Group=SEU_USUARIO$/Group=$(id -gn)/" \
  deploy/yt-transcriber-bot.service \
  | sudo tee /etc/systemd/system/yt-transcriber-bot.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now yt-transcriber-bot
sudo systemctl status yt-transcriber-bot --no-pager
```

## Primeira transcrição

1. Abra o chat privado com o bot.
2. Envie `/healthcheck`; ele é um diagnóstico de runtime online, mais amplo que `--preflight`.
3. Envie uma URL curta do YouTube ou um arquivo de áudio.
4. Acompanhe com `/status` ou `/queue`.
5. Use `/list` para confirmar que o job concluído entrou no histórico.

Para idioma explícito, use `/pt <link>` ou `/en <link>`; `/transcribe <link>` usa a política automática.

## Comandos principais

| Objetivo | Comando |
|---|---|
| Ajuda/estado | `/help`, `/status`, `/queue` ou `/fila` |
| Cancelamento | `/cancel`, `/cancelall`, `/clearqueue` |
| Histórico | `/list`, `/last [n]`, `/search <texto>` |
| Reprocessar | `/redo <link> [--lang pt\|en]` |
| Falantes | `/rename [n]` |
| Resumo | `/summary [n]` |
| Exportação | `/text [n]`, `/json [n]`, `/srt [n]`, `/vtt [n]`, `/export <tipo> [n]` |
| Vídeo legendado | `/video_subs [n]` |
| Diagnóstico | `/healthcheck`, `/lasterror`, `/clearcache` |

Jobs concluídos podem ser reprocessados; a deduplicação protege a mesma origem/idioma **em processamento ou na fila**. Em falha de entrega, consulte `/lasterror`; `delivery_failed` é estado persistido.

## Atualização

O checkout é fonte de instalação, não diretório de execução. Faça backup, pare o serviço, atualize o checkout para a revisão desejada, reinstale com `/opt/yt-transcriber-bot/venv/bin/pip install --upgrade .`, execute `--preflight`, inicie o serviço e valide `/healthcheck`, `/status` e um smoke curto. Veja o [runbook](docs/11-operator-runbook.md).

## Backup

O backup padrão é **credential-free**. Preserve SQLite e artefatos canônicos, mas não inclua `/etc/yt-transcriber-bot/env`, cookies, tokens, cache de modelos ou mídia temporária. Veja [segurança](docs/08-seguranca-e-segredos.md) e [runbook](docs/11-operator-runbook.md).

## Troubleshooting

- `--preflight` falha: corrija Python, módulos/binários, credenciais ou runtime JS;
- serviço não inicia: `sudo systemctl status yt-transcriber-bot` e `journalctl -u yt-transcriber-bot -n 120 --no-pager`;
- provider falha: `/healthcheck` e depois `/lasterror`;
- YouTube retorna 401/403/429: revise cookies e runtime JS;
- `/summary` falha: valide backend/endpoint/modelo; transcrição continua independente;
- `delivery_failed`: o artefato pode existir localmente; siga o runbook.

## Desenvolvimento

```bash
uv sync --dev
uv run pytest -p no:cacheprovider
uv run ruff check --no-cache .
uv run ruff format --check --no-cache .
uv run mypy src
uv run pre-commit run --all-files
```

Use `.env.example` somente como template de desenvolvimento.

## Documentação canônica

- [Contrato funcional](docs/01-contrato-funcional.md)
- [Arquitetura](docs/02-arquitetura.md)
- [Manual de uso](docs/03-manual-de-uso.md)
- [Instalação](docs/04-manual-de-instalacao.md)
- [Roadmap](docs/06-funcionalidades-futuras.md) — explicitamente futuro, não comportamento atual.
- [Glossário e decisões vigentes](docs/07-glossario-e-decisoes.md)
- [Segurança e segredos](docs/08-seguranca-e-segredos.md)
- [Production readiness](docs/09-production-readiness.md)
- [Recovery semantics](docs/10-recovery-semantics-adr.md)
- [Runbook](docs/11-operator-runbook.md)
- [Deprecações e compatibilidade](docs/12-deprecacoes-e-compatibilidade.md)

Specs, requirements, tasks e casos de uso permanecem em `specs/` como contratos de engenharia e conformance; não são o onboarding operacional do usuário.
