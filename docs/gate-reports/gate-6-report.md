# Gate 6 — Retenção FIFO + /rename interativo + comandos auxiliares

**Data**: 2026-05-01
**Status**: ✅ FECHADO

## Entregáveis

### Application services
- `application/services/retention_policy.py` — `RetentionPolicy` que mantém os últimos N jobs concluídos, expurga em conjunto downloads/processed/logs, e **preserva o MD como legado** (Dúvida 28).
- `application/services/rename_speakers.py` — `RenameSpeakersService` que carrega o snapshot persistido, aplica aliases, re-renderiza o MD e o reescreve no mesmo path. Funciona em vídeos legados.
- `application/services/config_signature.py` — `compute_config_signature()`, `describe_config()`, `diff_configs()` para detecção de mudança de configuração (Dúvida 23).

### Infrastructure
- `infrastructure/persistence/filesystem/transcript_snapshot.py` — `TranscriptSnapshotRepository` que persiste segments + metadata + render_context em JSON versionado (`schema_version=1`). Permite rerender após expurgo do `.ogg`.

### Telegram BotAdapter (extensão)
- Novos handlers: `/list`, `/last`, `/rename` (com diálogo de mapeamento textual), `/clearcache`.
- Diálogo de rename com timeout implícito (próxima mensagem qualquer); `/cancel` aborta.
- Mapeamento aceito: `SPEAKER_00=João, SPEAKER_01=Maria` (vírgula ou nova linha).
- `speaker_renames` persistido no Job para auditoria.
- `_parse_rename_mapping()` testado com 9 casos parametrizados.

## Testes (43 novos, 417 unit no total)

| Suíte | Testes |
|---|---|
| `test_retention_policy.py` | 6 |
| `test_rename_speakers.py` | 7 |
| `test_config_signature.py` | 7 |
| `test_transcript_snapshot.py` | 4 |
| `test_bot_adapter_commands.py` | 19 |

### Bug encontrado e regressão criada

Nenhum bug crítico encontrado; uma corrupção de edição em `_decode` foi identificada no merge e corrigida com isinstance() runtime checks que tornaram o código tipo-seguro sem `# type: ignore` espalhados.

## Critérios de aceitação

- [x] 417 testes unit verdes (449 com integration habilitado)
- [x] `ruff check` zerado
- [x] `ruff format --check` zerado
- [x] `mypy --strict` zerado em 69 arquivos
- [x] Política FIFO preserva MDs como legado
- [x] /rename funciona em vídeos legados (snapshot persistido independente do .ogg)
- [x] Comandos /list, /last, /clearcache implementados e testados

## Próximo gate

Gate 7 — E2E real no sandbox com `j2p8p7cg0q8` (ou clipe equivalente em PT) e documentação final de uso/instalação.
