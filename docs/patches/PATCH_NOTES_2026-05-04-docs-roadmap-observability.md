# Patch notes — 2026-05-04 — Documentação e roadmap pós-summary

## Objetivo

Atualizar README e documentação para refletir o estado real do projeto após estabilização da feature `/summary` via LM Studio, e registrar a próxima direção de desenvolvimento.

## Alterações documentais

- README reescrito para refletir o estado atual do bot:
  - exportação JSON/SRT/VTT;
  - MP4 com legenda selecionável;
  - renomeação/mesclagem de falantes por botões inline;
  - sumarização via LM Studio/OpenAI-compatible;
  - chunking por tokenizer/estimativa;
  - deduplicação;
  - progresso no Telegram;
  - timeout adaptativo;
  - segurança e pre-commit.
- README passou a explicitar o paradigma de **Spec-Driven Development (SDD)** com desenvolvimento assistido por IA.
- Manual de uso atualizado para incluir `/summary [n]`, configuração atual de sumarização e próximos comandos planejados.
- Contrato funcional ajustado para tratar resumos e exportações como artefatos derivados, sem substituir a transcrição literal.
- ADR-008 atualizado: Markdown permanece fonte literal; resumos/exports são derivados auditáveis.
- Roadmap futuro revisado:
  - próxima prioridade: `/healthcheck` e `/lasterror`;
  - busca full-text `/search <texto>` priorizada após observabilidade;
  - entrada por arquivo de áudio enviado ao Telegram registrada como futura funcionalidade;
  - perfis múltiplos de resumo removidos da prioridade por decisão de produto;
  - tradução, Obsidian/Notion, backend Transformers e melhorias de áudio mantidos como candidatos futuros.

## Decisão de produto

A próxima implementação recomendada é o gate de observabilidade operacional:

- `/healthcheck` para diagnosticar configuração, dependências, Telegram, SQLite e LM Studio;
- `/lasterror` para recuperar o último erro sanitizado sem vazar tokens/cookies.

## Testes

Este patch é apenas documental. Não altera código de produção nem suíte de testes.
