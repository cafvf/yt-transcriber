# Patch notes — 2026-05-04 — Diagnóstico de `.env` para sumarização

## Objetivo

Reduzir ambiguidade na configuração efetiva usada pela feature `/summary`, especialmente quando `SUMMARY_MODEL` parece diferente do valor definido no `.env`.

## Alterações

- Adicionado suporte opcional a `YT_TRANSCRIBER_ENV_FILE` em `AppSettings`.
  - Quando definido, esse caminho passa a ser o `.env` carregado pelo bot.
  - Quando não definido, o comportamento padrão permanece: carregar `.env` relativo ao diretório atual do processo.
- Melhorado `scripts/config/print_effective_settings.py` para mostrar:
  - diretório atual;
  - valor de `YT_TRANSCRIBER_ENV_FILE`;
  - arquivo `.env` usado no diagnóstico;
  - se o arquivo existe;
  - origem de cada campo relevante: ambiente real, `.env` ou valor padrão/argumento explícito.
- O diagnóstico agora explicita que variáveis reais do ambiente sobrescrevem valores do `.env`.
- Mantida a regra de segurança: segredos continuam mascarados no output.

## Testes adicionados/atualizados

- `SUMMARY_MODEL` é carregado a partir do `.env` do diretório atual.
- `YT_TRANSCRIBER_ENV_FILE` força o carregamento de um `.env` específico.
- Variável real `SUMMARY_MODEL` sobrescreve o `.env` e aparece como origem diagnosticável.
- `/help` continua listando `/summary [n]`.

## Comandos úteis

```bash
uv run python scripts/config/print_effective_settings.py
```

Para forçar um arquivo `.env` específico:

```bash
export YT_TRANSCRIBER_ENV_FILE=/home/cafvf/git/yt-transcriber/.env
uv run python scripts/config/print_effective_settings.py
uv run python -m yt_transcriber_bot
```

Para remover uma variável real que esteja sobrescrevendo o `.env`:

```bash
unset SUMMARY_MODEL
```
