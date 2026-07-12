# Contrato funcional

## Público e limites

O YT Transcriber Bot é um bot privado para um único usuário Telegram definido
em `TELEGRAM_ALLOWED_USER_ID`. Ele processa links YouTube e mídia de áudio
enviada por esse usuário. Não oferece contas, grupos, cotas, isolamento entre
usuários, API pública, processamento em lote ou serviço hospedado.

## Entradas e saída principal

| Entrada | Comportamento |
|---|---|
| URL YouTube | Obtém metadados, aplica limite de duração, tenta legendas e baixa áudio quando necessário. |
| Áudio, voz ou documento Telegram | Valida tipo, extensão, tamanho e duração; baixa para staging privado antes do enqueue. |

O resultado principal é um documento Markdown com título, origem apropriada,
modelo/idioma e falas com timestamps. Para YouTube a identidade pode incluir o
ID/URL da origem. Para Telegram ela não inventa URL ou ID do YouTube.

## Processamento

O bot executa um job por vez. Para YouTube, legendas úteis podem substituir o
ASR; nos demais casos WhisperX transcreve o áudio. A diarização é tentada pelo
backend configurado e o resultado é renderizado mesmo quando a origem não é
YouTube. Cancelamento é cooperativo entre etapas; não há garantia de interromper
uma chamada externa já iniciada instantaneamente.

## Comandos suportados

| Área | Comandos |
|---|---|
| Início e fila | `/start`, `/help`, `/status`, `/queue`, `/fila`, `/cancel`, `/cancelall`, `/clearqueue` |
| Entrada | mensagem com URL, `/transcribe`, `/pt`, `/en`, áudio/voz/documento |
| Histórico | `/list`, `/last [n]`, `/search <texto>`, `/redo <url> [--lang pt\|en]` |
| Edição | `/rename [n]` e botões inline para atribuir/mesclar nomes de falantes |
| Derivados | `/summary [n]`, `/text [n]`, `/json`, `/srt`, `/vtt`, `/export`, `/video_subs` |
| Operação | `/healthcheck`, `/lasterror`, `/clearcache` |

`/redo <link>` cria um job novo imediatamente e não pede confirmação inline.
Jobs concluídos podem ser reprocessados; a deduplicação protege apenas a mesma
origem/idioma em processamento ou na fila. `/last` reenvia o Markdown salvo.
`/video_subs` cria MP4 com legenda selecionável somente para jobs YouTube e
respeita seus limites de tamanho e duração.

## Histórico, busca e retenção

Jobs, status e metadados operacionais ficam em SQLite local. Não existem, nesta versão, tabelas ORM separadas `speakers` ou `queue`. Persiste as atribuições no próprio job, em `speaker_renames_json`. `/search` consulta
somente jobs concluídos do usuário autorizado e usa FTS5 quando disponível, com
fallback limitado e determinístico quando não estiver. Exportações e resumo são
derivados de snapshots: não reprocessam a mídia.

A retenção é FIFO sobre jobs concluídos. Cada áudio convertido recebe um nome
derivado do `job_id`, portanto dois uploads com o mesmo nome não compartilham
artefato. Ela remove staging, áudio convertido e log associado a jobs antigos;
preserva Markdown e snapshots de segmentos para histórico e renomeação. Backup
e descarte de dados devem considerar esse fato.

## Reinício e falhas

A fila é em memória, mas cada job recebe estado persistido. No reinício
(restart),
pendentes com dados suficientes voltam à fila. Estados ativos interrompidos são
marcados como `failed`; `delivering` interrompido vira `delivery_failed`,
consultável por `/lasterror`.
Não existe retomada no meio de download, ASR ou diarização.

Mensagens de erro, auditoria e `/lasterror` são sanitizados. Isso reduz o risco
de expor tokens, cookies, payloads e transcrições, mas os dados locais ainda são
privados e não devem ser publicados.

## Fora de escopo atual

Busca semântica, tradução, ASR alternativo multilíngue, confirmação visual de
`/redo`, retomada por checkpoint, Docker Compose, multiusuário e produção
pública são evoluções futuras.
