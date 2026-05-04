# Patch Notes — 2026-05-04 — Summary tokenizer chunking and transcript deduplication

## Contexto

A feature `/summary` estava funcionando com `SUMMARY_DISABLE_THINKING=true` e `reasoning_effort="none"`, mas transcrições longas ainda podiam ser divididas em dezenas de blocos por causa de uma estimativa conservadora de caracteres por token. Além disso, segmentos consecutivos de transcrição podiam carregar redundâncias típicas de legendas/transcrição, como repetições adjacentes e sobreposição de prefixo.

## Alterações

- Adicionado chunking por token quando um tokenizer Hugging Face local puder ser carregado.
- Adicionado fallback seguro para estimativa por caracteres quando o tokenizer local não estiver disponível.
- Adicionadas configurações:
  - `SUMMARY_TOKENIZER_BACKEND=auto|hf|estimate`;
  - `SUMMARY_TOKENIZER_MODEL=`;
  - `SUMMARY_DEDUPLICATE_TRANSCRIPT=true|false`;
  - `SUMMARY_MERGE_SAME_SPEAKER_GAP_S=2.0`;
  - `SUMMARY_MIN_OVERLAP_WORDS=6`.
- O texto enviado para resumo passa a unir segmentos consecutivos do mesmo falante quando o gap é pequeno.
- Segmentos adjacentes idênticos são removidos antes da sumarização.
- Prefixos repetidos por sobreposição entre segmentos adjacentes são removidos.
- O Markdown de saída registra o método de tokenização e se a deduplicação pré-resumo estava ativa.
- `print_effective_settings.py` agora exibe as novas configurações de tokenização/deduplicação.

## Observações

- Em `SUMMARY_TOKENIZER_BACKEND=auto`, o sistema tenta carregar `transformers.AutoTokenizer.from_pretrained(..., local_files_only=True)`. Portanto, não baixa tokenizer da internet durante o runtime.
- Se o tokenizer não existir localmente, o sistema cai para a estimativa por caracteres.
- Em `SUMMARY_TOKENIZER_BACKEND=hf`, a ausência do tokenizer local vira erro explícito de configuração.
- Para modelos LM Studio em GGUF, o tokenizer exato pode estar embutido no servidor. Este patch usa o tokenizer Hugging Face local quando disponível; caso contrário, mantém fallback conservador.

## Testes

Testes adicionados/atualizados para:

- chunking com tokenizer injetado;
- deduplicação de segmentos adjacentes repetidos;
- normalização de `SUMMARY_TOKENIZER_BACKEND`;
- preservação dos testes existentes de sumarização e configuração.
