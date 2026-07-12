# Arquitetura

## Visão geral

O projeto usa arquitetura hexagonal. Regras de negócio e orquestração não
dependem diretamente de Telegram, YouTube, SQLite, ffmpeg, WhisperX, pyannote
ou LM Studio. Essas integrações ficam atrás de portas e adapters.

```text
Telegram / CLI -> adapter Telegram -> caso de uso -> pipeline -> portas
                                             |                  |
                                      SQLite + snapshots   yt-dlp, ffmpeg,
                                      logs/auditoria       WhisperX, pyannote
```

## Camadas

| Camada | Responsabilidade | Diretório |
|---|---|---|
| Domínio | `Job`, status, transcrição, value objects e regras puras | `domain/` |
| Aplicação | caso de uso, pipeline, serviços e portas | `application/` |
| Infraestrutura | adapters de Telegram, SQLite, filesystem, ML, ffmpeg, YouTube e resumo | `infrastructure/` |
| Composição | conecta as implementações concretas | `composition_root.py`, `__main__.py` |

Pontos de entrada: `application/config.py`, `application/use_cases/transcribe_video.py`,
`application/ports/youtube_downloader.py`, `infrastructure/telegram/bot_adapter.py`
e `infrastructure/logging/execution_audit.py`.

O domínio não deve importar bibliotecas de infraestrutura. A aplicação conhece
interfaces como `JobRepository`, downloader, conversor, transcritor, diarizador,
armazenamento e busca, mas não as classes concretas.

## Pipeline por origem

```text
YouTube: FetchMetadata -> TryYouTubeSubtitles -> DownloadAudio
Telegram: UseTelegramAudio
Ambos: ConvertAudio -> SelectRuntime -> Transcribe -> Diarize -> RenderMarkdown
```

`PipelineRunner` executa etapas sequenciais, publica progresso/auditoria e
respeita cancelamento cooperativo. O caso de uso persiste o job antes da
execução; ao produzir a transcrição ele passa a `delivering`. O adapter Telegram
entrega os artefatos e então marca `completed`, ou `delivery_failed` após
esgotar tentativas.

## Dados locais

SQLite contém a tabela de jobs e documentos derivados para busca. A tabela
`jobs` possui `job_id`, `video_id`, `status`, `requested_by_user_id`,
`requested_at`, `updated_at`, `error_message`, `source_url`, `source_type`,
`canonical_reference`, `source_title`, `source_duration_seconds`,
`requested_chat_id`, `requested_language`, `artifact_policy`,
`config_signature`, `speaker_renames_json`, `md_path`, `audio_path` e
`log_path`. Um job guarda
fonte, estado, idioma solicitado, chat, política de artefato e paths locais
necessários para recuperação. Ainda não há tabelas separadas `speakers` ou `queue`.
Snapshots JSON versionados guardam segmentos e
renomes; Markdown é o artefato humano principal.

```text
data/jobs.db                 estados, histórico e busca
data/downloads/<job-id>/     staging privado Telegram/YouTube
data/processed/              áudio convertido
data/transcripts/            Markdown
data/segments/               snapshot para edição/exportação
data/summaries/              resumos
data/logs/*.jsonl            auditoria e erros sanitizados
```

Os nomes reais dependem da configuração. Paths e conteúdo são dados privados.

## Recovery e retenção

`StartupRecoveryService` lê `jobs` uma vez por inicialização. A fila é em memória.
Em reinício
(restart), jobs `pending`
com payload completo são re-enfileirados por data; estados ativos tornam-se
`failed`; `delivering` torna-se `delivery_failed`, apresentado por
`/lasterror`. O design não tenta continuar
uma etapa cara pelo meio.

`RetentionPolicy` aplica FIFO aos concluídos: remove mídia bruta, conversão e
logs do job antigo, preservando Markdown e snapshot. Portanto, manter o banco
e os snapshots é necessário para histórico e `/rename`.

## Extensão segura

Uma nova integração deve implementar uma porta, ser ligada em
`composition_root.py`, ter testes de unidade e não transportar payloads ou
segredos para domínio/aplicação. Todo novo caminho externo precisa usar a
sanitização central e registrar somente metadados operacionais mínimos.
