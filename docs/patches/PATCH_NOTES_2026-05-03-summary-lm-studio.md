# Patch — Summary via LM Studio / OpenAI-compatible API

## Mudanças

- Adicionado comando `/summary [n]`.
- Adicionado serviço `TranscriptSummaryService` para gerar resumo Markdown a partir de snapshots.
- Adicionado cliente mínimo `OpenAICompatibleChatClient` para `POST /v1/chat/completions`.
- Adicionadas configurações `SUMMARY_*` no `AppSettings` e `.env.example`.
- Atualizado `/help` com o comando `/summary [n]`.
- Atualizado entrypoint real com `CommandHandler("summary", on_summary)`.
- Adicionados testes para cliente OpenAI-compatible, sumarização, comando Telegram e registro no entrypoint.

## Uso esperado

```text
/summary
/summary 2
```

## Configuração típica

```env
SUMMARY_BACKEND=openai_compatible
SUMMARY_BASE_URL=http://localhost:1234/v1
SUMMARY_MODEL=qwen3.5-9b
SUMMARY_TEMPERATURE=0.2
SUMMARY_MAX_TOKENS=2048
SUMMARY_MAX_CHARS_PER_CHUNK=12000
SUMMARY_OUTPUT_LANGUAGE=auto
```
