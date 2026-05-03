# Gate 1 — Domain Model + Config + Repository — REPORT

## Escopo realizado
Implementadas as camadas de domínio puro e a primeira parte da infraestrutura.

**Value Objects** (`domain/value_objects/`): `VideoId` (extração tolerante de URLs `watch`, `youtu.be`, `shorts`, `embed`, `v/`, com texto livre ao redor), `Slug` (sanitização de títulos com truncamento word-boundary), `Duration` (com helpers `to_hms`/`to_human` e operadores de comparação), `Language` (ISO-639-1 com factories `pt`/`en`), `ModelName` (com `vram_requirement_gb` e `smaller_alternative` para fallback), `Device` (auto/cpu/cuda) e `ComputeType` (auto/float16/float32/int8/int8_float16). Todos imutáveis (`frozen=True, slots=True`) com validações no `__post_init__`.

**Especificações** (`domain/specifications/`): classe base genérica `Specification[T]` com combinadores `&`, `|`, `~`, e quatro especificações concretas (`UrlIsYoutube`, `LanguageAllowed`, `DurationWithinLimit`, `HasEnoughSpeech`).

**Entidades** (`domain/entities/`): `VideoMetadata` (imutável, com flag de auto-dub), `TranscriptSegment`/`SpeakerTurn`/`Transcript` (com agregação de turnos por falante e estatísticas de tempo), `Job` (com máquina de estados, transições terminais e mapeamento de renomeações).

**Configuração** (`application/config.py`): `AppSettings` baseada em `pydantic-settings`, lê do ambiente do usuário e opcionalmente de `.env`. Inclui `transcription_signature()` para detectar mudanças de configuração e `validate_runtime_secrets()` para falhar rápido na inicialização.

**Persistência** (`infrastructure/persistence/`): porta `JobRepository`, implementação `SqlAlchemyJobRepository` (mapeamento entidade↔modelo, queries por `video_id`, por usuário, e ordenação por antiguidade para a política FIFO), e `LocalFileStorage` operando via `pathlib`.

## Métricas
A suíte chega a **188 testes** (3 do Gate 0 + 185 do Gate 1), todos verdes em **0,9s**. Cobertura global de **98%** (apenas branches de comparação retornando `NotImplemented` ficam descobertas — não são caminhos de negócio). Ruff (check + format) e Mypy `--strict` retornam zero ofensas em 33 arquivos-fonte.

## Bugs/correções dentro do gate
Durante o lint inicial surgiram quatro categorias de problemas: classes herdando de `(str, Enum)` deveriam usar `StrEnum` (Python 3.11+); EN DASH em docstring acionando `RUF002`; `pytest.raises(ValueError)` sem `match` violando `PT011`; e funções utilitárias não tipadas no repositório. Todos corrigidos e o lint passou a zerar. Cada correção respeitou o protocolo "bug → ajuste sem regredir testes". Não houve mudança em comportamento exposto, apenas em estilo/tipagem.

## Próximo gate
Gate 2 — Adaptadores `YouTubeDownloader` (yt-dlp) e `AudioConverter` (ffmpeg).
