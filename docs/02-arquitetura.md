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
| **Strategy** | `TranscriptionEngine`, `DiarizationEngine`, `YouTubeDownloader`, `AudioConverter`, `GPUDetector`. |
| **Repository** | `JobRepository` sobre SQLAlchemy e snapshots de transcrição em filesystem. |
| **Chain of Responsibility** | `PipelineRunner` executa uma sequência de `PipelineStep`s (metadados → legendas → áudio → runtime → transcrição → diarização → Markdown). |
| **Command** | `BotAdapter` roteia comandos Telegram para handlers explícitos (`handle_command_*`) e serviços de aplicação. |
| **Observer / Event Bus** | `ProgressReporter` edita uma mensagem de progresso no Telegram; `ExecutionAuditLogger` registra eventos JSONL estruturados. |
| **Factory/selection** | `select_runtime()` decide modelo/device/compute type com base em configuração e GPU detectada. |
| **Adapter** | `TelegramBotAdapter`, `YtDlpDownloader`, `FfmpegAudioConverter`, engines WhisperX/pyannote e `SqlAlchemyJobRepository`. |
| **Specification** | Validação de URLs, idiomas, durações como `Specification`s compostáveis. |

---

## 2. Camadas

```
┌─────────────────────────────────────────────────────────────┐
│  CAMADA DE INFRAESTRUTURA (adapters concretos)              │
│  - BotAdapter / PTBBotClient (Telegram)                     │
│  - YtDlpDownloader (yt-dlp)                                 │
│  - FFmpegAudioConverter (subprocess + ffmpeg)               │
│  - WhisperXTranscriptionEngine                              │
│  - WhisperX/Pyannote diarization engines                    │
│  - SQLAlchemyJobRepository                                  │
│  - TranscriptSnapshotRepository                             │
│  - MarkdownTranscriptRenderer / exportadores                │
│  - ExecutionAuditLogger (JSONL local)                       │
└──────────────────────────┬──────────────────────────────────┘
                           │ implementa
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  CAMADA DE PORTS (interfaces abstratas em application/ports) │
│  - YouTubeDownloader                                        │
│  - AudioConverter                                           │
│  - TranscriptionEngine                                      │
│  - DiarizationEngine                                        │
│  - JobRepository                                            │
│  - FileStorage                                              │
│  - GPUDetector                                              │
└──────────────────────────┬──────────────────────────────────┘
                           │ usado por
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  CAMADA DE APLICAÇÃO                                        │
│  - TranscribeVideoUseCase                                   │
│  - PipelineRunner + PipelineStep                            │
│  - RenameSpeakersService                                    │
│  - RetentionPolicy / Healthcheck / LastError                │
│  - Runtime selection e configuração efetiva                 │
└──────────────────────────┬──────────────────────────────────┘
                           │ orquestra
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  CAMADA DE DOMÍNIO                                          │
│  - Job, VideoMetadata, Transcript                           │
│  - Specifications                                           │
│  - ValueObjects: VideoId, Slug, Language, Duration,         │
│                  ModelName, Device, ComputeType             │
└─────────────────────────────────────────────────────────────┘
```

A regra de dependência é **estrita**: domínio não importa infraestrutura; aplicação depende de ports e entidades; adapters concretos ficam na borda e são montados no composition root.

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
│   ├── 07-glossario-e-decisoes.md
│   ├── 08-seguranca-e-segredos.md
│   └── patches/
├── deploy/
│   └── yt-transcriber-bot.service
├── scripts/
│   ├── config/
│   └── security/
├── src/yt_transcriber_bot/
│   ├── __main__.py
│   ├── composition_root.py
│   ├── application/
│   │   ├── config.py
│   │   ├── pipeline/
│   │   ├── ports/                     # inclui application/ports/youtube_downloader.py
│   │   ├── runtime_selection.py
│   │   ├── services/
│   │   └── use_cases/transcribe_video.py  # application/use_cases/transcribe_video.py
│   ├── domain/
│   │   ├── entities/
│   │   ├── specifications/
│   │   └── value_objects/
│   └── infrastructure/
│       ├── audio/ffmpeg_converter.py
│       ├── diarization/
│       ├── exporting/
│       ├── gpu/torch_gpu_detector.py
│       ├── logging/execution_audit.py     # infrastructure/logging/execution_audit.py
│       ├── persistence/
│       ├── rendering/markdown_renderer.py
│       ├── summarization/
│       ├── telegram/bot_adapter.py        # infrastructure/telegram/bot_adapter.py
│       ├── text/normalization.py
│       ├── transcription/
│       └── youtube/yt_dlp_downloader.py
└── tests/
    └── unit/
```

A árvore acima descreve o estado atual do repositório. Novas abstrações devem entrar primeiro em `application/ports/` ou `application/services/` quando forem contratos de aplicação; integrações concretas permanecem em `infrastructure/`.

## 4. Pipeline de processamento (Chain of Responsibility)

O coração do processamento é o `PipelineRunner`, que executa uma sequência ordenada de `PipelineStep`s. Cada step expõe a interface:

```python
class PipelineStep(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    def should_run(self, ctx: PipelineContext) -> bool: ...

    @abstractmethod
    def execute(self, ctx: PipelineContext) -> None: ...
```

O `PipelineContext` é um objeto mutável que carrega o `Job` corrente, paths intermediários, metadados, transcrição parcial, anotação de diarização, diagnósticos e artefatos gerados. Cada `PipelineStep` lê e escreve apenas os campos necessários para sua etapa.

### 4.1 Steps

| # | Step | Responsabilidade | Pode pular? |
|---|---|---|---|
| 1 | `FetchMetadataStep` | Buscar metadados e validar duração/idioma. | Não |
| 2 | `TryYouTubeSubtitlesStep` | Tentar legenda elegível do YouTube antes de transcrever áudio. | Sim |
| 3 | `DownloadAudioStep` | Baixar a faixa de áudio original. | Sim, quando legenda aceita substitui ASR |
| 4 | `ConvertAudioStep` | Converter áudio bruto para o formato configurado. | Sim, quando legenda aceita substitui ASR |
| 5 | `SelectRuntimeStep` | Selecionar modelo, device e compute type efetivos. | Sim, quando legenda aceita substitui ASR |
| 6 | `TranscribeStep` | Executar WhisperX quando não houver legenda aceita. | Sim |
| 7 | `DiarizeStep` | Atribuir falantes por WhisperX/pyannote ou falante único forçado. | Sim |
| 8 | `RenderMarkdownStep` | Gerar Markdown final e snapshot de transcrição. | Não |

O runner emite callbacks de progresso por step e eventos de auditoria estruturada. O `BotAdapter` transforma esses eventos em mensagens Telegram; `ExecutionAuditLogger` persiste a trilha JSONL local.

### 4.2 Tratamento de erros no pipeline
- Cada `PipelineStep` pode lançar erros de rejeição de negócio (`VideoTooLongError`, `LanguageNotAllowedError`) ou erros operacionais dos adapters.
- O use case de transcrição captura, encaminha ao tratamento adequado e marca o job conforme política definida em [contrato §K](./01-contrato-funcional.md#k-erros-e-retentativas).
- `OutOfMemoryError` no `TranscribeStep` aciona retentativa com runtime menor quando a política configurada permite.

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

Além da tabela `jobs`, falhas derivadas de comandos que não alteram o status do job principal — por exemplo `/summary`, exportações e `/video_subs` — são registradas em `data/logs/operational_errors.jsonl`. Esse arquivo JSONL é intencionalmente simples: cada linha representa um erro operacional sanitizado com usuário, operação, etapa, severidade, classe da exceção, contexto limitado, traceback final e sugestões de verificação. O `/lasterror` combina essa fonte com jobs `failed` para apresentar o erro mais recente.

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

Uma única instância de `SequentialJobQueue` consome a fila. Como o usuário é único, essa simplificação é suficiente e elimina riscos de concorrência (acesso a GPU, modelos carregados em memória, escrita concorrente em SQLite).

Implementação: um `asyncio.Task` em loop que:
1. Lê o próximo `Job` na fila com status `pending` (ordenado por `enqueued_at`).
2. Marca como `processing`.
3. Instancia o `PipelineRunner` configurado para aquele job.
4. Executa.
5. Marca o resultado (`completed`, `failed`, `cancelled`).
6. Volta ao topo.

Em paralelo, o `TelegramBotAdapter` continua respondendo a comandos administrativos (`/status`, `/cancel`, etc.) sem bloquear o loop.

O cancelamento do job em curso é cooperativo, mas atravessa toda a cadeia de portas/adapters relevantes: `PipelineRunner` injeta um `threading.Event` no `PipelineContext`, os steps repassam esse sinal para downloader/converter/ASR/diarização, e os adapters reais interrompem trabalho ativo sempre que possível (`yt-dlp` via `progress_hooks`, `ffmpeg` via `subprocess.Popen` + `terminate`, wrappers de WhisperX/pyannote com checkpoints antes/depois das fases mais caras). O caminho de legendas do YouTube também usa espera cancelável nas retentativas transitórias e uma etapa de integridade textual antes da renderização final do Markdown.

---

## 7. Composition root e injeção de dependências

`composition_root.py` é o ponto central que conhece simultaneamente as interfaces de aplicação e os adapters concretos. Ele:

1. Recebe `AppSettings` de `application/config.py`.
2. Prepara diretórios de runtime (`data/`, `downloads/`, `processed/`, `transcripts/`, `logs/`, `models/`).
3. Cria repositórios SQLAlchemy e filesystem, incluindo snapshots de transcrição.
4. Monta downloader, conversor de áudio, runtime/engines de transcrição e diarização.
5. Cria `ExecutionAuditLogger` em `settings.logs_dir() / "execution_audit.jsonl"`.
6. Injeta serviços de rename, exportação, legendas, sumarização, healthcheck e last-error no `BotAdapter`.
7. Retorna um objeto `Composition` usado por `__main__.py` para iniciar o polling Telegram e encerrar recursos com segurança.

Não há framework de DI: a injeção é manual, explícita e auditável.

## 8. Strategy: motores intercambiáveis

### 8.1 `TranscriptionEngine` (port)
```python
class TranscriptionEngine(Protocol):
    def transcribe(
        self,
        audio_path: Path,
        *,
        device: Device,
        compute_type: ComputeType,
        model: ModelName,
        allowed_languages: tuple[str, ...],
        language_hint: str | None = None,
        progress: Callable[[float, str], None] | None = None,
    ) -> TranscriptionResult: ...
```

Implementações:
- `WhisperXTranscriptionEngine` (única hoje).
- (futuro) `OpenAIWhisperApiAdapter`, `LocalLLMAdapter`, etc.

### 8.2 `DiarizationEngine` (port)
```python
class DiarizationEngine(Protocol):
    def diarize(
        self,
        audio_path: Path,
        *,
        device: str,
        hf_token: str,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
        progress: Callable[[float, str], None] | None = None,
    ) -> DiarizationResult: ...
```

Implementações em ordem de tentativa:
1. `WhisperXDiarizationEngine` (primário).
2. `PyannoteDiarizationEngine` (fallback automático quando o primário fica indisponível ou falha).

A composição é feita por `CompositeDiarizationEngine`, que tenta cada engine na ordem configurada e preserva o último erro para diagnóstico.

---

## 9. Observador: progresso e logs

`PipelineRunner` recebe callbacks opcionais de progresso e auditoria. Em produção:
- `ProgressReporter` — edita uma única mensagem de progresso no Telegram.
- `ExecutionAuditLogger` — escreve eventos JSONL estruturados em `data/logs/execution_audit.jsonl`.

Em testes, os callbacks podem ser funções simples ou `None`, mantendo o pipeline desacoplado de Telegram e filesystem.

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

`AppSettings` (em `application/config.py`) é uma classe `BaseSettings` do `pydantic-settings`. Variáveis lidas:

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
