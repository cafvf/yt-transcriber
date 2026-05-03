# Gate Report 4 — Pipeline (Chain of Responsibility) + Use Case

**Status:** ✅ Aprovado (automático)
**Data:** 2026-05-01

## Escopo entregue

- **Pipeline runner** (`application/pipeline/runner.py`) — Step base + executor sequencial com suporte a cancelamento e diagnósticos.
- **PipelineContext** (`application/pipeline/context.py`) — estado mutável compartilhado entre steps (mas isolado dentro de uma execução).
- **Steps concretos** (`application/pipeline/steps.py`):
  1. `FetchMetadataStep` — busca metadados via YouTubeDownloader; rejeita por duração e idioma fora da allowlist.
  2. `TryYouTubeSubtitlesStep` — tenta legendas YT no idioma original (manual > auto-gen); legenda traduzida é rejeitada.
  3. `DownloadAudioStep` — baixa áudio via YouTubeDownloader; rejeita vídeos sem stream de áudio.
  4. `ConvertAudioStep` — chama AudioConverter para Opus/OGG mono 32 kbps.
  5. `SelectRuntimeStep` — calcula RuntimePlan (device + compute_type + modelo) via runtime_selection.
  6. `TranscribeStep` — chama WhisperX; em caso de OOM/RuntimeError retenta uma vez com modelo menor em CPU/INT8 (regra Dúvida 11).
  7. `DiarizeStep` — chama DiarizationEngine; agrega segmentos transcritos a labels de speaker.
  8. `RenderMarkdownStep` — produz o Markdown final via MarkdownRenderer.
- **Use case** (`application/use_cases/transcribe_video.py`) — `TranscribeVideoUseCase` que monta o pipeline com dependências injetadas, executa, persiste o `Job` no JobRepository com transições de estado corretas e devolve `TranscribeVideoResult` (sucesso / rejeição / falha / cancelado).
- **MarkdownRenderer** (`infrastructure/rendering/markdown_renderer.py`) — produz o template aprovado com cabeçalho de auditoria, resumo da diarização (% por falante) e turnos de fala (1 bloco por mudança de speaker).

## Decisões consolidadas neste gate

- **VideoMetadata.original_language** passou a ser `Language | None` para permitir representar "idioma indeterminado" sem violar o contrato do `Language` (ISO-639-1 estrito de 2 letras). Step adapta: se `None`, deixa o WhisperX detectar.
- **`PipelineRejectionError`** (renomeado de `PipelineRejection` por convenção PEP 8/ruff N818) é a exceção semântica de rejeição de negócio, capturada pelo use case para gerar `TranscribeVideoResult.rejected`.
- **AppSettings.prefer_youtube_subtitles** adicionado (default `True`) para habilitar/desabilitar o atalho de legendas.
- **Helper `assign_speakers_to_segments`** alinha turnos de speaker com segmentos transcritos por sobreposição máxima.

## Métricas

| Métrica | Valor | Limiar | Status |
|---|---|---|---|
| Testes unit | 323 | n/a | ✅ |
| Testes integration | 32 | n/a | ✅ |
| Total verde | 355 | 100% | ✅ |
| Cobertura global (com integration) | 93% | ≥ 90% | ✅ |
| Cobertura `markdown_renderer.py` | 100% | ≥ 95% | ✅ |
| Cobertura `pipeline/steps.py` | 100% | ≥ 95% | ✅ |
| Cobertura `transcribe_video.py` | 100% | ≥ 95% | ✅ |
| ruff check | 0 erros | 0 | ✅ |
| ruff format | OK | OK | ✅ |
| mypy --strict | 0 erros | 0 | ✅ |

## Suítes adicionadas neste gate

- `tests/unit/application/pipeline/test_runner.py` (10 testes) — runner, exceções, cancelamento, diagnósticos.
- `tests/unit/application/use_cases/test_transcribe_video.py` (19 testes) — happy path, rejeições (duração, idioma, sem áudio), legendas YT (manual/auto/traduzida), OOM com retry, cancelamento, persistência de `Job`.
- `tests/unit/infrastructure/rendering/test_markdown_renderer.py` (22 testes) — template, escape, fontes (whisperx/yt_manual/yt_auto), tempos, percentuais de speaker, encoding.
- `tests/unit/application/conftest.py` — fakes reutilizáveis: FakeYouTubeDownloader, FakeAudioConverter, FakeGpuDetector, FakeTranscriptionEngine, FakeDiarizationEngine, FakeJobRepository.

## Bugs encontrados e corrigidos (gerando testes de regressão)

| # | Bug | Teste de regressão |
|---|---|---|
| G4.1 | Edição manual corrompeu região do `DiarizeStep` (linhas embaralhadas). | Já coberto por `test_full_pipeline_completes` que falhou de imediato após a corrupção e voltou a passar após reparo. |
| G4.2 | `Language("und")` violava regex 2-letras. | `test_und_language_passes` (idioma indeterminado deve passar para WhisperX detectar). |

## Próximo gate

Gate 5 — TelegramAdapter: handlers de comandos, autorização silenciosa, fila sequencial, mensagens de progresso editadas com 5 marcos, botões inline.
