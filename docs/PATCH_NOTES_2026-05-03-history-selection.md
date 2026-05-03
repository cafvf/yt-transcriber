# Patch notes — seleção de histórico para /last e /rename

## Objetivo

Permitir operar sobre transcrições recentes sem reprocessar vídeo, especialmente o penúltimo vídeo.

## Mudanças

- `/list` agora lista apenas transcrições concluídas e numeradas em ordem decrescente de atualização.
- `/last [n]` reenvia o Markdown da n-ésima transcrição concluída.
  - `/last` mantém compatibilidade e usa `n=1`.
  - `/last 2` reenvia o penúltimo Markdown.
- `/rename [n]` abre o fluxo de renomeação para a n-ésima transcrição concluída.
  - `/rename` mantém compatibilidade e usa `n=1`.
  - `/rename 2` renomeia/mescla falantes do penúltimo vídeo sem reprocessar.
- O estado interno do diálogo de renomeação agora guarda `job_id` e `md_path` do alvo escolhido.
- O input do rename re-renderiza o Markdown do job selecionado, não necessariamente o último.
- O help foi atualizado com os novos usos.

## Testes adicionados

- `/list` numera transcrições concluídas em ordem mais recente primeiro.
- `/last 2` reenvia o penúltimo Markdown.
- `/last 2` fora do intervalo orienta usar `/list`.
- `/rename 2` renomeia o penúltimo job, não o último.
- `/rename 2` fora do intervalo não abre diálogo de renomeação.

## Validação executada

```bash
python3 -m compileall -q src tests scripts
PYTHONPATH=/mnt/data/test_stubs:src pytest -q \
  tests/unit/infrastructure/telegram/test_bot_adapter.py \
  tests/unit/infrastructure/telegram/test_bot_adapter_commands.py \
  tests/unit/infrastructure/telegram/test_job_queue.py
python3 scripts/security/scan_secrets.py --all
```

Resultado local no sandbox:

```text
47 passed
[security] Scanner local: nenhum segredo óbvio encontrado.
```
