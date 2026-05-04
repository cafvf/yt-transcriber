# Patch notes — resolução robusta do .env de runtime

Data: 2026-05-04

## Objetivo

Corrigir a ambiguidade de carregamento de configuração que permitia que o diagnóstico/runtime lesse valores de exemplo ou defaults em vez do `.env` real do projeto, especialmente em `SUMMARY_MODEL`.

## Alterações

- `AppSettings` agora resolve dinamicamente o arquivo dotenv efetivo em vez de depender apenas de `.env` relativo ao diretório atual.
- Ordem de resolução do arquivo dotenv:
  1. `YT_TRANSCRIBER_ENV_FILE`, se definido;
  2. `.env` na raiz do projeto detectada a partir do diretório atual;
  3. `.env` na raiz do projeto detectada a partir do próprio código-fonte;
  4. `.env` do diretório atual como fallback para instalações fora do repositório.
- `.env.example` passa a ser rejeitado quando apontado explicitamente por `YT_TRANSCRIBER_ENV_FILE`.
- `print_effective_settings.py` agora mostra:
  - raiz detectada pelo diretório atual;
  - raiz detectada pelo código;
  - arquivo forçado resolvido;
  - `.env` usado para diagnóstico/runtime;
  - nota explícita de que `.env.example` nunca é usado como configuração runtime.

## Testes adicionados/ajustados

- `SUMMARY_MODEL` carregado do `.env` na raiz detectada do projeto.
- `SUMMARY_MODEL` carregado de `YT_TRANSCRIBER_ENV_FILE` quando override explícito é usado.
- `.env.example` não é carregado como default de runtime.
- `YT_TRANSCRIBER_ENV_FILE=.env.example` gera erro claro.
- Variável real `SUMMARY_MODEL` continua sobrescrevendo o `.env` e sendo diagnosticável.

## Comandos de validação executados

```bash
PYTHONPATH=src:. python -m pytest \
  tests/unit/application/test_config.py \
  tests/unit/infrastructure/summarization/test_openai_compatible_client.py \
  tests/unit/infrastructure/summarization/test_transcript_summarizer.py \
  tests/unit/test_entrypoint_command_registration.py \
  -q
```

Resultado observado:

```text
48 passed
```
