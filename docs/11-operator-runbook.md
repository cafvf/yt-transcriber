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

Os helpers são mutáveis: podem parar/iniciar o serviço e trocar a revisão Git
durante um ensaio de rollback. O caminho principal falha logo após uma operação
crítica malsucedida. Na recuperação, cada compensação é tentada de forma
independente — inclusive o `systemctl start` final — e falhas secundárias são
anexadas ao erro principal. Execute-os somente em host/staging autorizado,
leia o relatório gerado e nunca trate a geração do arquivo como prova de êxito.
Os diretórios de sessão e backup são criados com `0700`; cópias, bancos e
tarballs recebem `0600`.

Evidência mínima por ensaio:

| Ensaio | Deve comprovar |
|---|---|
| Backup/restore | Backup criado, restore executado em serviço parado ou staging isolado, banco abre depois do restore e `/healthcheck`, `/status` e `/list` foram registrados após o start. |
| systemd start/stop/restart/rollback | `start`, `status`, `stop`, `restart` e rollback executados no serviço real, com `journalctl`, `/healthcheck` e `/status` depois das transições críticas. |
| `delivery_failed`/recuperação manual | Job controlado chegou a `delivery_failed`, `/lasterror` trouxe paths/contexto sanitizados, artefatos foram localizados no host e a recuperação manual foi documentada. |
| Job interrompido/restart recovery | Interrupção ocorreu durante estado ativo controlado e, após restart, `/status`, `/list`, `/lasterror` ou `execution_audit.jsonl` demonstraram requeue de `pending` ou reconciliação para `failed`/`delivery_failed`. |

---

## 2. Pré-flight antes de produção privada

Comece pelo contrato read-only de host/systemd:

```bash
cd ~/yt-transcriber-bot
uv run python scripts/ops/systemd_host_preflight.py --service yt-transcriber-bot --output ~/Downloads/p06-005-preflight.json
```

O relatório não lê nem imprime os valores do arquivo secreto; valida somente caminho, owner/mode e propriedades não-secretas do serviço. Saídas levadas a superfícies de colaboração devem ser sanitizadas. O `systemd-smoke` sanitiza stdout/stderr antes de gravar evidência.

Depois execute no diretório do projeto:

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

Antes do primeiro start e após mudanças na unit/env, reexecute `scripts/ops/systemd_host_preflight.py`. Falha de conta não-root, owner/mode do env ou pré-requisito é evidência Red e deve ser corrigida antes do smoke.

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

## 4. Backup padrão credential-free

O backup operacional padrão é um **backup de dados duráveis**, não uma cópia da
instalação inteira. Ele continua sendo dado privado e deve permanecer sob acesso
restrito, mas **não carrega credenciais reutilizáveis**.

### 4.1 Contrato do conjunto padrão

Incluído:

| Classe | Artefato | Razão |
|---|---|---|
| Estado/histórico | `jobs.db` | Jobs, histórico e associações persistidas. |
| Evidência canônica | `canonical-transcripts.tgz` | Markdown e snapshots JSON versionados de `data/transcripts/`. |
| Contrato/revisão | `backup-contract.json`, `git-revision.txt` | Reprodutibilidade e validação do conjunto. |

Excluído do backup padrão:

- `.env`, arquivo de ambiente/segredos do systemd e credenciais de providers;
- cookies do navegador/YouTube e qualquer outro material de autenticação reutilizável;
- mídia staged/downloaded, áudio convertido e outros artefatos voláteis;
- logs operacionais;
- summaries, exports e vídeos derivados, que não são fonte canônica de verdade;
- modelos e caches reconstruíveis.

Credenciais e cookies devem ser **reprovisionados separadamente** no host de destino.
Nunca copie `systemd-env`, `.env` ou cookies para dentro do diretório do backup padrão.

### 4.2 Criar o backup padrão

O helper é a referência executável do contrato local:

```bash
cd ~/yt-transcriber-bot
uv run python scripts/ops/phase4_phase8_rehearsal.py backup \
  --output-dir "$HOME/yt-transcriber-backups"
```

Para um backup frio em host autorizado:

```bash
uv run python scripts/ops/phase4_phase8_rehearsal.py backup \
  --stop-service \
  --start-service \
  --service yt-transcriber-bot \
  --output-dir "$HOME/yt-transcriber-backups"
```

Se `DB_PATH` ou o diretório canônico de transcrições forem customizados, informe
`--db-path` e `--transcripts-dir`. O helper usa a API `sqlite3.Connection.backup()`,
gera um archive limitado a `transcripts/`, grava o contrato em JSON, executa
`PRAGMA integrity_check` na cópia e rejeita nomes conhecidos de arquivos de
credencial/cookie no diretório de backup.

A criação bem-sucedida deste conjunto é **evidência local de composição e integridade
do backup**, não prova de restauração.

### 4.3 Backup online apenas do SQLite

Uma cópia online do SQLite pode ser útil para diagnóstico ou proteção adicional,
mas não substitui o conjunto padrão quando é necessário preservar também Markdown
e snapshots canônicos. Use sempre a API de backup do SQLite; não copie o arquivo
`jobs.db` cru enquanto houver escrita concorrente.

---

## 5. Fronteira de restore deste round

`TASK-P06-002` define o **contrato de dados**. O procedimento operacional completo
de restore, incluindo staging/serviço parado, validação das relações canônicas e
evidência pós-restore, pertence a `TASK-P06-006`.

Até `TASK-P06-006` fechar:

1. não trate a simples criação do backup como prova de restore;
2. não restaure `.env`, systemd env ou cookies a partir do backup padrão — eles não
   devem existir nele;
3. qualquer ensaio deve ocorrer em staging isolado ou com o serviço parado;
4. a evidência futura precisa demonstrar abertura/integridade do SQLite, preservação
   de `canonical_transcript_ref`→snapshot e `md_path`→Markdown, além de
   `/healthcheck`, `/status` e `/list` após o restore;
5. credenciais/cookies são provisionados separadamente depois que os dados duráveis
   forem restaurados.

O helper deste Round A valida composição e integridade do **backup**; ele
deliberadamente não implementa nem simula a restauração real de `TASK-P06-006`.

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

## 8. PLAN-006 / P06-006 — backup credential-free e restore validado

O backup operacional padrão é deliberadamente **credential-free**. Ele inclui somente o banco SQLite de Jobs/histórico, os transcripts canônicos (Markdown + snapshots estruturados), a revisão Git e o contrato do backup. `.env`, `/etc/yt-transcriber-bot/env`, cookies de autenticação, logs, mídia volátil, modelos e caches reconstruíveis ficam fora do conjunto e devem ser reprovisionados separadamente.

### 8.1 Backup controlado no host

Para um rehearsal operacional conservador, pare o serviço durante a captura do conjunto completo e reinicie ao final:

```bash
cd ~/git/yt-transcriber
uv run python scripts/ops/phase4_phase8_rehearsal.py backup \
  --service yt-transcriber-bot \
  --stop-service \
  --start-service \
  --output-dir ~/Downloads/p06-006-backup
```

O banco é copiado por `sqlite3.Connection.backup()` e o helper valida `PRAGMA integrity_check`, composição do backup e exclusão de credenciais/cookies antes de produzir evidência.

### 8.2 Restore obrigatório primeiro em staging isolado

Nunca valide um backup pela primeira vez sobre o diretório operacional. Restaure-o em uma árvore vazia fora do repositório:

```bash
uv run python scripts/ops/phase4_phase8_rehearsal.py restore-staging \
  --backup-dir ~/Downloads/p06-006-backup/backup-<TIMESTAMP> \
  --restore-root ~/Downloads/p06-006-restore-staging \
  --output-dir ~/Downloads/p06-006-restore-evidence
```

O restore staging recusa a árvore da aplicação como destino, recusa destino não vazio, extrai o archive canônico sem links/path traversal e valida: abertura do SQLite, `PRAGMA integrity_check`, tabela `jobs`, contagem de histórico e referências `canonical_transcript_ref`/documentos de busca contra os snapshots restaurados. Quando `md_path` existe, o Markdown correspondente também deve existir.

### 8.3 Evidência pós-restore

Após o restore staging, mantenha o serviço operacional com suas credenciais/cookies originais e capture:

```text
/healthcheck
/status
/list
```

A evidência de P06-006 é composta pelo relatório do backup, relatório do restore staging e checkpoints sanitizados de health/status/history. O rehearsal real desta tarefa também pode satisfazer a evidência compatível de P06-002; não repita a mesma operação apenas para bookkeeping.

## 9. PLAN-006 / P06-007 — upgrade e rollback versionados

O procedimento de upgrade/rollback parte de uma revisão Git conhecida, exige backup credential-free previamente validado e não autoriza migração destrutiva silenciosa.

### 9.1 Preflight read-only

Antes de qualquer troca de revisão:

```bash
uv run python scripts/ops/upgrade_rollback_rehearsal.py preflight \
  --backup-dir ~/Downloads/p06-007-backup/backup-<TIMESTAMP> \
  --from-ref <REVISAO_ANTERIOR> \
  --to-ref <REVISAO_ALVO> \
  --output-dir ~/Downloads/p06-007-preflight
```

O preflight exige worktree limpo, resolve as duas revisões para SHAs, verifica que a revisão anterior é ancestral da revisão alvo, valida o contrato do backup e exige que `git-revision.txt` do backup corresponda exatamente à revisão anterior. O preflight não executa checkout, não reinicia serviço e registra `production_mutated=false`.

### 9.2 Rehearsal real explicitamente opt-in

O rehearsal real só deve ser executado depois que a revisão alvo estiver commitada e publicada, com o checkout de produção limpo e já na revisão alvo:

```bash
uv run python scripts/ops/upgrade_rollback_rehearsal.py rehearsal \
  --backup-dir ~/Downloads/p06-007-backup/backup-<TIMESTAMP> \
  --from-ref <REVISAO_ANTERIOR> \
  --to-ref <REVISAO_ALVO> \
  --service yt-transcriber-bot \
  --output-dir ~/Downloads/p06-007-rehearsal \
  --execute
```

A sequência controlada demonstra: revisão anterior conhecida → upgrade para a revisão alvo → rollback de código para a revisão anterior → validação do backup em staging isolado → retorno final à revisão alvo. O helper recusa execução sem `--execute`, worktree sujo, backup associado a outra revisão ou relação de upgrade não ancestral.

O procedimento não executa rollback destrutivo de banco por padrão. Quando uma mudança futura introduzir migração incompatível/destrutiva, o deploy deve parar antes da produção até existir uma estratégia explícita e testada de dados compatíveis usando o backup aprovado.

Após o rehearsal, capture no Telegram:

```text
/healthcheck
/status
```

e preserve o relatório sanitizado de `journalctl` gerado pelo helper. Evidência de backup/restore já válida pode ser reutilizada; não repita operações apenas para bookkeeping.

## 10. PLAN-006 / P06-008 — recuperação manual após `delivery_failed`

A recuperação desta baseline é deliberadamente manual. Ela não reabre o Job terminal, não
recomputa transcrição/diarização/renderização e não dispara reenvio automático ao Telegram.

### 10.1 Identificar o Job e a disponibilidade

Primeiro use `/lasterror`. Para um Job em `delivery_failed`, a resposta informa se existem
artefatos locais recuperáveis, mas não publica caminhos privados no Telegram.

No host, use o `job_id` informado por `/lasterror` para inspecionar as referências persistidas:

```bash
cd ~/git/yt-transcriber
uv run python scripts/ops/manual_artifact_recovery.py \
  --db-path data/jobs.db \
  --job-id <JOB_ID> \
  --output ~/Downloads/p06-008-inspect.json \
  inspect
```

O relatório privado distingue:

- `available`: referência persistida e arquivo local existente;
- `reference_absent`: não há referência persistida; para artefatos voláteis isso pode refletir
  ausência ou purga legítima por retenção;
- `referenced_missing`: a referência persiste, mas o arquivo não existe no disco.

A retenção de Completed Jobs não autoriza remover Markdown nem transcript canônico. Portanto,
Markdown ausente deve ser tratado como indisponível/anômalo, não como artefato recuperável.

### 10.2 Copiar um artefato existente

A cópia exige opt-in explícito, restringe a origem a uma raiz permitida, recusa symlinks,
não sobrescreve destino existente e grava a cópia com modo `0600`:

```bash
uv run python scripts/ops/manual_artifact_recovery.py \
  --db-path data/jobs.db \
  --job-id <JOB_ID> \
  copy \
  --artifact markdown \
  --allowed-root data \
  --destination ~/Downloads/recovered-<JOB_ID>.md
```

Se os dados estiverem fora de `data`, informe explicitamente a raiz operacional aprovada em
`--allowed-root`. A cópia não altera o Job, não altera o artefato de origem e não envia nada
a serviços externos.

### 10.3 Evidência de rehearsal

Para P06-008, produza/identifique um `delivery_failed` controlado em host/staging, capture
`/lasterror`, execute `inspect`, copie um artefato existente para um destino privado e confirme:

1. o Job permanece `delivery_failed`;
2. o arquivo recuperado é byte-a-byte equivalente ao artefato persistido;
3. a origem permanece intacta;
4. nenhum reenvio automático ocorre;
5. um artefato ausente/purgado é reportado como indisponível, nunca como recuperável.

Preserve apenas evidência sanitizada/privada. Não publique caminhos, conteúdo de artefatos,
IDs privados ou credenciais.
