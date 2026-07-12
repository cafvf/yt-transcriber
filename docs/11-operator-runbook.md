# Runbook do operador

Este runbook cobre a operação privada/single-operator do YT Transcriber Bot em um host Linux gerenciado por systemd. Ele complementa o [manual de instalação](./04-manual-de-instalacao.md), o [manual de uso](./03-manual-de-uso.md) e a [política de segurança](./08-seguranca-e-segredos.md).

Escopo atual:

- instalação e operação em um único host;
- um único usuário autorizado no Telegram;
- SQLite local em `DB_PATH` (`data/jobs.db` por padrão);
- artefatos locais sob `BASE_DIR` (`data/` por padrão) e modelos sob `MODELS_DIR` (`models/` por padrão);
- serviço systemd opcional usando `deploy/yt-transcriber-bot.service`.

Não cobre produção pública/multiusuário, cotas, alertas externos, Docker Compose ou retomada seletiva no meio de ASR/diarização.

---

## 1. Mapa operacional rápido

| Ação | Comando/caminho principal | Quando usar |
|---|---|---|
| Ver serviço | `sudo systemctl status yt-transcriber-bot` | Bot não responde ou após restart. |
| Acompanhar logs | `journalctl -u yt-transcriber-bot -f` | Diagnóstico de startup/crash. |
| Diagnóstico pelo Telegram | `/healthcheck` | Depois de mudar `.env`, atualizar dependências ou trocar modelo. |
| Último erro | `/lasterror` | Job falhou, entrega Telegram falhou ou `/summary`/exportação falhou. |
| Fila/status | `/status`, `/queue` | Ver job atual e pendentes. |
| Parar com segurança | `sudo systemctl stop yt-transcriber-bot` | Backup frio, restore, upgrade ou manutenção. |
| Reiniciar | `sudo systemctl restart yt-transcriber-bot` | Após alterar env, atualizar código ou renovar cookies. |
| Logs operacionais | `data/logs/operational_errors.jsonl` | Erros persistidos para `/lasterror`. |
| Auditoria de execução | `data/logs/execution_audit.jsonl` | Eventos locais de fila/job/etapa/recovery. |
| Banco SQLite | `data/jobs.db` por padrão | Histórico, estados e payload mínimo de restart. |

---

### 1.1 Registro de evidência para ensaios Phase 4/8

Os procedimentos deste runbook ainda precisam ser ensaiados em host ou staging
real antes de declarar produção privada completa. Para cada ensaio, crie um
registro de evidência sanitizado com:

- data UTC, host/ambiente, operador, commit Git e caminho do registro;
- objetivo do ensaio e estado inicial conhecido;
- comandos executados ou ações Telegram realizadas, na ordem;
- trechos relevantes de saída, sem tokens, cookies, transcrições privadas ou
  caminhos que não possam ser compartilhados com o time;
- resultado esperado, resultado observado e decisão: passou, falhou ou passou
  com ressalvas;
- ação corretiva ou follow-up, quando houver.

Se um helper de template de evidência estiver disponível no repositório, use-o
apenas para gerar o esqueleto do registro. O helper não substitui os comandos
reais, os trechos de log nem a decisão operacional assinada pelo operador.

Helpers locais atualmente disponíveis:

- `uv run python scripts/ops/create_phase4_phase8_evidence.py --output-dir ops-evidence`
  cria o Markdown-base do relatório;
- `uv run python scripts/ops/run_phase4_phase8_full_rehearsal.py --output-dir ops-evidence`
  orquestra a sessão completa: chama os helpers automatizados, pausa para
  checkpoints Telegram/manuais e grava um relatório consolidado por sessão;
- `uv run python scripts/ops/phase4_phase8_rehearsal.py backup`
  executa backup real e salva um snippet Markdown com artefatos/comandos;
- `uv run python scripts/ops/phase4_phase8_rehearsal.py systemd-smoke --service yt-transcriber-bot`
  executa smoke de `status`/`stop`/`start`/`restart`/`journalctl`;
- `uv run python scripts/ops/phase4_phase8_rehearsal.py inspect-delivery-failed`
  captura jobs `delivery_failed` e eventos `transcribe_delivery`;
- `uv run python scripts/ops/phase4_phase8_rehearsal.py inspect-restart-recovery`
  captura jobs/JSONL úteis para o ensaio de restart recovery.

Evidência mínima por ensaio:

| Ensaio | Deve comprovar |
|---|---|
| Backup/restore | Backup criado, restore executado em serviço parado ou staging isolado, banco abre depois do restore e `/healthcheck`, `/status` e `/list` foram registrados após o start. |
| systemd start/stop/restart/rollback | `start`, `status`, `stop`, `restart` e rollback executados no serviço real, com `journalctl`, `/healthcheck` e `/status` depois das transições críticas. |
| `delivery_failed`/recuperação manual | Job controlado chegou a `delivery_failed`, `/lasterror` trouxe paths/contexto sanitizados, artefatos foram localizados no host e a recuperação manual foi documentada. |
| Job interrompido/restart recovery | Interrupção ocorreu durante estado ativo controlado e, após restart, `/status`, `/list`, `/lasterror` ou `execution_audit.jsonl` demonstraram requeue de `pending` ou reconciliação para `failed`/`delivery_failed`. |

---

## 2. Pré-flight antes de produção privada

Execute no diretório do projeto:

```bash
cd ~/yt-transcriber-bot
uv sync --locked
uv run python scripts/config/print_effective_settings.py
uv run python - <<'PY'
import importlib.util
for module in ["telegram", "yt_dlp", "sqlalchemy", "torch", "whisperx", "pyannote.audio"]:
    try:
        present = importlib.util.find_spec(module) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        present = False
    print(module, "OK" if present else "FALTANDO")
PY
ffmpeg -version | head -1
ffprobe -version | head -1
```

Depois de iniciar o bot, valide no Telegram:

```text
/healthcheck
```

O `/healthcheck` deve ser a triagem inicial. Ele verifica configuração obrigatória, `.env` efetivo, `ffmpeg`/`ffprobe`/`yt-dlp`, módulos Python, diretórios graváveis, SQLite, espaço livre, cookies do YouTube, backend de sumarização, tokenizer e presença de `SUMMARY_MODEL` em `/v1/models` quando aplicável.

### 2.1 Como interpretar `/healthcheck`

| Resultado | Interpretação | Próxima ação |
|---|---|---|
| `✅ Healthcheck: OK` | Dependências e configuração essenciais passaram. | Rode `/status` e envie um link curto de smoke se for primeira implantação. |
| `⚠️ OK com avisos` | O bot pode funcionar, mas há risco operacional. | Leia cada aviso; cookies ausentes, tokenizer em estimativa ou sumarização desabilitada podem ser aceitáveis se forem intencionais. |
| `❌ problemas encontrados` | Algo essencial falhou. | Corrija antes de processar vídeos longos; use `journalctl -u yt-transcriber-bot -n 120 --no-pager` se a falha aparecer no startup. |

Itens que podem expor metadados privados mesmo sanitizados: paths locais, `user_id`, nomes de modelos, nomes de arquivos e contagens de registros. Não cole a saída completa em chats públicos.

---

## 3. Operação com systemd

Os exemplos assumem:

```bash
APP_DIR="$HOME/yt-transcriber-bot"
SERVICE="yt-transcriber-bot"
ENV_FILE="/etc/yt-transcriber-bot/env"
```

### 3.1 Instalar ou revisar o serviço

```bash
cd "$APP_DIR"
which uv
sudo cp deploy/yt-transcriber-bot.service /etc/systemd/system/yt-transcriber-bot.service
sudo systemctl daemon-reload
sudo systemctl enable yt-transcriber-bot
```

Revise `/etc/systemd/system/yt-transcriber-bot.service` antes de iniciar. `User`, `Group`, `WorkingDirectory` e `ExecStart` devem apontar para o usuário real, diretório real e binário `uv` real.

### 3.2 Start, stop, restart e logs

```bash
sudo systemctl start yt-transcriber-bot
sudo systemctl status yt-transcriber-bot --no-pager
journalctl -u yt-transcriber-bot -n 80 --no-pager
```

Operações comuns:

```bash
sudo systemctl stop yt-transcriber-bot
sudo systemctl restart yt-transcriber-bot
journalctl -u yt-transcriber-bot -f
```

Após cada restart operacional, rode no Telegram:

```text
/healthcheck
/status
/lasterror
```

Para o smoke de systemd contar como evidência Phase 4/8, registre também:

- saída sanitizada de `systemctl status` antes e depois de `start`, `stop` e
  `restart`;
- trecho de `journalctl` cobrindo cada transição;
- resultado de `/healthcheck` e `/status` depois do start/restart;
- revisão Git inicial, revisão após upgrade e revisão restaurada no rollback,
  quando o ensaio incluir rollback.

### 3.3 Parada segura

Prefira parar o serviço antes de backup frio, restore, troca de branch ou limpeza manual pesada:

```bash
sudo systemctl stop yt-transcriber-bot
sudo systemctl status yt-transcriber-bot --no-pager
```

Se houver job ativo, a Phase 2 não retoma o meio da etapa. Ao voltar, jobs `pending` com payload de restart são re-enfileirados; jobs interrompidos em download/conversão/transcrição/diarização/renderização viram `failed`; jobs interrompidos em `delivering` viram `delivery_failed`.

---

## 4. Backup

Backups podem conter transcrições privadas, áudio, caminhos locais, cookies e segredos. Guarde-os com permissão restrita, criptografia ou volume protegido.

### 4.1 Backup recomendado antes de upgrade/manutenção

```bash
set -euo pipefail
APP_DIR="$HOME/yt-transcriber-bot"
SERVICE="yt-transcriber-bot"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$HOME/yt-transcriber-backups/$STAMP"

mkdir -p "$BACKUP_DIR"
cd "$APP_DIR"
sudo systemctl stop "$SERVICE"
test -f "$APP_DIR/data/jobs.db"

uv run python - "$APP_DIR/data/jobs.db" "$BACKUP_DIR/jobs.db" <<'PY'
import sqlite3
import sys
source, target = sys.argv[1:3]
with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
    src.backup(dst)
PY

tar -C "$APP_DIR" -czf "$BACKUP_DIR/runtime-data.tgz" data
[ -d "$APP_DIR/models" ] && tar -C "$APP_DIR" -czf "$BACKUP_DIR/models.tgz" models || true
sudo cp /etc/yt-transcriber-bot/env "$BACKUP_DIR/systemd-env" 2>/dev/null || true
cp .env "$BACKUP_DIR/dotenv" 2>/dev/null || true
git rev-parse HEAD > "$BACKUP_DIR/git-revision.txt"
chmod -R go-rwx "$BACKUP_DIR"

sudo systemctl start "$SERVICE"
echo "Backup criado em: $BACKUP_DIR"
```

Esse backup guarda:

- `jobs.db` via API de backup do SQLite;
- `data/` com banco, downloads, processed, transcripts, summaries, video exports e logs;
- `models/`, se existir;
- arquivo de ambiente systemd e `.env`, se existirem;
- revisão Git atual para rollback.

Se você customizou `DB_PATH`, `BASE_DIR` ou `MODELS_DIR`, ajuste os caminhos no comando.

### 4.2 Backup online só do SQLite

Use quando não puder parar o serviço e precisar de uma cópia consistente do banco. Ele não garante consistência com artefatos gerados ao mesmo tempo.

```bash
set -euo pipefail
APP_DIR="$HOME/yt-transcriber-bot"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$HOME/yt-transcriber-backups/$STAMP"
mkdir -p "$BACKUP_DIR"
cd "$APP_DIR"
test -f "$APP_DIR/data/jobs.db"

uv run python - "$APP_DIR/data/jobs.db" "$BACKUP_DIR/jobs.db" <<'PY'
import sqlite3
import sys
source, target = sys.argv[1:3]
with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
    src.backup(dst)
PY
chmod -R go-rwx "$BACKUP_DIR"
```

---

## 5. Restore

Restaure apenas em uma instalação parada. Antes de sobrescrever qualquer coisa, faça uma cópia do estado atual.

```bash
set -euo pipefail
APP_DIR="$HOME/yt-transcriber-bot"
SERVICE="yt-transcriber-bot"
BACKUP_DIR="$HOME/yt-transcriber-backups/20260708T120000Z"  # ajuste

cd "$APP_DIR"
test -d "$BACKUP_DIR"
sudo systemctl stop "$SERVICE"
mkdir -p "$HOME/yt-transcriber-restore-safety"
tar -C "$APP_DIR" -czf "$HOME/yt-transcriber-restore-safety/pre-restore-data.tgz" data 2>/dev/null || true
cp data/jobs.db "$HOME/yt-transcriber-restore-safety/jobs.db.before-restore" 2>/dev/null || true

rm -rf data
tar -C "$APP_DIR" -xzf "$BACKUP_DIR/runtime-data.tgz"
cp "$BACKUP_DIR/jobs.db" data/jobs.db

if [ -f "$BACKUP_DIR/systemd-env" ]; then
  sudo cp "$BACKUP_DIR/systemd-env" /etc/yt-transcriber-bot/env
  sudo chmod 600 /etc/yt-transcriber-bot/env
  sudo chown root:root /etc/yt-transcriber-bot/env
fi

if [ -f "$BACKUP_DIR/models.tgz" ]; then
  rm -rf models
  tar -C "$APP_DIR" -xzf "$BACKUP_DIR/models.tgz"
fi

sudo systemctl start "$SERVICE"
sudo systemctl status "$SERVICE" --no-pager
```

Após restore, rode no Telegram:

```text
/healthcheck
/status
/list
/lasterror
```

Se o restore trouxe jobs `pending`, o startup recovery deve re-enfileirá-los. Se trouxe jobs interrompidos em estados ativos antigos, eles devem ser reconciliados para `failed` ou `delivery_failed`.

Para o ensaio de backup/restore contar como evidência Phase 4/8, registre o
diretório do backup, commit Git, confirmação de que o serviço estava parado ou
que o restore ocorreu em staging isolado, saída sanitizada dos comandos de
restore, `systemctl status` após o start e os resultados de `/healthcheck`,
`/status` e `/list`. Não publique o conteúdo de backups, `.env`, cookies ou
transcrições privadas.

---

## 6. Upgrade e rollback

### 6.1 Upgrade seguro

```bash
set -euo pipefail
APP_DIR="$HOME/yt-transcriber-bot"
SERVICE="yt-transcriber-bot"
cd "$APP_DIR"

OLD_REV="$(git rev-parse HEAD)"
echo "$OLD_REV" > /tmp/yt-transcriber-old-rev
# Rode o backup recomendado do item 4.1 antes de continuar.

sudo systemctl stop "$SERVICE"
git fetch --all --prune
git pull --ff-only
uv sync --locked
uv run python scripts/config/print_effective_settings.py
sudo systemctl start "$SERVICE"
sudo systemctl status "$SERVICE" --no-pager
```

Valide pelo Telegram:

```text
/healthcheck
/help
/status
```

Se `/healthcheck` falhar por LM Studio, confirme se o servidor local está ativo e se `SUMMARY_MODEL` aparece em `GET /v1/models`.

### 6.2 Rollback por Git

Use quando a versão nova falhar antes de alterar dados de forma incompatível. A Phase 2 usa migração SQLite aditiva; ainda assim, prefira restaurar o backup se houver dúvida.

```bash
set -euo pipefail
APP_DIR="$HOME/yt-transcriber-bot"
SERVICE="yt-transcriber-bot"
OLD_REV="$(cat /tmp/yt-transcriber-old-rev)"  # ou leia git-revision.txt do backup
cd "$APP_DIR"

sudo systemctl stop "$SERVICE"
git checkout "$OLD_REV"
uv sync --locked
sudo systemctl start "$SERVICE"
sudo systemctl status "$SERVICE" --no-pager
```

Se o rollback de código não bastar, execute o restore completo do item 5 usando o backup feito antes do upgrade.

Para o ensaio de rollback contar como evidência Phase 4/8, registre a revisão
antes do upgrade, a revisão testada, a revisão restaurada, a estratégia usada
(`git checkout` ou restore completo), `journalctl` da falha ou do smoke e
`/healthcheck` mais `/status` após o rollback.

---

## 7. Recovery de falhas comuns

### 7.1 Entrega Telegram falhou (`delivery_failed`)

Sintomas:

- Telegram mostra aviso de transcrição gerada, mas entrega falhou;
- `/list` mostra job com status `delivery_failed`;
- `/lasterror` mostra `Status: delivery_failed` ou operação `transcribe_delivery`.

Procedimento:

1. Rode `/lasterror`.
2. Copie os paths locais de `Markdown parcial`/`Áudio parcial` ou `md_path`/`audio_path` no contexto.
3. No host, confirme os arquivos:
   ```bash
   ls -lh /caminho/mostrado/pelo/lasterror
   ```
4. Recupere manualmente por `scp`, cópia local ou reenvio fora do bot.
5. Se quiser novo envio pelo bot e o problema do Telegram já foi resolvido, reenvie o link ou use `/redo <link>`.

O bot não tem, nesta versão, comando dedicado para reenviar automaticamente artefatos de um job `delivery_failed`.

Para este ensaio contar como evidência Phase 4/8, registre o job de teste, a
forma controlada de induzir ou observar `delivery_failed`, a saída sanitizada de
`/lasterror`, a confirmação de que os paths locais existem e o método usado para
recuperar manualmente os artefatos. O registro deve deixar claro que não houve
reenvio automático pelo bot.

### 7.2 Processo caiu ou host reiniciou durante job

Após o serviço voltar:

```text
/status
/list
/lasterror
```

Interpretação atual:

- `pending` com payload de restart volta para a fila;
- `downloading`, `converting`, `transcribing`, `diarizing` e `rendering` interrompidos viram `failed`;
- `delivering` interrompido vira `delivery_failed`;
- `completed`, `failed`, `cancelled` e `delivery_failed` permanecem como estavam.

Para jobs que viraram `failed`, reenvie o link ou use `/redo <link>`. Não há retomada no meio de download, ASR, diarização ou renderização.

Para este ensaio contar como evidência Phase 4/8, registre em qual estado o job
foi interrompido, como o processo/serviço foi parado, a saída de `systemctl` ou
`journalctl` ao voltar, e a evidência de `/status`, `/list`, `/lasterror` ou
`execution_audit.jsonl` mostrando requeue de `pending` ou reconciliação para
`failed`/`delivery_failed`.

### 7.3 Bot não responde

1. Verifique systemd:
   ```bash
   sudo systemctl status yt-transcriber-bot --no-pager
   journalctl -u yt-transcriber-bot -n 120 --no-pager
   ```
2. Confirme env e dependências:
   ```bash
   cd ~/yt-transcriber-bot
   uv run python scripts/config/print_effective_settings.py
   ffmpeg -version | head -1
   ```
3. Se o processo está vivo mas você não recebe resposta, confirme `TELEGRAM_ALLOWED_USER_ID`.
4. Reinicie:
   ```bash
   sudo systemctl restart yt-transcriber-bot
   ```

### 7.4 `/summary` falha

1. Rode `/lasterror` para ver operação, etapa e erro sanitizado.
2. Rode `/healthcheck` para validar `SUMMARY_BASE_URL`, `SUMMARY_MODEL`, tokenizer e modo sem thinking.
3. Teste o servidor:
   ```bash
   curl http://127.0.0.1:1234/v1/models
   ```
4. Se o erro for contexto excedido, reduza `SUMMARY_MAX_INPUT_TOKENS` e `SUMMARY_MAX_CHARS_PER_CHUNK` no `.env` e reinicie.

### 7.5 Banco e artefatos parecem divergentes

Sintomas típicos: `/list` mostra um job concluído, mas `/last`, `/summary`, `/export` ou `/video_subs` não encontra o arquivo local. Isso costuma acontecer depois de limpeza manual, restore parcial ou mudança de `BASE_DIR`.

Procedimento conservador:

1. Pare o serviço antes de mexer em arquivos:
   ```bash
   sudo systemctl stop yt-transcriber-bot
   ```
2. Faça cópia de segurança do estado atual, mesmo que pareça quebrado.
3. Compare os paths do job via `/lasterror` ou banco SQLite com o conteúdo de `data/transcripts`, `data/processed` e `data/downloads`.
4. Se o artefato final foi perdido, reenvie o link ou use `/redo <link>`.
5. Se o problema veio de restore parcial, restaure novamente usando o backup completo do item 5.

Não edite `data/jobs.db` manualmente salvo em investigação isolada e com backup.

---

## 8. Modelos, caches e disco

### 8.1 O que ocupa espaço

- `models/`: cache configurado do bot para modelos quando usado pelo adapter.
- `~/.cache/huggingface`: cache padrão do Hugging Face/transformers/pyannote quando bibliotecas usam o default.
- `data/downloads`, `data/processed`, `data/video_exports`: mídia e artefatos temporários/derivados.
- `data/transcripts` e `data/summaries`: artefatos finais pequenos, mas privados.
- `data/logs`: logs operacionais e auditoria.

### 8.2 Limpeza pelo bot

Use no Telegram:

```text
/clearcache
```

O comando remove arquivos dentro do diretório de modelos configurado e recusa diretórios amplos/inseguros. Modelos ausentes serão baixados novamente na próxima transcrição.

### 8.3 Limpeza manual emergencial

Pare o serviço antes de apagar diretórios manualmente:

```bash
APP_DIR="$HOME/yt-transcriber-bot"
SERVICE="yt-transcriber-bot"
cd "$APP_DIR"
sudo systemctl stop "$SERVICE"

du -h -d 2 data models ~/.cache/huggingface 2>/dev/null | sort -h
# Exemplos conservadores: apague apenas caches/derivados que você aceita recriar.
rm -rf data/downloads/* data/processed/* data/video_exports/*
# Opcional e caro: força novo download de modelos Hugging Face.
# rm -rf ~/.cache/huggingface

sudo systemctl start "$SERVICE"
```

Não apague `data/jobs.db`, `data/transcripts`, `data/summaries` ou `data/logs` sem backup se quiser preservar histórico, artefatos e diagnóstico.

---

## 9. Segurança operacional

- Não cole `/lasterror`, logs completos ou backups em chats públicos. Eles são sanitizados para segredos comuns, mas ainda podem conter caminhos locais, IDs e metadados privados.
- Trate backups como dados sensíveis: `chmod -R go-rwx`, volume criptografado e retenção curta.
- Cookies do YouTube equivalem a sessão autenticada. Renove e proteja o arquivo com `chmod 600`.
- Não versionar `.env`, `/etc/yt-transcriber-bot/env`, cookies, bancos SQLite, logs, áudio, vídeo, transcrições ou backups.
- Antes de publicar patches, rode os scanners do projeto descritos em [segurança e segredos](./08-seguranca-e-segredos.md).

---

## 10. Limitações residuais atuais

- A fila operacional ainda é em memória; a durabilidade atual vem de recovery orientado por `jobs` no startup.
- Não há tabela `queue` separada nem retomada por checkpoint de download/ASR/diarização/renderização.
- Não há comando para reenviar automaticamente artefatos de `delivery_failed`.
- Não há `LOG_FORMAT=json`; logs Python continuam em texto, enquanto `operational_errors.jsonl` e `execution_audit.jsonl` são JSONL estruturados.
- Não há alertas externos, métricas Prometheus, cotas multiusuário ou hardening para bot público.
- O baseline default da Phase 5 está limpo em 2026-07-09, incluindo `mypy` em CI; reexecute os gates após mudanças e mantenha checks ML/network/e2e como validações environment-gated.
