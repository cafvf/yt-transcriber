# Deprecações e compatibilidade

Superfícies relevantes ao operador. Compatibilidades internas adicionais permanecem em `specs/007-production-coherence/COMPATIBILITY.md`.

## Política

Uma superfície depreciada deixa de ser ensinada em documentação/templates novos, pode continuar aceita pelo código por compatibilidade, deve ter migração explícita e não é removida silenciosamente na mesma alteração que primeiro documenta a depreciação. Remoção exige atualização de testes/compatibilidade e documentação de release. Não há data implícita de remoção.

## `MAX_VIDEO_DURATION_MIN`

**Status:** alias legado aceito. **Canônico:** `MAX_MEDIA_DURATION_MIN`.

Configuração nova usa `MAX_MEDIA_DURATION_MIN`; o loader atual continua aceitando o nome antigo para compatibilidade.

## `uv sync --extra ml`

**Status:** compatibilidade de instrução antiga. A stack ML é dependência principal. `pyproject.toml` mantém `ml = []` vazio, mas documentação atual não recomenda o extra. Produção não depende de `uv` em runtime.

## Compatibilidades internas

Estados persistidos legados, aliases de tipos e colunas físicas de compatibilidade podem permanecer para leitura/migração sem serem APIs de operador. A fonte normativa é `specs/007-production-coherence/COMPATIBILITY.md`.
