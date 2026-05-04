# Patch — summary model guard

Este patch reforça a integração de sumarização com LM Studio/OpenAI-compatible:

- valida `SUMMARY_MODEL` contra `GET /v1/models` antes da primeira chamada de resumo;
- falha com diagnóstico se o modelo configurado não estiver na lista de modelos disponíveis;
- falha se a resposta declarar um modelo diferente do configurado quando `SUMMARY_STRICT_MODEL_MATCH=true`;
- adiciona `SUMMARY_VALIDATE_MODEL` e `SUMMARY_STRICT_MODEL_MATCH` ao `.env.example`;
- prefixa prompts de sumarização com `/no_think` quando `SUMMARY_DISABLE_THINKING=true`;
- mantém a regra de não usar `reasoning_content` como resumo final.

Motivação: evitar que o LM Studio use um modelo diferente do selecionado no `.env` e evitar artefatos derivados de `reasoning_content`, que em modelos Qwen pode conter apenas o prompt ou planejamento interno, não um resumo final.
