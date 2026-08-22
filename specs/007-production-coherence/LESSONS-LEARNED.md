# PLAN-007 — Lições aprendidas e filtros obrigatórios

Status: ativo durante a execução do PLAN-007.

Este registro consolida falhas observadas nas rodadas de implementação do
Gate A e falhas encontradas na revisão pré-entrega. Cada item deve funcionar
como filtro obrigatório para os próximos pacotes e gates.

## 1. Execução e empacotamento

### LL-001 — Não usar `set -e` no shell interativo externo
**Problema observado:** blocos anteriores podiam encerrar o terminal do VS Code
quando `set -e`/`exit` eram executados no shell interativo.

**Filtro:** toda sequência entregue ao operador deve executar dentro de
subshell `( ... )`. Falha pode encerrar o subshell, nunca o terminal.

### LL-002 — Validadores críticos não podem depender de ferramenta opcional
**Problema observado:** a ausência de `rg` fez uma validação cair no ramo de
sucesso e imprimir um falso `OK`.

**Filtro:** usar Python/stdlib para validação crítica ou testar explicitamente
a disponibilidade da ferramenta antes de usá-la.

### LL-003 — Toda alegação de qualidade do ZIP precisa ser realmente executada
**Problemas observados:** pacote de especificação com trailing whitespace e
pacote A1 entregue sem `ruff format --check`.

**Filtro pré-entrega:** compilação/AST, trailing whitespace, `ruff check` e
`ruff format --check` sobre Python gerado, integridade do ZIP e manifesto
SHA-256.

### LL-004 — Aplicadores devem ser transacionais antes da primeira escrita
**Problema observado:** migrações incompletas obrigaram várias retomadas.

**Filtro:** preparar transformações em memória, validar sintaxe/semântica e
somente então escrever. Quando a etapa necessariamente escreve antes de outra
validação, a retomada deve ser idempotente e reconhecer o estado parcial.

### LL-005 — Estado Git machine-readable deve preservar bytes significativos
**Problema observado:** `.strip()` sobre `git status --porcelain` removeu o
espaço inicial da primeira linha e transformou `src/...` em `rc/...`.

**Filtro:** nunca aplicar `.strip()` ao conteúdo bruto de porcelain; parser
centralizado e teste de regressão para ` M`, ` D` e `??`.

### LL-006 — Manifesto e escopo precisam ser recalculados após autofix
**Problema observado:** Ruff/pre-commit podem modificar arquivos após a
aplicação.

**Filtro:** gerar/atualizar manifesto do working tree e conferir novamente o
escopo depois de formatter/hooks, antes do staging.

## 2. Taxonomia e migração de contratos

### LL-007 — Teste de proibição não pode se autoidentificar como violação
**Problema observado:** A1 v1 continha literalmente nomes proibidos no próprio
teste de conformance e o scanner bloqueou o pacote.

**Filtro:** scanners de taxonomia devem distinguir dados de teste de uso
executável; quando busca textual for inevitável, construir sentinelas por
fragmentos.

### LL-008 — Busca textual bruta não prova existência de consumidor
**Problema observado:** v5 classificou menções em strings/docstrings como
consumidores de API removida.

**Filtro:** auditoria de consumidor deve usar AST/semântica: imports, `Name`,
`Attribute`, keyword, chamada e acesso dinâmico conhecido.

### LL-009 — Scripts, ferramentas e E2E são consumidores de contrato
**Problemas encontrados:** `scripts/e2e_validate.py` e benchmark ainda usavam
nomes/assinaturas antigos, inclusive `VideoMetadata`, seleção de áudio,
fingerprint e contratos de cancelamento/diarização.

**Filtro:** toda migração de API varre `src/`, `tests/` e `scripts/`.

### LL-010 — Compatibilidade só permanece quando comprovada e isolada
**Problema tratado:** `config_signature` e `artifact_policy` ainda existem como
representação física SQL, mas não devem vazar para application/domain.

**Filtro:** teste de round-trip real em SQLite e auditoria de fronteira; nomes
físicos legados ficam restritos à persistência.

### LL-011 — Remoção de campo exige auditoria de comportamento, não só de nome
**Problema observado:** `startup_recovery.py` ainda consultava
`artifact_policy`, embora o campo fosse um default constante sem decisão real.

**Filtro:** antes de remover campo, classificar cada uso como comportamento,
persistência, compatibilidade ou redundância. Não inventar enum para campo sem
variantes comportamentais.

## 3. Tipagem de domínio e fronteiras

### LL-012 — Migração de primitivo para VO/enum exige varredura de TODOS os construtores
**Problema atual:** `ProcessingProvenance.language_source` tornou-se
`LanguageSource`, mas fixture de snapshot continuou criando
`ProcessingProvenance(language_source="asr")`, causando
`AttributeError: 'str' object has no attribute 'value'`.

**Filtro:** AST global para literais primitivos passados a campos tipados em
`src/`, `tests/` e `scripts/`, incluindo fixtures e objetos auxiliares.

### LL-013 — Domínio não deve mascarar erro de fronteira normalizando string
**Problema encontrado:** `Job.__post_init__` aceitava/normalizava
`requested_language` cru, escondendo consumidores incorretos.

**Filtro:** domínio canônico rejeita tipo errado; parsing/normalização ocorre
na borda de transporte/configuração.

### LL-014 — Fronteira tipada → transporte deve serializar explicitamente
**Problema encontrado:** recovery Telegram passava `Language` diretamente para
`JobPayload`, cujo contrato é string.

**Filtro:** entrada de transporte faz `str -> VO`; saída para transporte faz
`VO -> .code/.value`. Nenhuma passagem implícita.

### LL-015 — Fingerprint tipado não aceita strings de conveniência
**Problema encontrado:** testes ainda passavam strings para
`requested_language` e `source_type`.

**Filtro:** chamadas de `compute_processing_fingerprint` usam `Language` e
`MediaSourceType`; auditoria AST bloqueia literais string nesses keywords.

### LL-016 — Tipagem precisa incluir proveniência e metadados auxiliares
**Problema atual:** o filtro anterior cobria `Job`, pipeline e fingerprint, mas
não `ProcessingProvenance`.

**Filtro:** checklist de tipos canônicos inclui pelo menos `Language`,
`LanguageSource`, `AudioTrackSelection`, `MediaSourceType`, metadados e
proveniência. Novos VOs devem ser adicionados ao filtro.

## 4. Ruff, testes e regressões

### LL-017 — Ruff/format deve rodar antes da entrega, inclusive em testes gerados
**Problemas observados:** A2 encontrou 17 `I001`; v6 encontrou 23 findings,
corrigiu 20 e deixou `SIM102` + dois `RUF043`.

**Filtro:** `ruff check --fix` pode ser usado durante preparação, mas a entrega
só ocorre após `ruff check` e `ruff format --check` sem pendências.

### LL-018 — Regex de `pytest.raises(match=...)` deve ser semanticamente explícita
**Problema observado:** Ruff `RUF043` em padrões com `(?i)`.

**Filtro:** regex com metacaracteres usa raw string ou `re.escape`.

### LL-019 — Bugs encontrados durante gate viram regressões permanentes
**Problema histórico:** regressão de seleção de runtime/VRAM e demais bugs de
gate.

**Filtro:** toda falha funcional confirmada deve gerar teste que falha antes da
correção e passa depois.

## 5. Modos de falha operacionais

### LL-020 — Caminhos de erro vêm antes do happy path na validação do gate
**Filtro obrigatório antes do commit:**
- YouTube: indisponível, membros, idade, sem áudio e seleção original segura;
- conversão;
- duração e idioma fora da política;
- cancelamento;
- ASR/`OutOfMemoryError`;
- diarização indisponível/falha;
- ausência de evidência canônica;
- restart/recovery;
- persistência SQLite e snapshots legados;
- sanitização/observabilidade.

### LL-021 — Falha não pode ser transformada em sucesso parcial
**Filtro:** nenhum caminho chega a `DELIVERING/COMPLETED` sem Markdown e
referência canônica persistidos; cancelamento, rejeição e exceção técnica
continuam distintos.

### LL-022 — Erros persistidos/exibidos devem permanecer sanitizados
**Filtro:** testes de sanitização e `/lasterror` são obrigatórios sempre que
pipeline, adapters, logging ou persistência de erro forem tocados.

## 6. Processo do PLAN-007

### LL-023 — Implementar por Gate, não fazer uma mini-release por task
**Problema de processo:** ciclos A1/A2 por task criaram overhead e repetição de
validações.

**Filtro:** tasks são incrementos internos; a unidade de entrega/aceitação é o
Gate, salvo bloqueio estrutural real.

### LL-024 — Falha parcial deve continuar do estado real, não reiniciar por padrão
**Problemas observados:** A3 e demais migrações deixaram estados parciais úteis.

**Filtro:** diagnosticar primeiro; não `reset`/reaplicar quando o estado pode ser
reconhecido e retomado com segurança.

### LL-025 — O gerador do pacote também precisa de validação incremental
**Problema encontrado:** uma tentativa de gerar o v8 falhou por delimitadores
de string aninhados no próprio tooling de montagem.

**Filtro:** construir conteúdo, aplicador e ZIP em etapas; compilar/parsear o
aplicador antes de empacotar e nunca tratar falha do gerador como alteração do
repositório.


### LL-026 — Testes de conformance também são consumidores da arquitetura
**Problema observado:** após a migração canônica para
`processing_fingerprint.py`, `test_configuration_taxonomy.py` ainda exigia
literalmente `application/services/config_signature.py` como owner de
`SIGNIFICANT_FIELDS`.

**Filtro:** toda mudança arquitetural deve migrar também asserts, comparações,
paths e inventários executáveis de `tests/conformance`. Conformance vigente não
pode exigir API/path removido apenas porque a expectativa era antiga. Evidência
histórica deve ficar em documentação/fixtures históricas, não em assert do HEAD.

### LL-027 — Manifesto SHA deve ser validado após reabrir o ZIP
**Problema encontrado antes da entrega:** uma tentativa de gerar o v9 escreveu
`\n` literal dentro de `SHA256SUMS.txt`; o ZIP existia, mas o parser do
manifesto tratava múltiplos registros como uma única linha.

**Filtro:** após empacotar, extrair o ZIP em diretório novo, reabrir o manifesto,
validar a quantidade de registros e verificar cada hash contra o arquivo
extraído. Nunca confiar apenas no manifesto ainda em memória.


### LL-028 — Helpers de auditoria devem aceitar fixtures fora do repositório
**Problema observado:** o teste negativo do guard de conformance criou um
arquivo em `tmp_path`, mas `_violations()` executou
`path.relative_to(REPO_ROOT)` incondicionalmente e lançou `ValueError` antes
de avaliar a semântica da fixture.

**Filtro:** helpers reutilizados por testes com arquivos sintéticos devem
separar lógica de análise de lógica de apresentação de paths. Se o path não
estiver sob o repositório, usar o path absoluto (ou outro label seguro) em vez
de assumir `relative_to(REPO_ROOT)`. O próprio teste de fixture externa deve
ser executado na pré-entrega do pacote.

## Checklist pré-entrega derivado

1. Classificar dependências e impacto dos arquivos alterados.
2. Cruzar alterações com todos os modos de falha operacionais afetados.
3. Auditar `src/`, `tests/` e `scripts/`.
4. Auditar consumidores por AST, não substring.
5. Auditar literais primitivos em contratos migrados para VO/enum.
6. Auditar serialização explícita nas fronteiras.
7. Provar compatibilidade persistida com round-trip real quando aplicável.
8. Rodar compile/AST, Ruff lint e format no material gerado.
9. Rodar negative/error-path tests relevantes.
10. Rodar conformance, mypy e suíte completa.
11. Rodar pre-commit, secret scan e Gitleaks.
12. Revalidar escopo Git e `diff --check`.
13. Só então permitir staging/commit.

### LL-029 — `**kwargs` is an indirect API consumer

A mapping expanded into a canonical call is part of that API contract. Migrate the mapping producer and enumerate every expansion consumer rather than checking only explicit keyword calls.

### LL-030 — Preconditions validate invariants, not diagnostic cardinality

Migration preflight must prove the invariants needed for a safe edit. It must not assume that a known number of findings is the complete set of repository defects.

### LL-031 — Architectural filters also apply to migration tooling

Auditors and migration helpers must obey the same semantic distinction between real API consumption and declarative vocabulary that they impose on repository code.

### LL-032 — A named test is not evidence when markers deselect it

Validation must override default marker selection when an integration test is mandatory and must prove that the target test actually executed and passed.

### LL-033 — Diagnostics accumulate independent failures before returning

A failure in one independent quality check must not suppress other safe checks. Dependent checks may be reported as SKIPPED with a reason; the runner returns non-zero only after the final aggregate report.

### LL-034 — Auditors must not classify declarative rule vocabulary as API use

Forbidden/canonical strings used to define rules, negative fixtures, documentation, or absence assertions are not consumers by themselves. Classification requires AST/semantic context.

### LL-035 — Diagnostic snapshots preserve Git visibility semantics

A cloned snapshot can lose local `.git/info/exclude` rules. Build validation snapshots from the original checkout's tracked plus non-ignored untracked file set so ignored runtime state cannot become test or secret-scan input.

### LL-036 — A quality-tool invocation must prove it analyzed a target

A CLI usage error such as running `mypy` without files is a validator defect, not evidence of a code defect. Validation records are valid only when the intended target was actually analyzed.

### LL-037 — Semantic migrations target consumers, not lexical cardinality

A migration must identify the AST consumer whose contract changes and transform that semantic node. Unrelated lexical occurrences may be intentional compatibility evidence and must not be counted or rewritten as API consumers.

## LL-038 — Gate validators must not widen static-analysis scope implicitly

A validator may not turn unrelated historical test/tooling debt into a Gate A blocker by inventing a broader mypy target than the gate or an established clean baseline requires. Blocking scope must be explicit and documented; broader debt may still be inventoried separately.

## LL-039 — Migration exclusions must mirror audit semantics

When the auditor intentionally excludes negative or compatibility evidence from consumer findings, migration tooling must preserve that semantic distinction. A transformer must not rewrite an excluded fixture merely because its syntax resembles a real consumer.

## LL-040 — Installed quality tooling is part of the quality surface

A permanent auditor or validator installed into the repository must itself satisfy the repository's lint, format, compile, and relevant type checks. Tooling that audits quality cannot be exempt from those same checks.

## LL-041 — Gate correctness and repository-wide debt inventory are distinct evidence

A gate may block on its documented production/tooling type scope while separately collecting non-gating repository-wide test/script mypy debt. The report must label that distinction explicitly rather than presenting debt as either silently waived or falsely gate-clean.

<!-- PLAN-007:GATE-A:LESSONS-042-044 -->
## LL-042 — Deletions are first-class staged-scope entries

A staging/commit automation must validate deletions explicitly. Staging only paths that still exist can leave validated deletions outside the index even when every content check is green. Staged-scope tests must include additions, modifications, and deletions.

## LL-043 — Physical path audits must disable Git rename detection

When a quality gate reasons about the exact physical path set, Git rename detection can collapse a deletion/addition pair into one logical rename entry and change cardinality. Physical scope verification must use `--no-renames` (or equivalent explicit path accounting) rather than treating rename-aware display output as a path ledger.

## LL-044 — Gate closure requires reproduction on committed bytes

A gate that passes only before commit is not yet fully evidenced. After the intended commit is created, rerun an independent validation on the committed tree and confirm a clean working tree. This distinguishes validated content from assumptions about staging/commit behavior.
