# Gate 0 — Bootstrap do projeto — REPORT

## Escopo realizado
- `pyproject.toml` com metadata, deps de runtime, deps de dev (grupo `dev`), extras `ml` e configurações de ruff/mypy/pytest/coverage.
- `uv.lock` gerado e commitável.
- Estrutura mínima `src/yt_transcriber_bot/` com `__init__.py` (versão) e `__main__.py` (CLI mínima).
- Estrutura mínima `tests/unit/` com 3 testes (importação, função main, subprocess).
- `.gitignore` cobrindo Python, ambientes, cobertura, dados runtime e IDEs.
- Template `deploy/yt-transcriber-bot.service`.
- Diretório `docs/gate-reports/` para reports.

## Métricas
- Testes adicionados: 3 unit
- Cobertura `src/yt_transcriber_bot/`: 100% (apenas `__init__.py` em escopo; `__main__.py` excluído via `omit`)
- Tempo da suíte: 0,05s
- ruff check: 0 ofensas
- ruff format: 6 arquivos limpos
- mypy --strict: 0 erros

## Bugs encontrados durante o gate
1. **Versões pinadas no contrato (`pyannote-audio>=3.1,<4.0`) eram incompatíveis com o WhisperX 3.8.4+** que exige `pyannote-audio>=4.0`. Corrigido para `pyannote.audio>=4.0,<5.0`. Não gerou teste de regressão por ser configuração de dependências (não código).

## Riscos e dívidas conhecidas
- A stack ML (`extras=ml`) ainda não foi instalada; será habilitada nos Gates 2-3.
- O `__main__.py` será reescrito completamente no Gate 5 (bootstrap real do bot).

## Próximo gate
Gate 1 — Domain model + Config + Repository SQLite (TDD purista).
