# Checklist de prontidão para produção

Este ledger acompanha a trilha de maturidade aprovada em
`.omx/plans/prd-production-maturity-20260704T195723Z.md`.

Escopo da meta atual: **produção privada/single-operator**. A Phase 0 e as
Phases 1, 2, 3 e 5 estão fechadas para o baseline atual, e os ensaios
operacionais de Phase 4/8 — systemd, backup/restore, rollback, restart
reconciliation e recuperação manual — foram executados e agregados pelo
`TASK-P06-010` sobre o baseline operacional
`ed3985b7e9337cbd05a3dec896c29845865fbda2`. A declaração final de prontidão
privada ainda depende do exit gate `TASK-P06-011`. Uso público ou multiusuário
exige uma trilha posterior de autorização, cotas, isolamento, observabilidade e
mitigação de abuso.

## Estado de referência

| Área | Estado atual | Evidência | Risco residual |
|---|---|---|---|
| Fila | Sequencial em memória (`asyncio.Queue`) com payload de restart persistido em `jobs` | `src/yt_transcriber_bot/infrastructure/telegram/job_queue.py`, `src/yt_transcriber_bot/infrastructure/telegram/bot_adapter.py` | A fila em memória continua volátil; a durabilidade vem do recovery orientado por status em `jobs`. |
| Persistência | SQLite com tabela `jobs` compacta | `src/yt_transcriber_bot/infrastructure/persistence/sqlalchemy/models.py` | Não há tabelas atuais `speakers` ou `queue`; renomes ficam serializados em `jobs.speaker_renames_json`. |
| Recuperação após restart | Implementada via recovery orientado por status em `jobs` | `docs/10-recovery-semantics-adr.md`, `StartupRecoveryService`, startup do `TelegramBotAdapter` | Não há resume no meio de ASR/diarização; a garantia atual é requeue seguro de `pending` e reconciliação explícita de estados interrompidos. |
| `/redo` | Reprocessa imediatamente como novo job | `CommandHandler("redo", on_redo)` e manual de uso | Confirmação inline, diff de configuração e reuso seletivo são futuros. |
| Busca, artefatos e entrada Telegram | `/search <texto>`, `/text [n]` e áudio/voz/documento Telegram registrados, user-scoped e cobertos por FTS5 opcional/fallback limitado e snapshots | port de busca, adapter SQLite, exportador `.txt`, handlers Telegram e regressões | Busca semântica e `/translate` continuam futuros; o índice, snapshots e staging de mídia privada permanecem locais. |
| Falha de entrega Telegram | Implementada com use case persistindo renderização como `delivering`, adapter promovendo `delivering` para `completed` após envio ou `delivery_failed` após retries, preservação de paths locais, registro `transcribe_delivery` quando disponível e fallback job-side em `/lasterror` | `JobStatus.DELIVERING`, `JobStatus.DELIVERY_FAILED`, `_mark_job_completed_after_delivery`, `_mark_delivery_failed`, `LastErrorService` | Operador ainda precisa usar `/lasterror` e paths locais para recuperar manualmente artefatos não entregues. |
| Segurança e sanitização | Phase 3 fechada para os caminhos conhecidos de Telegram/logs operacionais | `sanitize_text`, `LastErrorService`, `HealthCheckService`, `ExecutionAuditLogger`, regressões de sanitização em `tests/unit/application/services`, `tests/unit/infrastructure/telegram` e `tests/unit/infrastructure/logging` | Novos caminhos de erro devem continuar usando o sanitizador central; saídas sanitizadas ainda podem conter metadados privados e não devem ser publicadas integralmente. |
| Observabilidade operacional | `/healthcheck`, `/lasterror`, `operational_errors.jsonl` e `execution_audit.jsonl` implementados; documentação/runbook e ensaio systemd real registrados | `HealthCheckService`, `LastErrorService`, `ExecutionAuditLogger`, `docs/03-manual-de-uso.md`, `docs/11-operator-runbook.md`, `specs/006-execution/PLAN-006-READINESS-LEDGER.md` | Logs Python continuam em texto e não há métricas/alertas externos; isso não bloqueia a meta privada atual. |
| Operação e recovery | Runbook orientado a systemd criado e procedimentos críticos ensaiados para backup/restore, upgrade/rollback e recovery de `delivery_failed`/restart | `docs/11-operator-runbook.md`, `deploy/yt-transcriber-bot.service`, `specs/006-execution/PLAN-006-READINESS-LEDGER.md` | O exit gate `TASK-P06-011` ainda precisa confirmar a convergência final do PLAN-006. |

## Fases de maturidade

| Fase | Dono principal | Status | Evidência exigida | Risco/blocker |
|---|---|---|---|---|
| 0 — Baseline, contratos e ledger | Docs + testes de consistência | Concluída | Docs reconciliados; testes de consistência de comandos/claims; baseline amplo revalidado em 2026-07-09 | Reexecutar os gates antes de commit/release se houver novas alterações. |
| 1 — Lifecycle de jobs | Aplicação/Telegram | Concluída com regressões direcionadas | Regressões para `/cancel`, `/cancelall`, pendentes cancelados, falha de entrega, fallback `/lasterror` e retenção | Semântica de entrega é durável no job e prepara o recovery operacional. |
| 2 — Fila durável e restart recovery | Persistência/aplicação | Concluída com regressões direcionadas | ADR de Recovery Semantics; migração aditiva SQLite; testes SQLite temporários simulando restart e idempotência por instância | Ainda não há retomada por checkpoint dentro de etapas caras; isso fica para fase posterior. |
| 3 — Segurança e privacidade | Aplicação/infra | Concluída para o baseline atual | Sanitização central em Telegram/logs; `/healthcheck` omite paths locais sensíveis; `/lasterror` persiste mensagem/contexto/traceback sanitizados; regressões para tokens, cookies, `Authorization`, corpos de API, prompts e transcrições ecoadas por erros; secret scan limpo em baseline recente | Não é autorização para expor logs completos publicamente; novos handlers devem manter o mesmo padrão de sanitização. |
| 4 — Observabilidade e runbooks | Operação/docs | Implementada e empiricamente ensaiada | `/healthcheck`, `/lasterror`, registros systemd/backup/restore/rollback/recovery agregados por `TASK-P06-010` | `LOG_FORMAT=json` e alertas externos ficam como evolução futura; o exit gate `TASK-P06-011` permanece. |
| 5 — CI e quality gates | Tooling | Concluída para o baseline default local/CI | Em 2026-07-09: ruff, format, pytest, mypy, secret scan, gitleaks e `git diff --check` passaram; CI agora inclui `uv run mypy src` | Checks ML/network/e2e seguem environment-gated; manter o baseline limpo em alterações futuras. |
| 6 — Maintainability/refactor | Arquitetura/executor | Concluída com testes de caracterização | Colaboração de histórico extraída sem alterar autorização, ordenação, índices ou comandos existentes | Mudanças futuras devem preservar os testes de equivalência. |
| 7 — Search MVP | Produto/aplicação | Concluída com regressões direcionadas | FTS5 opcional, fallback limitado, isolamento por usuário, snippets sanitizados, backfill/refresh | Busca semântica permanece deliberadamente fora de escopo. |
| 8 — Deployment systemd | Operação/docs | Ensaiada no host privado; evidência agregada | Smoke systemd, backup/restore, rollback e recovery em host/staging real estão referenciados no ledger P06-010 | Docker Compose permanece opcional/futuro; o exit gate P06-011 ainda é necessário. |
| 9 — Funcionalidades estendidas | Produto | Em execução incremental | `/text [n]` e entrada de áudio/voz/documento Telegram concluídos com TDD; ASR multilíngue, `/translate`, `/redo` avançado permanecem no roadmap | Não misturar com hardening de produção. |

## Checklist de contrato atual vs planejado

- [x] Documentar que a fila atual é em memória.
- [x] Documentar que a fila continua em memória, mas restart recovery mínimo
      agora é implementado via `jobs`.
- [x] Documentar que o schema atual tem apenas `jobs` como tabela ORM de
      primeira classe; `speakers` e `queue` são planejados.
- [x] Documentar que `/redo <link>` executa imediatamente como novo job.
- [x] Implementar e documentar `/search <texto>` com FTS5 opcional, fallback
      compatível limitado, isolamento por usuário e sanitização.
- [x] Entregar `/text [n]` e entrada de áudio/voz/documento Telegram com identidade de origem privada; `/translate` permanece futuro.
- [x] Documentar que falha de entrega Telegram usa `delivery_failed` e
      `/lasterror` após exaustão de retry.
- [x] Implementar Phase 1 antes de declarar o ciclo de vida de jobs pronto para
      produção privada.
- [x] Implementar Phase 2 antes de avançar para ensaios de produção
      privada/single-operator.
- [x] Concluir Phase 3 com sanitização central e regressões para os caminhos de
      erro/log conhecidos.
- [x] Corrigir baseline `mypy` e promovê-lo para gate de CI.
- [x] Criar runbook orientado a systemd para start/stop/restart, backup/restore,
      upgrade/rollback, recovery, modelos/cache, `/healthcheck`, `/lasterror` e
      limpeza emergencial.
- [ ] Declarar produção privada/single-operator completa somente depois dos
      ensaios Phase 4/8. O baseline default da Phase 5 está limpo em
      2026-07-09, mas deve ser reexecutado antes de commit/release se houver
      novas alterações.
- [x] Executar e registrar ensaio real de backup/restore em host ou ambiente de
      staging.
- [x] Executar e registrar smoke real de systemd start/stop/restart/rollback.
- [x] Executar e registrar ensaio de recovery de `delivery_failed` e job
      interrompido seguindo o runbook.

## Critério de evidência Phase 4/8

Os ensaios Phase 4/8 só contam como concluídos quando houver registro
reproduzível de execução em host ou staging real. Um template gerado por helper
de evidência, se existir no repositório, pode iniciar o registro, mas não
substitui a execução nem os trechos de saída coletados pelo operador.

Cada registro deve conter, no mínimo:

- data UTC, host/ambiente, operador, commit Git, versão do lockfile e caminho do
  arquivo de evidência;
- comandos executados ou ações Telegram realizadas, com ordem suficiente para
  reprodução;
- trechos sanitizados de `systemctl`, `journalctl`, `/healthcheck`, `/status`,
  `/list`, `/lasterror`, `operational_errors.jsonl` ou
  `execution_audit.jsonl`, conforme o ensaio;
- resultado esperado, resultado observado e decisão explícita: passou, falhou ou
  passou com ressalvas;
- links/caminhos locais para backups, artefatos restaurados ou arquivos
  recuperados, sem publicar segredos, cookies, transcrições privadas ou tokens.

Critério específico por ensaio:

| Ensaio | Evidência mínima para contar como concluído |
|---|---|
| Backup/restore | Backup criado a partir do host real; restore feito em instalação parada ou staging isolado; `jobs.db` abre depois do restore; `/healthcheck`, `/status` e `/list` executados depois do start; operador registrou se jobs `pending`/interrompidos foram reconciliados conforme o runbook. |
| systemd start/stop/restart/rollback | `systemctl start`, `status`, `stop`, `restart` e rollback exercitados no serviço real; `journalctl` coletado em cada transição; `/healthcheck` e `/status` confirmam bot responsivo após start/restart/rollback; commit anterior ou backup usado no rollback fica registrado. |
| `delivery_failed` e recuperação manual | Job real ou staging controlado chega a `delivery_failed`; `/lasterror` mostra contexto sanitizado e paths locais; operador confirma existência dos artefatos e documenta o método de recuperação manual; ausência de reenvio automático pelo bot fica registrada. |
| Job interrompido e restart recovery | Processo/serviço interrompido durante estado ativo controlado; após restart, `/status`, `/list`, `/lasterror` e auditoria mostram requeue de `pending` ou reconciliação para `failed`/`delivery_failed`; operador registra o caminho usado para reprocessar ou recuperar manualmente. |

## Baseline de validação

O quadro abaixo preserva o baseline amplo histórico de **2026-07-09**. A
validação operacional/qualidade mais recente do PLAN-006 ocorreu em **2026-08-18**
sobre o baseline `ed3985b7e9337cbd05a3dec896c29845865fbda2`; o ledger P06-010
distingue explicitamente testes locais de rehearsals empíricos:

| Check | Status atual | Observação |
|---|---|---|
| `uv run ruff check .` | Passou em 2026-07-09 | Lint amplo sem achados. |
| `uv run ruff format --check .` | Passou em 2026-07-09 | Formatação ampla conforme ruff. |
| `uv run pytest` | Passou em 2026-07-09 | 622 testes passaram; 38 marcados `integration`, `slow` ou `e2e` ficaram desselecionados pelo baseline local. |
| `uv run mypy src` | Passou em 2026-07-09 | `Success: no issues found in 91 source files`; não é mais blocker da Phase 5. |
| `python3 scripts/security/scan_secrets.py --all` | Passou em 2026-07-09 | Nenhum segredo óbvio detectado na varredura completa. |
| `python3 scripts/security/gitleaks_if_available.py --all` | Passou em 2026-07-09 | `gitleaks` disponível; nenhum vazamento encontrado. |
| `git diff --check` | Passou em 2026-07-09 | Sem whitespace errors no diff validado. |
| CI workflow | Atualizado em 2026-07-09 | O workflow agora inclui `uv run mypy src` junto dos demais gates default. |
| Regressões Phase 3 | Passaram em 2026-07-09 | Cobrem sanitização de tokens/cookies/headers, corpos de API, prompts, transcrições ecoadas, `/healthcheck`, `/lasterror`, auditoria JSONL e mensagens Telegram. |
| Revisão documental Phase 4 (`README.md`, `docs/03`, `docs/04`, `docs/08`, `docs/09`, `docs/11`) | Atualizada em 2026-07-09 | Docs/runbook: operação systemd, backup/restore, upgrade/rollback, healthcheck/lasterror, recovery e limitações residuais. Não substitui ensaios reais. |

## O que ainda falta para declarar produção privada completa

- Executar o `TASK-P06-011` como exit gate do PLAN-006, incluindo a revisão final
  de conformance/quality gates e a confirmação de que nenhuma obrigação ou
  evidência ficou silenciosamente omitida.
- Se o exit gate encontrar falha material, reabrir o task proprietário; P06-010
  e P06-011 não devem corrigir produto por contorno.

## Evoluções operacionais futuras não bloqueantes

- Decidir se logs Python também precisam de `LOG_FORMAT=json`; hoje os logs
  estruturados existentes são `operational_errors.jsonl` e
  `execution_audit.jsonl`.
- Adicionar métricas, alertas externos e operação multiusuário apenas em uma
  trilha posterior; não são requisitos para a meta privada/single-operator.
