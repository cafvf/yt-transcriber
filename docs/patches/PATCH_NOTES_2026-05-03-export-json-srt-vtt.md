# Patch notes — export JSON/SRT/VTT

## Objetivo

Adicionar exportação de artefatos derivados de transcrições concluídas sem reprocessar áudio, ASR ou diarização.

## Alterações

- novo serviço `TranscriptExportService`;
- novo comando Telegram `/export json|srt|vtt [n]`;
- suporte a exportar a transcrição mais recente ou uma anterior via índice de `/list`;
- aplicação de `speaker_renames` salvos no job nos arquivos exportados;
- geração de `.json`, `.srt` e `.vtt` ao lado do Markdown selecionado;
- registro do comando `/export` no entrypoint real;
- atualização do `/help` e do manual de uso;
- testes unitários para o serviço exportador e para o comando Telegram.

## Validação local

```bash
python3 -m compileall -q src tests scripts
PYTHONPATH=/mnt/data/test_stubs:src pytest -q   tests/unit/infrastructure/exporting/test_transcript_exporter.py   tests/unit/infrastructure/telegram/test_bot_adapter_commands.py   tests/unit/test_entrypoint_command_registration.py
```
