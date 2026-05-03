# Gate 2 — Adapters YouTube + Áudio — REPORT

## Escopo realizado
Criadas as portas de aquisição de dados externos e suas implementações concretas.

**Porta `YouTubeDownloader`** (`application/ports/youtube_downloader.py`): define os métodos `fetch_metadata`, `list_subtitles`, `fetch_subtitle` e `download_audio`, junto com os tipos `DownloadedAudio`, `SubtitleTrack`, `FetchedSubtitle` e a hierarquia de erros (`YouTubeError`, `VideoUnavailableError`, `MembersOnlyError`, `AgeRestrictedError`, `NoAudioStreamError`).

**Implementação `YtDlpDownloader`** (`infrastructure/youtube/yt_dlp_downloader.py`): adapta `yt-dlp` à porta. Recebe a factory do `YoutubeDL` por construtor (Dependency Injection) para permitir testes sem rede. A detecção de auto-dub usa o sufixo `-orig` no campo `language` dos `formats` ou a flag `original=True`, escolhendo sempre a faixa original e listando idiomas alternativos. As legendas seguem precedência VTT > SRT > TTML, descartam variantes regionais e marcam pistas traduzidas (códigos como `pt-en`). O parser de legendas é tolerante a VTT do YouTube com tags inline (`<c.color>`), numeração SRT e cabeçalhos. Erros do yt-dlp são mapeados por inspeção textual para a hierarquia de exceções da porta.

**Porta `AudioConverter`** (`application/ports/audio_converter.py`): define `convert_to_opus_mono` e `split_for_telegram`, mais o DTO `ConvertedAudio` e a exceção `AudioConversionError`.

**Implementação `FfmpegAudioConverter`** (`infrastructure/audio/ffmpeg_converter.py`): chama `ffmpeg`/`ffprobe` via subprocess. Toda interação passa por `CommandRunner` injetável (`SubprocessCommandRunner` é a implementação real). A conversão usa o codec `libopus` com perfil `voip` para máxima inteligibilidade de fala em bitrates baixos. A divisão para o Telegram usa `-f segment -c copy` para evitar reencode quando o arquivo passa do limite. Validação rigorosa de bitrate (16–128 kbps) e sample rate (apenas valores aceitos pelo Opus: 8/12/16/24/48 kHz).

## Métricas
A suíte cresceu para **237 testes** (188 herdados + 49 novos), todos verdes em **1,3 s**. Ruff (check + format) e Mypy `--strict` continuam zerados. O conversor inclui três testes de integração que executam o `ffmpeg` real (gerando um WAV de 2–3 segundos via lavfi e validando codec, canais e tamanho do OGG resultante) — todos passaram no sandbox.

## Bugs/correções dentro do gate
Quatro categorias de problemas surgiram no lint final: variáveis em comprehension chamadas `l` (E741), pequenos `.code` redundantes, EN DASH em docstring (RUF002) e imports não-ordenados em testes. Todos foram corrigidos via auto-fix do ruff onde aplicável e edições pontuais nos demais. Nenhum teste regrediu — as correções foram puramente de estilo e não alteraram comportamento.

## Próximo gate
Gate 3 — TranscriptionEngine (WhisperX) e DiarizationEngine (WhisperX → pyannote fallback). Será o gate mais sensível em termos de dependências (PyTorch, WhisperX, pyannote) e exigirá injeção de dependência cuidadosa para manter o domínio testável sem precisar rodar modelos reais.
