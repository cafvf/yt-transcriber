# Patch notes — summary reasoning_effort=none

Data: 2026-05-04

## Objetivo

Reforçar a desativação de thinking/reasoning nas chamadas de sumarização via API OpenAI-compatible do LM Studio.

## Alterações

- Quando `SUMMARY_DISABLE_THINKING=true`, o payload de `/v1/chat/completions` passa a incluir também:

```json
{
  "reasoning_effort": "none"
}
```

- O payload mantém as proteções já existentes:
  - `enable_thinking=false`;
  - `chat_template_kwargs={"enable_thinking": false}`;
  - prefixo textual `/no_think`;
  - remoção de blocos `<think>...</think>`;
  - rejeição de respostas que tragam apenas `reasoning_content` com `content` vazio.

## Testes

- Atualizado o teste do cliente OpenAI-compatible para garantir que `reasoning_effort="none"` é enviado quando thinking está desabilitado.
- Atualizado o teste de thinking habilitado para garantir que `reasoning_effort` não é enviado quando `disable_thinking=False`.

## Observação

`reasoning_effort` pode ser ignorado por servidores OpenAI-compatible que não implementem esse campo. Por isso, as proteções textuais e o bloqueio de `reasoning_content` continuam ativos.
