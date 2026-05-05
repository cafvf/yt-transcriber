# Patch Notes — Roadmap reprioritization

Data: 2026-05-04

## Objetivo

Atualizar a documentação para refletir a nova priorização funcional após a estabilização de `/healthcheck` e `/lasterror`.

## Mudanças

- `/search <texto>` permanece como próxima prioridade e passa a incluir explicitamente preparação arquitetural para busca semântica futura.
- `/text [n]` foi promovido para prioridade alta logo após busca.
- Upload de áudio pelo Telegram permanece como prioridade relevante.
- Backend alternativo de ASR e suporte multilíngue foram antecipados para antes de tradução e Obsidian.
- `/translate` passa a depender conceitualmente de melhor suporte multilíngue.
- Obsidian/Notion foi movido para etapa posterior.
- `/stats` e recuperação avançada após interrupção foram removidos da prioridade principal atual e mantidos apenas como ideias de baixa prioridade/arquivadas.

## Arquivos impactados

- `README.md`
- `docs/01-contrato-funcional.md`
- `docs/03-manual-de-uso.md`
- `docs/05-plano-de-execucao.md`
- `docs/06-funcionalidades-futuras.md`
- `docs/07-glossario-e-decisoes.md`
