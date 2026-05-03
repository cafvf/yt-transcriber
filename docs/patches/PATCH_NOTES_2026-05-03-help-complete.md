# Patch notes — /help completo e testado

## Objetivo

Atualizar a interface de ajuda do Telegram para listar todos os comandos públicos atuais do bot, com descrições curtas, agrupadas por intenção de uso.

## Alterações

- Criado `HELP_TEXT` centralizado em `TelegramBotAdapter`.
- `/help` passou a mostrar comandos de:
  - entrada e idioma;
  - status, fila e cancelamento;
  - histórico e revisão;
  - exportações;
  - manutenção e ajuda.
- Incluídos explicitamente aliases como `/fila`, `/cancelqueue`, `/limparfila`, `/cancelartudo`, `/videosubs` e atalhos `/json`, `/srt`, `/vtt`.
- Criado teste dedicado para garantir que todo comando público conhecido aparece no help e tem linha com descrição.

## Validação

```bash
python3 -m compileall -q src tests scripts
PYTHONPATH=/mnt/data/test_stubs:src pytest -q \
  tests/unit/infrastructure/telegram/test_help_text.py \
  tests/unit/infrastructure/telegram/test_bot_adapter.py \
  tests/unit/infrastructure/telegram/test_bot_adapter_commands.py \
  tests/unit/test_entrypoint_command_registration.py \
  tests/unit/test_patch_notes_location.py
```

Resultado local no sandbox: `64 passed`.
