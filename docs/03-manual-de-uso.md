# Manual de uso

## Antes de enviar o primeiro pedido

O bot responde somente ao ID configurado. Confirme que `/healthcheck` não
reporta bloqueios, que há espaço em disco e que o modelo/servidor de resumo só
é exigido se você pretende usar `/summary`.

## Transcrever

1. Envie uma URL YouTube diretamente ou use `/transcribe <url>`.
2. Para escolher idioma, use `/pt <url>` ou `/en <url>`.
3. Para conteúdo privado, envie áudio, voz ou documento de áudio.
4. Acompanhe com `/status` ou `/queue`.

Arquivos Telegram aceitos: `mp3`, `m4a`, `ogg`, `opus`, `wav`, `flac` e `webm`,
com MIME de áudio e dentro de `TELEGRAM_MAX_MEDIA_SIZE_MB` e
`MAX_MEDIA_DURATION_MIN`. O bot informa rejeições antes de enfileirar.

## Referência rápida de comandos

`/start` `/help` `/status` `/healthcheck` `/lasterror` `/queue` `/fila`
`/clearqueue` `/cancelqueue` `/limparfila` `/cancelall` `/cancelartudo`
`/cancel` `/redo` `/pt` `/en` `/transcribe` `/list` `/search` `/last`
`/rename` `/summary` `/text` `/export` `/json` `/srt` `/vtt` `/video_subs`
`/videosubs` `/clearcache`.

## Fila e cancelamento

| Ação | Comando |
|---|---|
| Estado atual | `/status` |
| Ver pendências | `/queue` ou `/fila` |
| Cancelar job ativo | `/cancel` |
| Cancelar pendências | `/clearqueue`, `/cancelqueue` ou `/limparfila` |
| Cancelar tudo | `/cancelall` ou `/cancelartudo` |

Há um único processamento por vez. A capacidade total da fila é configurável;
quando cheia, o bot recusa novas entradas em vez de descartá-las silenciosamente.
Jobs concluídos podem ser reprocessados; a deduplicação vale para a mesma
origem/idioma em processamento ou na fila. Em reinício (restart), jobs `pending` com payload mínimo persistido são recuperados.

## Histórico e edição

`/list` mostra jobs concluídos recentes e seus índices. Use esses índices nos
comandos abaixo:

| Ação | Exemplo |
|---|---|
| Reenviar Markdown | `/last 2` |
| Pesquisar histórico | `/search reunião orçamento` |
| Reprocessar URL | `/redo https://youtu.be/... --lang pt` |
| Renomear falantes | `/rename 2` |
| Mesclar nomes | `SPEAKER_00=Ana, SPEAKER_01=Ana` na conversa de renomeação |

`/redo <link>` cria um job novo na hora e não pede confirmação inline. `/search` não consulta mídia nem conteúdo de
outros usuários; os trechos mostrados são sanitizados.

## Exportar e resumir

| Saída | Comando |
|---|---|
| Texto limpo | `/text [n]` |
| JSON | `/json [n]` ou `/export json [n]` |
| SubRip | `/srt [n]` ou `/export srt [n]` |
| WebVTT | `/vtt [n]` ou `/export vtt [n]` |
| MP4 com faixa de legenda | `/video_subs [n]` |
| Resumo Markdown | `/summary [n]` |

Exportações usam o snapshot existente. `/video_subs` só funciona para origem
YouTube e pode recusar vídeos acima dos limites configurados. `/summary`
depende de backend OpenAI-compatible configurado; ele não envia conteúdo para
um serviço externo a menos que você configure um endpoint externo.

## Diagnóstico

- `/healthcheck`: dependências, diretórios, SQLite, espaço, cookies e resumo.
- `/lasterror`: último erro operacional sanitizado.
- `/clearcache`: remove caches locais que podem ser reconstruídos; não use como
  substituto de backup.

Em caso de `delivery_failed` ou falha após restart, consulte `/status`, `/lasterror` e o
[runbook](11-operator-runbook.md). Não envie saída completa de diagnóstico em
canais públicos: paths, títulos e IDs ainda podem ser privados.

## Funcionalidades planejadas

`/translate`, `/search semantic <texto>` e melhorias de confirmação de `/redo`
ainda não são comandos atuais.
