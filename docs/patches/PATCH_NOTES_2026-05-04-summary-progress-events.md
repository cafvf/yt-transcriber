# Patch notes — 2026-05-04 — Progresso observável no `/summary`

## Contexto

Após a introdução de chunking por tokenizer e deduplicação, a geração de resumo podia ficar vários minutos sem feedback no Telegram. O arquivo final era enviado corretamente, mas o usuário não via progresso durante as chamadas longas à LLM.

Também houve confusão possível ao interpretar logs do LM Studio: linhas como `created context checkpoint 1 of 32` são checkpoints internos de contexto/cache do servidor, não necessariamente os chunks de sumarização do bot.

## Alterações

- Adicionado `SummaryProgress`, evento estruturado de progresso da sumarização.
- `TranscriptSummaryService.summarize(...)` agora aceita `on_progress` opcional.
- O serviço emite eventos para:
  - planejamento dos chunks;
  - início de passagem única;
  - conclusão de passagem única;
  - início de cada chunk;
  - conclusão de cada chunk;
  - início da síntese final;
  - conclusão da síntese final.
- O adapter do Telegram passa um callback para o serviço de resumo e edita a mensagem inicial do `/summary` com o andamento.
- O progresso é emitido antes de cada chamada longa à LLM, evitando silêncio durante o primeiro chunk.

## Testes

- Adicionado teste unitário para verificar emissão de eventos de progresso no modo map-reduce.
- Atualizado teste do adapter Telegram para verificar que o callback `on_progress` é passado e que há edições de mensagem durante o `/summary`.

## Observação

O bot ainda não recebe progresso token-a-token do LM Studio. O progresso exibido é por etapas/chunks da aplicação. Para progresso dentro de uma única chamada à LLM, seria necessário migrar a chamada para streaming ou consultar uma API específica do servidor, se disponível e estável.
