# Patch notes — 2026-05-01

Correções aplicadas ao pacote `yt-transcriber-bot` após inspeção estática.

## Código

- Implementado `TelegramBotAdapter.handle_command_redo(...)`.
- Registrado `CommandHandler("redo", ...)` no entrypoint `src/yt_transcriber_bot/__main__.py`.
- Refatorado enfileiramento de links para um helper único usado por mensagens normais e por `/redo`.
- Jobs criados pelo Telegram adapter agora recebem `config_signature` da configuração atual.
- O pipeline agora aceita `snapshot_repository` em `TranscribeVideoDependencies`.
- `RenderMarkdownStep` agora persiste snapshot JSON automaticamente usando o mesmo `stem` do Markdown final. Isso corrige o problema em que `/rename` podia procurar um snapshot inexistente.
- A `Composition` injeta `TranscriptSnapshotRepository` no use case.
- A política FIFO de retenção agora é aplicada após o envio dos artefatos de um job concluído.
- `/clearcache` agora valida se o diretório alvo é exatamente o `models_dir` configurado e recusa diretórios suspeitos ou amplos demais.

## Testes adicionados

- Regressão para `/redo` sem link.
- Regressão para `/redo <link>` enfileirando reprocessamento.
- Regressão para `/clearcache` recusando diretório não configurado.
- Regressão para persistência automática de snapshot após execução do pipeline.

## Documentação

- README atualizado para refletir o estado real do pacote.
- Manual de uso atualizado para descrever os comandos efetivamente implementados.
- Contrato funcional recebeu nota de alinhamento explicitando limitações atuais.

## Validação executada neste ambiente

- `python -m compileall -q src tests`: passou.
- `python -m py_compile` nos arquivos alterados: passou.
- `pytest` não pôde ser executado integralmente neste ambiente porque dependências de runtime/dev não estão instaladas aqui: `python-slugify`, `sqlalchemy`, `python-telegram-bot`, entre outras.

## Limitações mantidas

- `/redo <link>` reprocessa imediatamente como novo job; confirmação inline com diff de configuração ainda não foi implementada.
- Botões inline, `/clearqueue` e `/lasterror` permanecem fora do escopo desta correção.
- A validação E2E real ainda precisa ser feita em ambiente com `ffmpeg`, token do Telegram, token Hugging Face, dependências Python instaladas e acesso aos modelos.
