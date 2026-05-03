# Patch Notes — 2026-05-03 — Summary context budget

## Correção

A sumarização via LM Studio agora aplica um orçamento conservador de entrada antes de chamar a API OpenAI-compatible.

O problema observado era que o bot podia enviar prompts maiores que a janela ativa do modelo no LM Studio, por exemplo:

```text
request (5944 tokens) exceeds the available context size (4096 tokens)
```

## Alterações

- Reduzidos defaults de sumarização:
  - `SUMMARY_MAX_TOKENS=1024`
  - `SUMMARY_MAX_CHARS_PER_CHUNK=4000`
  - `SUMMARY_TIMEOUT_S=300`
- Adicionados:
  - `SUMMARY_MAX_INPUT_TOKENS=2500`
  - `SUMMARY_CHARS_PER_TOKEN=2.0`
- O chunking agora usa o menor valor entre:
  - limite por caracteres; e
  - limite estimado por tokens de entrada.
- Segmentos individuais muito longos agora são divididos para evitar prompts enormes.
- Erros HTTP de contexto da API OpenAI-compatible agora retornam sugestão explícita para reduzir os parâmetros de sumarização.
- Documentação e `.env.example` atualizados para LM Studio com contexto de 4096 tokens.

## Validação

```bash
python3 -m compileall -q src tests scripts
PYTHONPATH=/mnt/data/test_stubs:src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_PLUGINS=pytest_asyncio.plugin pytest -q \
  tests/unit/infrastructure/summarization/test_openai_compatible_client.py \
  tests/unit/infrastructure/summarization/test_transcript_summarizer.py \
  tests/unit/application/test_config.py
python3 scripts/security/scan_secrets.py --all
```

Resultado local no ambiente de patch: `29 passed` nos testes direcionados.
