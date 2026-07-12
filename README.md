# YT Transcriber Bot

Bot privado do Telegram para transcrever conteúdo do YouTube ou arquivos de
áudio enviados pelo próprio usuário. Ele produz uma transcrição em Markdown,
separa falantes quando o ambiente permite, mantém histórico local e oferece
exportação, busca e resumo opcional por um servidor compatível com OpenAI.

O projeto foi desenhado para **um único operador autorizado**, em uma máquina
Linux ou WSL2. Não é um serviço público, multiusuário ou hospedado.

## O que ele faz

- aceita um link do YouTube, uma mensagem de voz, um áudio ou um documento de
  áudio no Telegram;
- prefere legendas aproveitáveis do YouTube e usa WhisperX quando necessário;
- converte o áudio com ffmpeg, diariza falantes e entrega Markdown;
- guarda histórico em SQLite, permite renomear/mesclar falantes e exportar
  JSON, SRT, VTT e texto simples;
- gera MP4 com legenda selecionável apenas para origens YouTube compatíveis;
- pesquisa transcrições concluídas, produz resumo opcional e oferece
  `/healthcheck` e `/lasterror` para operação local.

## Começo rápido

Pré-requisitos mínimos: Python 3.11 ou 3.12, [uv](https://docs.astral.sh/uv/),
ffmpeg/ffprobe, uma conta Telegram com bot criado no BotFather e tokens locais
para Telegram e Hugging Face. WhisperX, PyTorch e pyannote são instalados pelo
`uv sync`, mas podem exigir GPU, memória e aceite dos modelos no Hugging Face.

```bash
git clone <repo>
cd yt-transcriber
uv sync --dev
sudo apt install ffmpeg              # Ubuntu/WSL; use o equivalente da sua distro
cp .env.example .env
# edite .env: TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USER_ID e HF_TOKEN
uv run python scripts/config/print_effective_settings.py
uv run python -m yt_transcriber_bot
```

Use `uv run python -m yt_transcriber_bot` ou o comando instalado
`uv run yt-transcriber-bot`. O processo recusa segredos ausentes e verifica as
dependências de runtime antes de iniciar o polling.

Leia o [manual de instalação](docs/04-manual-de-instalacao.md) antes de usar em
um host persistente: ele cobre drivers/GPU, cookies YouTube, Hugging Face, LM
Studio e systemd.

## Uso no Telegram

Envie uma URL do YouTube ou um arquivo de áudio. Para fixar idioma, use
`/pt <link>` ou `/en <link>`; `/transcribe <link>` usa a seleção automática.

| Objetivo | Comando |
|---|---|
| Ajuda e estado | `/help`, `/status`, `/queue` ou `/fila` |
| Cancelar | `/cancel`, `/cancelall` ou `/clearqueue` |
| Histórico | `/list`, `/last [n]`, `/search <texto>` |
| Reprocessar URL | `/redo <link> [--lang pt\|en]` |
| Renomear falantes | `/rename [n]` |
| Resumir | `/summary [n]` |
| Exportar | `/text [n]`, `/json [n]`, `/srt [n]`, `/vtt [n]`, `/export <tipo> [n]` |
| Vídeo com legenda | `/video_subs [n]` (somente YouTube) |
| Diagnosticar | `/healthcheck`, `/lasterror`, `/clearcache` |

`n` é o índice mostrado por `/list`. `/last` reenvia apenas o Markdown salvo;
não reenvia o áudio. `/redo <link>` reprocessa imediatamente e não pede
confirmação inline; confirmação visual e comparação de configuração ainda não
existem.

O bot atende somente `TELEGRAM_ALLOWED_USER_ID`. Arquivos aceitos devem ser
áudio reconhecível, usar extensão suportada (`mp3`, `m4a`, `ogg`, `opus`, `wav`,
`flac` ou `webm`) e respeitar os limites de tamanho e duração configurados.

## Como o processamento funciona

```text
YouTube: URL -> metadados -> legenda aproveitável ou download -> conversão
Telegram: mídia validada e baixada para staging -> conversão
ambos: seleção de runtime -> ASR -> diarização -> Markdown -> entrega/exportação
```

Cada pedido vira um job. A fila de execução é sequencial e fica em memória;
SQLite guarda o estado, origem e dados mínimos necessários para recovery. Após
reinício (restart), pendentes seguros voltam à fila. A deduplicação protege a
mesma origem/idioma em processamento ou na fila; jobs concluídos podem ser
reprocessados. Jobs interrompidos em etapa ativa são marcados como falhos e não
retomam no meio de ASR ou diarização; falha de entrega é `delivery_failed` e
aparece em `/lasterror`.

Aceita links do YouTube, áudio, mensagens de voz e documentos de áudio.

Mídia Telegram é tratada como privada: não recebe URL ou ID sintético do
YouTube. Cada conversão usa um caminho vinculado ao `job_id`, evitando colisão
entre arquivos com o mesmo nome. A política de retenção remove mídia bruta,
conversões e logs associados a jobs antigos, mas preserva Markdown e snapshots
de segmentos para histórico e renomeação de falantes.

## Configuração essencial

`.env.example` contém apenas exemplos. Copie-o para `.env`; ele nunca é usado
como configuração real. Variáveis de ambiente têm precedência e
`YT_TRANSCRIBER_ENV_FILE` permite escolher um arquivo `.env` explícito.

| Grupo | Variáveis importantes |
|---|---|
| Acesso | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_ID`, `HF_TOKEN` |
| YouTube | `YOUTUBE_COOKIES_FILE` ou `YOUTUBE_COOKIES_BROWSER` |
| ASR | `WHISPER_MODEL`, `WHISPER_MODEL_PT`, `WHISPER_MODEL_EN`, `DEVICE`, `COMPUTE_TYPE` |
| Limites | `MAX_VIDEO_DURATION_MIN`, `TELEGRAM_MAX_MEDIA_SIZE_MB`, `TELEGRAM_MAX_QUEUE_SIZE`, `RETENTION_COUNT` |
| Diretórios | `BASE_DIR`, `DB_PATH`, `MODELS_DIR` |
| Resumo | `SUMMARY_BACKEND`, `SUMMARY_BASE_URL`, `SUMMARY_MODEL`, `SUMMARY_API_KEY` |

LM Studio é o backend local recomendado para resumo, mas é opcional: sem ele a
transcrição continua funcionando e apenas `/summary` fica indisponível.

## Documentação

| Documento | Para quê serve |
|---|---|
| [00 — auditoria](docs/00-auditoria-da-documentacao.md) | Mapa desta reconciliação e decisões de escopo. |
| [01 — contrato funcional](docs/01-contrato-funcional.md) | O que o produto faz e não faz. |
| [02 — arquitetura](docs/02-arquitetura.md) | Camadas, pipeline, dados e recovery. |
| [03 — manual de uso](docs/03-manual-de-uso.md) | Referência de comandos e exemplos. |
| [04 — instalação](docs/04-manual-de-instalacao.md) | Dependências, configuração e execução. |
| [06 — roadmap](docs/06-funcionalidades-futuras.md) | Próximas capacidades, sem promessas de entrega. |
| [07 — glossário e decisões](docs/07-glossario-e-decisoes.md) | Vocabulário e decisões duráveis. |
| [08 — segurança](docs/08-seguranca-e-segredos.md) | Dados privados, segredos e verificações. |
| [09 — prontidão](docs/09-production-readiness.md) | Estado e lacunas para operação privada. |
| [10 — ADR de recovery](docs/10-recovery-semantics-adr.md) | Semântica de reinício. |
| [11 — runbook](docs/11-operator-runbook.md) | Operação systemd, backup e incidentes. |

`/translate` e busca semântica continuam planejados; não são comandos atuais.

`docs/05-plano-de-execucao.md`, `docs/gate-reports/` e `docs/patches/` são
histórico e evidência; não substituem os guias acima. Evidências operacionais
geradas em `ops-evidence/` são locais, contêm dados sensíveis e são ignoradas
pelo Git.

## Verificação local

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run pre-commit run --all-files
python3 scripts/security/scan_secrets.py --all
```

Nunca versiona `.env`, cookies, tokens, banco SQLite, mídia, transcrições,
modelos ou logs. Consulte a [política de segurança](docs/08-seguranca-e-segredos.md)
antes de compartilhar diagnósticos ou backups.
