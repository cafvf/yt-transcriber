# Arquitetura

Este documento descreve o **desenho técnico** do YT Transcriber Bot: como as responsabilidades estão organizadas em camadas, quais padrões de projeto são aplicados, como os componentes se conectam e como o fluxo de dados percorre o sistema. O leitor deste documento já leu o [contrato funcional](./01-contrato-funcional.md) e precisa entender **como** as decisões funcionais serão materializadas.

A arquitetura é deliberadamente **conservadora e ortodoxa**: usa Hexagonal/Ports & Adapters como espinha dorsal porque essa abordagem maximiza a testabilidade — premissa fundamental do TDD purista que rege o projeto.

---

## 1. Princípios estruturantes

### 1.1 Hexagonal / Ports & Adapters
O **núcleo de domínio** (entidades, regras de negócio, serviços de aplicação) **não conhece** Telegram, YouTube, ffmpeg, WhisperX, pyannote ou SQLite. Ele conversa com o mundo exterior por meio de **interfaces abstratas** (`Port`s). Para cada interface, há **uma ou mais implementações concretas** (`Adapter`s) que vivem em camadas externas e são injetadas no núcleo via construtor.

**Consequência prática**: nos testes unitários do domínio, todos os ports recebem implementações fake/in-memory. O domínio é testado **em isolamento absoluto**, sem rede, sem disco, sem GPU.

### 1.2 SOLID
- **S**ingle Responsibility: uma classe, uma razão para mudar.
- **O**pen/Closed: extender via novas implementações de port, não editar as existentes.
- **L**iskov: subclasses honram os contratos das suas interfaces.
- **I**nterface Segregation: ports pequenos e específicos.
- **D**ependency Inversion: domínio depende de abstrações; concretudes injetadas.

### 1.3 Padrões de projeto aplicados

| Padrão | Aplicação |
|---|---|
| **Hexagonal** | Domínio puro + ports + adapters. |
| **Strategy** | `TranscriptionEngine`, `DiarizationEngine`, `SubtitleSource`, `StorageBackend`. |
| **Repository** | `JobRepository`, `SpeakerMapRepository`, `QueueRepository` sobre SQLAlchemy. |
| **Chain of Responsibility** | `Pipeline` é uma sequência de `Stage`s (Download → Convert → Transcribe → Diarize → Render → Deliver). |
| **Command** | Cada comando do Telegram (`StartCommand`, `RenameCommand`, etc.) é uma classe com `execute()`. |
| **Observer / Event Bus** | `Stage`s emitem `ProgressEvent`s; `TelegramProgressReporter` (e `LogReporter`) os consomem. |
| **Factory** | `EngineFactory.create_transcription_engine()` decide modelo/device com base em hardware detectado. |
| **Adapter** | `TelegramAdapter`, `YtDlpAdapter`, `FfmpegAdapter`, `WhisperxAdapter`, `PyannoteAdapter`, `SqliteRepository`. |
| **Null Object** | `NoOpProgressReporter` para testes ou execuções silenciosas. |
| **Specification** | Validação de URLs, idiomas, durações como `Specification`s compostáveis. |

---

## 2. Camadas

```
┌─────────────────────────────────────────────────────────────┐
│  CAMADA DE INFRAESTRUTURA (adapters concretos)              │
│  - TelegramAdapter (python-telegram-bot)                    │
│  - YtDlpAdapter (yt-dlp)                                    │
│  - FfmpegAdapter (subprocess + ffmpeg)                      │
│  - WhisperxAdapter (whisperx)                               │
│  - PyannoteAdapter (pyannote.audio)                         │
│  - SqliteJobRepository (SQLAlchemy)                         │
│  - FilesystemArtifactStore (operações em disco)             │
│  - SystemHardwareDetector (torch.cuda APIs)                 │
└──────────────────────────┬──────────────────────────────────┘
                           │ implementa
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  CAMADA DE PORTS (interfaces abstratas)                     │
│  - VideoSource         (abstrai download YouTube)           │
│  - AudioConverter      (abstrai ffmpeg)                     │
│  - SubtitleSource      (abstrai legendas YouTube)           │
│  - TranscriptionEngine (abstrai WhisperX)                   │
│  - DiarizationEngine   (abstrai pyannote)                   │
│  - JobRepository       (abstrai persistência de jobs)       │
│  - SpeakerMapRepository                                     │
│  - QueueRepository                                          │
│  - ArtifactStore       (abstrai filesystem)                 │
│  - MessageGateway      (abstrai Telegram)                   │
│  - HardwareDetector                                         │
│  - ProgressReporter                                         │
└──────────────────────────┬──────────────────────────────────┘
                           │ usado por
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  CAMADA DE APLICAÇÃO (services / use cases)                 │
│  - ProcessVideoUseCase                                      │
│  - RenameSpeakersUseCase                                    │
│  - ReprocessVideoUseCase                                    │
│  - CancelJobUseCase                                         │
│  - ListJobsUseCase                                          │
│  - ResendLastUseCase                                        │
│  - ClearCacheUseCase                                        │
│  - ClearQueueUseCase                                        │
│  - RecoverInterruptedJobsUseCase                            │
└──────────────────────────┬──────────────────────────────────┘
                           │ orquestra
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  CAMADA DE DOMÍNIO (entidades + regras puras)               │
│  - Job (id, video_id, url, status, paths, ...)              │
│  - VideoMetadata                                            │
│  - Transcript (segmentos, falantes, idioma)                 │
│  - SpeakerMap                                               │
│  - Pipeline (Chain of Responsibility de Stages)             │
│  - Stages: DownloadStage, ConvertStage, TranscribeStage,    │
│            DiarizeStage, RenderStage, DeliverStage          │
│  - Specifications: UrlIsYoutube, LanguageAllowed,           │
│                    DurationWithinLimit, HasEnoughSpeech     │
│  - Events: ProgressEvent, JobStarted, JobCompleted,         │
│            JobFailed, ModelDownloading                      │
│  - ValueObjects: VideoId, Slug, AudioCodec, ModelName,      │
│                  Device, ComputeType, Duration              │
└─────────────────────────────────────────────────────────────┘
```

A regra de dependência é **estrita**: setas de implementação/uso só apontam **para baixo**. Domínio não importa nada de aplicação, aplicação não importa nada de infraestrutura.

---

## 3. Estrutura de diretórios do código

```
yt-transcriber-bot/
├── pyproject.toml
├── uv.lock
├── README.md
├── docs/
│   ├── 01-contrato-funcional.md
│   ├── 02-arquitetura.md
│   ├── 03-manual-de-uso.md
│   ├── 04-manual-de-instalacao.md
│   ├── 05-plano-de-execucao.md
│   ├── 06-funcionalidades-futuras.md
│   └── 07-glossario-e-decisoes.md
├── deploy/
│   └── yt-transcriber-bot.service       # template systemd
├── src/yt_transcriber_bot/
│   ├── __init__.py
│   ├── __main__.py                       # entry point: `python -m yt_transcriber_bot`
│   ├── bootstrap.py                      # composition root (DI manual)
│   ├── config.py                         # pydantic-settings + validação
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── entities/
│   │   │   ├── job.py
│   │   │   ├── transcript.py
│   │   │   ├── speaker_map.py
│   │   │   └── video_metadata.py
│   │   ├── value_objects/
│   │   │   ├── video_id.py
│   │   │   ├── slug.py
│   │   │   ├── duration.py
│   │   │   ├── language.py
│   │   │   ├── model_name.py
│   │   │   └── device.py
│   │   ├── events/
│   │   │   ├── progress_event.py
│   │   │   └── lifecycle_events.py
│   │   ├── specifications/
│   │   │   ├── url_is_youtube.py
│   │   │   ├── language_allowed.py
│   │   │   ├── duration_within_limit.py
│   │   │   └── has_enough_speech.py
│   │   └── pipeline/
│   │       ├── pipeline.py               # Chain of Responsibility
│   │       ├── stage.py                  # interface base
│   │       ├── download_stage.py
│   │       ├── convert_stage.py
│   │       ├── transcribe_stage.py
│   │       ├── diarize_stage.py
│   │       ├── render_stage.py
│   │       └── deliver_stage.py
│   │
│   ├── application/
│   │   ├── __init__.py
│   │   ├── use_cases/
│   │   │   ├── process_video.py
│   │   │   ├── rename_speakers.py
│   │   │   ├── reprocess_video.py
│   │   │   ├── cancel_job.py
│   │   │   ├── list_jobs.py
│   │   │   ├── resend_last.py
│   │   │   ├── clear_cache.py
│   │   │   ├── clear_queue.py
│   │   │   └── recover_interrupted.py
│   │   ├── ports/
│   │   │   ├── video_source.py
│   │   │   ├── audio_converter.py
│   │   │   ├── subtitle_source.py
│   │   │   ├── transcription_engine.py
│   │   │   ├── diarization_engine.py
│   │   │   ├── job_repository.py
│   │   │   ├── speaker_map_repository.py
│   │   │   ├── queue_repository.py
│   │   │   ├── artifact_store.py
│   │   │   ├── message_gateway.py
│   │   │   ├── hardware_detector.py
│   │   │   └── progress_reporter.py
│   │   ├── factories/
│   │   │   └── engine_factory.py
│   │   └── queue/
│   │       └── sequential_queue.py       # consumer single-threaded
│   │
│   └── infrastructure/
│       ├── __init__.py
│       ├── telegram/
│       │   ├── adapter.py                # TelegramAdapter
│       │   ├── progress_reporter.py
│       │   ├── authorization.py          # filtra user_id permitido
│       │   └── commands/                 # Command pattern
│       │       ├── start_command.py
│       │       ├── help_command.py
│       │       ├── status_command.py
│       │       ├── last_command.py
│       │       ├── list_command.py
│       │       ├── redo_command.py
│       │       ├── cancel_command.py
│       │       ├── rename_command.py
│       │       ├── clearcache_command.py
│       │       ├── clearqueue_command.py
│       │       ├── lasterror_command.py
│       │       └── url_message_handler.py
│       ├── youtube/
│       │   ├── ytdlp_adapter.py
│       │   └── subtitle_adapter.py
│       ├── audio/
│       │   └── ffmpeg_adapter.py
│       ├── transcription/
│       │   ├── whisperx_adapter.py
│       │   └── language_detector.py
│       ├── diarization/
│       │   ├── whisperx_diarization_adapter.py    # primário
│       │   └── pyannote_direct_adapter.py         # fallback
│       ├── persistence/
│       │   ├── sqlalchemy/
│       │   │   ├── models.py
│       │   │   ├── job_repository.py
│       │   │   ├── speaker_map_repository.py
│       │   │   └── queue_repository.py
│       │   └── filesystem/
│       │       ├── artifact_store.py
│       │       └── retention_policy.py
│       ├── hardware/
│       │   └── torch_detector.py
│       ├── rendering/
│       │   └── markdown_renderer.py
│       └── logging/
│           └── job_logger.py
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── integration/
│   │   ├── test_youtube_download.py       # @pytest.mark.integration
│   │   ├── test_ffmpeg_conversion.py
│   │   ├── test_whisperx_real.py          # @pytest.mark.slow
│   │   ├── test_pyannote_real.py
│   │   └── test_sqlite_real.py
│   ├── e2e/
│   │   └── test_full_pipeline.py          # vídeo j2p8p7cg0q8
│   └── fixtures/
│       ├── audio/                          # WAVs/OGGs pequenos
│       ├── whisperx_outputs/               # JSONs gravados
│       ├── pyannote_outputs/
│       └── youtube_metadata/
│
├── data/                                   # criado em runtime
│   ├── downloads/
│   ├── processed/
│   ├── transcripts/
│   └── jobs.db
├── models/                                 # cache HF/Whisper (runtime)
└── logs/                                   # logs por job (runtime)
```

---

## 4. Pipeline de processamento (Chain of Responsibility)

O coração do sistema é um **pipeline** representado pela classe `Pipeline`, que executa uma sequência ordenada de `Stage`s. Cada `Stage` é uma classe com a interface:

```python
class Stage(ABC):
    @abstractmethod
    async def execute(self, context: PipelineContext) -> PipelineContext: ...

    @property
    def name(self) -> str: ...

    @property
    def progress_weight(self) -> float:
        """Peso relativo para cálculo do progresso global."""
```

O `PipelineContext` é um objeto mutável que carrega: o `Job` corrente, paths intermediários produzidos, metadados acumulados, transcrição parcial, anotação de diarização, lista de eventos emitidos. Cada `Stage` lê e escreve em campos específicos.

### 4.1 Stages

| # | Stage | Responsabilidade | Pode pular? |
|---|---|---|---|
| 1 | `DownloadStage` | Baixar metadados, validar (duração, idioma, falas), baixar faixa de áudio original. | Não |
| 2 | `SubtitleProbeStage` | Verificar legendas disponíveis no YouTube e classificar (manual/auto/traduzida). | Não |
| 3 | `ConvertStage` | Converter áudio bruto para Opus/OGG mono 32 kbps. | Não |
| 4 | `TranscribeStage` | Se houver legenda válida, usá-la; caso contrário, executar WhisperX. | Pode usar atalho |
| 5 | `AlignStage` | Alinhamento por palavra com wav2vec2 (apenas quando WhisperX foi usado em 4). | Sim |
| 6 | `DiarizeStage` | Diarização (WhisperX primário → pyannote fallback). | Sim, se 1 falante forçado |
| 7 | `RenderStage` | Renderizar MD a partir de transcrição + diarização + metadados. | Não |
| 8 | `DeliverStage` | Aplicar retenção FIFO; enviar áudio + MD pelo Telegram. | Não |

Cada stage emite eventos de progresso (`ProgressEvent(percent, message)`) que são propagados aos `ProgressReporter`s registrados (Telegram e log).

### 4.2 Tratamento de erros no pipeline
- Cada `Stage` pode lançar `StageError` (com sub-classes específicas: `DownloadFailedError`, `LanguageNotAllowedError`, `TranscriptionOOMError`, etc.).
- O `Pipeline` captura, encaminha ao tratamento adequado e marca o job conforme política definida em [contrato §K](./01-contrato-funcional.md#k-erros-e-retentativas).
- `TranscriptionOOMError` aciona o mecanismo de retentativa com modelo menor (decisão dentro do próprio `TranscribeStage`).

---

## 5. Modelo de dados (SQLite)

### 5.1 Tabela `jobs`
| Coluna | Tipo | Notas |
|---|---|---|
| `id` | `INTEGER PRIMARY KEY` | autoincremento |
| `video_id` | `TEXT NOT NULL` | YouTube ID |
| `url` | `TEXT NOT NULL` | URL canônica |
| `title` | `TEXT` | título do vídeo |
| `channel` | `TEXT` | nome do canal |
| `duration_seconds` | `INTEGER` | duração |
| `original_language` | `TEXT` | `pt` ou `en` |
| `status` | `TEXT NOT NULL` | `pending`, `processing`, `completed`, `failed`, `cancelled`, `delivery_failed` |
| `transcription_source` | `TEXT` | `whisperx`, `youtube_manual`, `youtube_auto` |
| `whisper_model` | `TEXT` | `small`, `medium`, etc. |
| `device` | `TEXT` | `cpu` ou `cuda` |
| `compute_type` | `TEXT` | `float16`, `int8_float16`, `int8` |
| `speaker_count` | `INTEGER` | número de falantes detectados |
| `audio_path` | `TEXT` | path do `.ogg` ou `NULL` se expirado |
| `transcript_path` | `TEXT NOT NULL` | path do `.md` (sempre presente) |
| `log_path` | `TEXT` | path do log ou `NULL` se expirado |
| `created_at` | `TIMESTAMP NOT NULL` | criação |
| `completed_at` | `TIMESTAMP` | conclusão |
| `error_message` | `TEXT` | última mensagem de erro |
| `error_traceback` | `TEXT` | stack trace para `/lasterror` |

Índices: `(video_id)`, `(status)`, `(completed_at)`.

### 5.2 Tabela `speakers`
| Coluna | Tipo | Notas |
|---|---|---|
| `id` | `INTEGER PRIMARY KEY` | |
| `job_id` | `INTEGER NOT NULL` | FK para `jobs.id` |
| `original_label` | `TEXT NOT NULL` | `SPEAKER_00`, etc. |
| `display_name` | `TEXT NOT NULL` | nome amigável (default = `original_label`) |
| `speaking_seconds` | `REAL` | tempo total de fala |
| `first_appearance_seconds` | `REAL` | momento da primeira aparição |

Constraint: `UNIQUE(job_id, original_label)`.

### 5.3 Tabela `queue`
| Coluna | Tipo | Notas |
|---|---|---|
| `id` | `INTEGER PRIMARY KEY` | |
| `job_id` | `INTEGER NOT NULL` | FK para `jobs.id` |
| `enqueued_at` | `TIMESTAMP NOT NULL` | ordem FIFO |
| `position` | `INTEGER` | calculado dinamicamente para `/status` |

---

## 6. Fila sequencial

Uma única instância de `SequentialQueueWorker` consome a fila. Como o usuário é único, essa simplificação é suficiente e elimina riscos de concorrência (acesso a GPU, modelos carregados em memória, escrita concorrente em SQLite).

Implementação: um `asyncio.Task` em loop que:
1. Lê o próximo `Job` na fila com status `pending` (ordenado por `enqueued_at`).
2. Marca como `processing`.
3. Instancia o `Pipeline` configurado para aquele job.
4. Executa.
5. Marca o resultado (`completed`, `failed`, `cancelled`).
6. Volta ao topo.

Em paralelo, o `TelegramAdapter` continua respondendo a comandos administrativos (`/status`, `/cancel`, etc.) sem bloquear o loop.

---

## 7. Composition root e injeção de dependências

`bootstrap.py` é o **único** lugar do código que sabe simultaneamente das interfaces (ports) e das implementações concretas (adapters). Lá, ele:

1. Carrega `Config` (via pydantic-settings, lendo das envs).
2. Valida ffmpeg, valida secrets obrigatórios.
3. Detecta hardware via `TorchHardwareDetector`.
4. Decide `EngineFactory` (que produzirá engines do tipo certo).
5. Cria `SqliteJobRepository`, `SpeakerMapRepository`, `QueueRepository`.
6. Cria `FilesystemArtifactStore` com a `RetentionPolicy(max_per_folder=5, keep_md=True)`.
7. Cria `TelegramAdapter` com `Authorization(allowed_user_id=...)`.
8. Cria `SequentialQueueWorker` com todas as dependências injetadas.
9. Inicia o adapter do Telegram em polling.
10. Inicia o worker da fila.
11. Aguarda sinais de encerramento (`SIGINT`, `SIGTERM`).

Não há frameworks de DI: a injeção é manual, explícita e fácil de seguir.

---

## 8. Strategy: motores intercambiáveis

### 8.1 `TranscriptionEngine` (port)
```python
class TranscriptionEngine(Protocol):
    async def transcribe(
        self,
        audio_path: Path,
        language_hint: Optional[Language],
        on_progress: Callable[[float], None],
    ) -> Transcript: ...
```

Implementações:
- `WhisperxAdapter` (única hoje).
- (futuro) `OpenAIWhisperApiAdapter`, `LocalLLMAdapter`, etc.

### 8.2 `DiarizationEngine` (port)
```python
class DiarizationEngine(Protocol):
    async def diarize(
        self,
        audio_path: Path,
        on_progress: Callable[[float], None],
    ) -> SpeakerAnnotation: ...
```

Implementações em ordem de tentativa:
1. `WhisperxDiarizationAdapter` (primário).
2. `PyannoteDirectAdapter` (fallback automático em caso de exceção do primário).

A composição é feita por `FallbackDiarizationEngine` (decorator), que envolve os dois e implementa a política de fallback.

---

## 9. Observador: progresso e logs

`Pipeline` mantém uma lista de `ProgressReporter`s. Em produção:
- `TelegramProgressReporter` — edita a mensagem do chat com throttle de 1s, marcos 10/25/50/75/90.
- `JobLogReporter` — escreve no arquivo de log do job.

Em testes:
- `RecordingProgressReporter` — guarda em lista para assertions.
- `NoOpProgressReporter` — não faz nada.

---

## 10. Especificações (Specification pattern)

Validações de negócio são objetos compostáveis. Exemplos:

```python
class UrlIsYoutube(Specification[str]):
    def is_satisfied_by(self, url: str) -> bool: ...

class LanguageAllowed(Specification[Language]):
    def __init__(self, allowlist: set[Language]) -> None: ...
    def is_satisfied_by(self, lang: Language) -> bool: ...

class DurationWithinLimit(Specification[Duration]):
    def __init__(self, max_seconds: int) -> None: ...
    def is_satisfied_by(self, d: Duration) -> bool: ...

# Composição:
spec = UrlIsYoutube() & DurationWithinLimit(max_seconds=10800)
```

Cada specification é trivialmente unit-testável.

---

## 11. Concorrência e segurança de threads

- O bot é **single-process, async**: um único event loop, um único worker da fila.
- WhisperX/pyannote usam threads internas (BLAS, ONNX runtime). Isso é encapsulado dentro dos adapters; o domínio não vê threads.
- SQLite é acessado via SQLAlchemy com `check_same_thread=False` e `pool_size=1`; como há um worker único, não há contenção real.
- Não há filesystem locks: a unicidade de usuário e o sequencial da fila eliminam corridas.

---

## 12. Configuração efetiva

`Config` (em `config.py`) é uma classe `BaseSettings` do `pydantic-settings`. Variáveis lidas:

| Var | Origem | Default | Sensível? |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | env | — (obrigatório) | Sim |
| `TELEGRAM_ALLOWED_USER_ID` | env | — (obrigatório) | Sim (PII) |
| `HF_TOKEN` | env | — (obrigatório) | Sim |
| `YOUTUBE_COOKIES_BROWSER` | env | `None` | Não |
| `YOUTUBE_COOKIES_FILE` | env | `None` | Sim (path) |
| `WHISPER_MODEL` | env/`.env` | `small` | Não |
| `DEVICE` | env/`.env` | `auto` | Não |
| `COMPUTE_TYPE` | env/`.env` | `auto` | Não |
| `LANGUAGE_ALLOWLIST` | env/`.env` | `pt,en` | Não |
| `MIN_GPU_COMPUTE_CAPABILITY` | env/`.env` | `6.0` | Não |
| `AUDIO_BITRATE_KBPS` | env/`.env` | `32` | Não |
| `AUDIO_CODEC` | env/`.env` | `libopus` | Não |
| `AUDIO_FORMAT` | env/`.env` | `ogg` | Não |
| `MAX_VIDEO_DURATION_MIN` | env/`.env` | `180` | Não |
| `MAX_FILES_PER_FOLDER` | env/`.env` | `5` | Não |
| `MIN_SPEECH_RATIO` | env/`.env` | `0.3` | Não |
| `DATA_DIR` | env/`.env` | `./data` | Não |
| `MODELS_DIR` | env/`.env` | `./models` | Não |
| `LOGS_DIR` | env/`.env` | `./logs` | Não |
| `LOG_LEVEL` | env/`.env` | `INFO` | Não |

Validação no startup: se obrigatórias ausentes ou tipos inválidos, processo aborta com `ConfigurationError` e mensagem orientativa.
