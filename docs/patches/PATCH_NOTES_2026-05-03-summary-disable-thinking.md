# Patch — desabilitar thinking/reasoning em sumarização

## Objetivo

Evitar que modelos Qwen/Qwen3.5 gastem contexto e tempo gerando blocos de raciocínio explícito durante `/summary [n]`.

## Mudanças

- Adicionada configuração `SUMMARY_DISABLE_THINKING=true`.
- O cliente OpenAI-compatible envia `enable_thinking=false` quando a configuração está ativa.
- O prompt de sumarização pede resposta direta, sem cadeia de raciocínio e sem blocos `<think>`.
- Blocos `<think>...</think>` retornados pelo servidor são removidos antes de salvar o Markdown.
- Adicionado script `scripts/config/print_effective_settings.py` para verificar as configurações efetivas carregadas pelo bot.
- Documentação de uso/instalação atualizada.

## Validação sugerida

```bash
uv run pytest
uv run pre-commit run --all-files
uv run python scripts/config/print_effective_settings.py
```
