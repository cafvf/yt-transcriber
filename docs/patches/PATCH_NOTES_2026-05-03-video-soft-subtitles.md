# Patch — vídeo com legenda selecionável

Implementa a exportação de MP4 com faixa de legenda selecionável, sem legenda queimada.

## Funcionalidades

- Novo comando `/video_subs [n]`.
- Alias `/videosubs [n]`.
- Usa a mesma numeração de histórico de `/list`, `/last [n]`, `/rename [n]` e `/export [n]`.
- Gera `.srt` a partir do snapshot já salvo.
- Baixa um MP4 compatível com `yt-dlp`.
- Usa `ffmpeg` para inserir a legenda como faixa `mov_text`.
- Envia o MP4 pelo Telegram com caption.

## Limites

- `MAX_VIDEO_SUBTITLES_DURATION_MIN=30`
- `MAX_VIDEO_SUBTITLES_SIZE_MB=200`
- `VIDEO_EXPORTS_DIR_NAME=video_exports`

## Testes

Inclui testes para:

- comando `/video_subs`;
- seleção por índice `/video_subs 2`;
- rejeição de vídeos acima de 30 minutos;
- rejeição por tamanho acima do limite;
- chamada `ffmpeg` com `-c:s mov_text` e cópia de áudio/vídeo;
- registro do comando no entrypoint real.
