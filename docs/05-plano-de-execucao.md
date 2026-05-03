# Plano de Execução

Este documento detalha o **plano de implementação** do projeto, dividido em **oito gates incrementais**. Cada gate tem escopo bem delimitado, lista exaustiva de testes obrigatórios, critérios de aceitação objetivos, e o ciclo de feedback **"bug → novo teste de regressão → correção"** explicitamente regulado.

A ordem dos gates é estrita: um gate não inicia antes do anterior estar fechado, pois as camadas dependem umas das outras.

---

## 0. Convenções aplicáveis a todos os gates

### 0.1 Ciclo Red-Green-Refactor (TDD purista)
Para cada método produtivo:
1. **Red**: escrever um teste que falha demonstrando o comportamento desejado.
2. **Green**: escrever o mínimo de código produtivo que faz o teste passar.
3. **Refactor**: limpar o código sem quebrar testes; reaplicar princípios SOLID.

### 0.2 Política "bug → novo teste de regressão"
Qualquer falha encontrada na avaliação de um gate (seja por mim, seja por você ao revisar):
1. **Primeiro**, um teste novo é criado, falhando, que reproduz o bug.
2. **Depois**, o bug é corrigido.
3. O teste fica permanentemente na suíte como **teste de regressão**, garantindo que a falha não retorne.
4. O contador de testes do gate aumenta — não há "redução" de cobertura para acomodar correções.

### 0.3 Critério geral de fechamento de gate
Para um gate ser considerado **fechado**, **todos** os itens abaixo precisam ser verdade:
- ✅ Todos os testes obrigatórios listados estão escritos e passando.
- ✅ Todos os testes adicionais surgidos por bugs também passam.
- ✅ `uv run pytest` retorna 0 (zero falhas, zero erros).
- ✅ `uv run pytest --cov` mostra cobertura ≥ 100% no domínio e ≥ 80% nos adapters.
- ✅ `uv run ruff check .` retorna 0 ofensas.
- ✅ `uv run ruff format --check .` retorna 0 arquivos a reformatar.
- ✅ `uv run mypy --strict src/` retorna 0 erros de tipo.
- ✅ Um **Gate Report** (relatório curto) é gerado e arquivado em `docs/gate-reports/gate-N-report.md` para registro histórico.

O avanço entre gates é **automático**: cumpridos os critérios objetivos acima, o próximo gate inicia imediatamente, sem interrupção para aprovação manual. O Gate Report é informativo (auditoria), não bloqueante. O usuário pode, a qualquer momento, intervir para pausar, redirecionar ou ajustar o plano — mas o fluxo padrão é contínuo.

### 0.4 Estrutura de testes
```
tests/
├── conftest.py                 # fixtures globais
├── unit/                       # rodam em milissegundos, sem I/O real
│   ├── domain/
│   ├── application/
│   └── infrastructure/
├── integration/                # rodam em segundos, podem usar disco
│   ├── test_youtube_download.py     @pytest.mark.integration
│   ├── test_ffmpeg_conversion.py    @pytest.mark.integration
│   ├── test_whisperx_real.py        @pytest.mark.integration @pytest.mark.slow
│   ├── test_pyannote_real.py        @pytest.mark.integration @pytest.mark.slow
│   └── test_sqlite_real.py          @pytest.mark.integration
├── e2e/                        # rodam em minutos
│   └── test_full_pipeline.py        @pytest.mark.e2e @pytest.mark.slow
└── fixtures/                   # arquivos de apoio versionados
    ├── audio/                  # WAVs/OGGs pequenos
    ├── whisperx_outputs/
    ├── pyannote_outputs/
    └── youtube_metadata/
```

Marks:
- Testes unitários: rodados em **todo** `pytest` (sem opções).
- Marcados com `@pytest.mark.integration`: rodados com `pytest -m integration`.
- Marcados com `@pytest.mark.slow`: rodados com `pytest -m slow` ou `pytest -m "integration and slow"`.
- Marcados com `@pytest.mark.e2e`: rodados com `pytest -m e2e`.

Pipeline de avaliação por gate: roda `pytest` (rápido) sempre; rodadas de integração/e2e nos gates apropriados (3, 4, 7).

### 0.5 Modelo do Gate Report
Cada gate fechado produz um relatório curto neste formato:

```markdown
# Gate N — Título — REPORT

## Escopo realizado
- ...

## Métricas
- Testes adicionados: X (unit) + Y (integration) + Z (regression)
- Cobertura domain: 100.0% | application: 99.2% | infrastructure: 87.1%
- Tempo da suíte completa: 4.3s (unit) + 18.2s (integration)
- Linhas adicionadas: ~N | removidas: ~M

## Bugs encontrados durante o gate (se houver)
1. <descrição> — corrigido + teste de regressão `test_xxx`

## Riscos e dívidas conhecidas
- ...

## Próximo gate
N+1 — <título>
```

---

## Gate 0 — Bootstrap do projeto

### Objetivo
Estabelecer a infraestrutura mínima de desenvolvimento: estrutura de diretórios, `pyproject.toml`, `uv.lock`, ferramentas de qualidade (ruff, mypy, pytest), configurações iniciais. **Nenhuma lógica de negócio é escrita.**

### Escopo
- Criar `pyproject.toml` com metadata, dependências de runtime e dev, configurações de tools.
- `uv lock` e `uv sync` rodando limpos.
- Estrutura de diretórios `src/yt_transcriber_bot/` e `tests/` criada.
- `src/yt_transcriber_bot/__init__.py` com versão.
- `src/yt_transcriber_bot/__main__.py` minimal (apenas imprime "alive").
- Configuração de `ruff`, `mypy`, `pytest`, `pytest-cov` em `pyproject.toml`.
- `.gitignore` adequado (`.venv`, `data/`, `models/`, `logs/`, `__pycache__`, `.coverage`, etc.).
- Template `deploy/yt-transcriber-bot.service`.

### Testes obrigatórios (mínimos, é apenas bootstrap)
1. **`test_package_imports`** — verifica que `import yt_transcriber_bot` funciona e expõe `__version__`.
2. **`test_main_module_runs`** — `python -m yt_transcriber_bot --version` executa e retorna 0.

### Critérios de aceitação adicionais
- `uv run pytest` passa.
- `uv run ruff check .` retorna 0 ofensas.
- `uv run mypy --strict src/` retorna 0 erros (em código mínimo, trivial).
- README e docs já presentes (já escritos nesta fase de planejamento).

### Não entra neste gate
- Qualquer lógica de domínio.
- Qualquer adapter.
- Qualquer interação Telegram/YouTube/WhisperX.

---

## Gate 1 — Domain model + Config + Repository SQLite

### Objetivo
Construir todo o **núcleo de domínio puro** (entidades, value objects, especificações, eventos), o sistema de configuração, e os repositórios SQLite — tudo testável **100% sem I/O real**, exceto o repositório (que é testado contra SQLite in-memory, ainda rapidíssimo).

### Escopo
**Domínio**:
- Value objects: `VideoId`, `Slug`, `Duration`, `Language`, `ModelName`, `Device`, `ComputeType`.
- Entidades: `Job` (com transições de status válidas), `VideoMetadata`, `Transcript`, `SpeakerMap`.
- Eventos: `ProgressEvent`, `JobStarted`, `JobCompleted`, `JobFailed`, `ModelDownloading`, `ModelDownloaded`.
- Especificações: `UrlIsYoutube`, `LanguageAllowed`, `DurationWithinLimit`, `HasEnoughSpeech`.

**Configuração**:
- `Config` (pydantic-settings) com todas as 19 variáveis listadas em `02-arquitetura.md` §12.
- Validação rigorosa: tipos, ranges (ex.: `MAX_FILES_PER_FOLDER >= 1`), conjuntos (`LANGUAGE_ALLOWLIST ⊆ {pt, en}`).
- Erro claro no startup se variável obrigatória ausente.

**Persistência**:
- Modelos SQLAlchemy 2.x: `JobModel`, `SpeakerModel`, `QueueModel`.
- Repositórios concretos: `SqliteJobRepository`, `SqliteSpeakerMapRepository`, `SqliteQueueRepository`.
- Interfaces (ports): `JobRepository`, `SpeakerMapRepository`, `QueueRepository`.
- Migration inicial criando tabelas (script simples, sem Alembic — escala não exige).

### Testes obrigatórios

**Value objects (unitários, ~25 testes)**
1. `test_video_id_extracts_from_watch_url`
2. `test_video_id_extracts_from_short_url`
3. `test_video_id_extracts_from_youtu_be`
4. `test_video_id_normalizes_with_extra_params`
5. `test_video_id_rejects_invalid_url`
6. `test_video_id_rejects_non_youtube_domain`
7. `test_video_id_extracts_from_text_with_url_in_middle`
8. `test_slug_handles_accents` (`"Não vou."` → `"nao-vou"`)
9. `test_slug_handles_emoji_and_special_chars`
10. `test_slug_truncates_long_titles_at_safe_limit`
11. `test_slug_collision_appends_suffix`
12. `test_duration_from_seconds_to_hms_format`
13. `test_duration_within_limit_specification`
14. `test_duration_above_limit_rejected`
15. `test_language_accepts_pt_en_only`
16. `test_language_rejects_unknown_codes`
17. `test_model_name_validates_against_allowlist`
18. `test_device_auto_validates`
19. `test_compute_type_validates`
20. `test_url_is_youtube_specification_accepts_valid`
21. `test_url_is_youtube_specification_rejects_invalid`
22. `test_specifications_can_be_combined_with_and`
23. `test_specifications_can_be_combined_with_or`
24. `test_has_enough_speech_specification`
25. `test_has_enough_speech_below_threshold_rejects`

**Entidades (unitários, ~15 testes)**
1. `test_job_starts_in_pending`
2. `test_job_transitions_pending_to_processing`
3. `test_job_transitions_processing_to_completed`
4. `test_job_transitions_processing_to_failed`
5. `test_job_transitions_processing_to_cancelled`
6. `test_job_invalid_transition_raises`
7. `test_job_records_error_message_and_traceback_on_failure`
8. `test_job_serializes_to_dict_for_persistence`
9. `test_job_can_be_loaded_from_dict`
10. `test_video_metadata_holds_all_required_fields`
11. `test_transcript_aggregates_segments_by_speaker_turn`
12. `test_transcript_merges_consecutive_same_speaker_segments`
13. `test_speaker_map_default_uses_original_labels`
14. `test_speaker_map_apply_renames_correctly`
15. `test_speaker_map_partial_rename_keeps_others`

**Configuração (unitários, ~12 testes)**
1. `test_config_loads_from_env_vars`
2. `test_config_loads_from_dotenv_file`
3. `test_config_env_vars_override_dotenv`
4. `test_config_missing_telegram_bot_token_aborts`
5. `test_config_missing_allowed_user_id_aborts`
6. `test_config_missing_hf_token_aborts`
7. `test_config_invalid_whisper_model_aborts`
8. `test_config_invalid_language_in_allowlist_aborts`
9. `test_config_invalid_min_compute_capability_aborts`
10. `test_config_max_video_duration_must_be_positive`
11. `test_config_default_values_when_optional_omitted`
12. `test_config_youtube_cookies_are_optional`

**Repositórios (unitários com SQLite in-memory, ~20 testes)**
1. `test_sqlite_job_repository_save_and_load`
2. `test_sqlite_job_repository_find_by_video_id`
3. `test_sqlite_job_repository_find_by_video_id_returns_none_when_absent`
4. `test_sqlite_job_repository_list_recent_orders_by_completed_at_desc`
5. `test_sqlite_job_repository_list_recent_limits_to_n`
6. `test_sqlite_job_repository_update_status`
7. `test_sqlite_job_repository_marks_as_failed_with_traceback`
8. `test_sqlite_job_repository_finds_processing_jobs_for_recovery`
9. `test_sqlite_speaker_map_repository_default_when_absent`
10. `test_sqlite_speaker_map_repository_save_and_load`
11. `test_sqlite_speaker_map_repository_overwrite_on_resave`
12. `test_sqlite_queue_repository_enqueue_appends`
13. `test_sqlite_queue_repository_dequeue_fifo_order`
14. `test_sqlite_queue_repository_dequeue_empty_returns_none`
15. `test_sqlite_queue_repository_size`
16. `test_sqlite_queue_repository_clear`
17. `test_sqlite_queue_repository_position_of_job`
18. `test_sqlite_repository_handles_concurrent_reads_safely` (smoke)
19. `test_sqlite_repository_creates_schema_on_first_use`
20. `test_sqlite_repository_migrates_idempotently_on_subsequent_starts`

**Total estimado para Gate 1**: ~72 testes unitários.

### Critérios de aceitação adicionais
- Cobertura `domain/`: 100%.
- Cobertura `application/ports/`: N/A (interfaces puras).
- Cobertura `infrastructure/persistence/`: ≥ 95% (algumas linhas defensivas podem não ser exercitadas).
- mypy --strict 100% limpo.

### Não entra neste gate
- Adaptadores externos (YouTube, ffmpeg, WhisperX, pyannote, Telegram).
- Pipeline / Stages.
- Use cases.

---

## Gate 2 — YouTubeDownloader e AudioConverter

### Objetivo
Implementar os adaptadores responsáveis por **adquirir áudio do YouTube** (faixa original, ignorando dub) e **converter** para Opus/OGG. Estes são adapters de I/O com binários externos (`yt-dlp`, `ffmpeg`).

### Escopo
- Port `VideoSource` com método `fetch_metadata(url)` e `download_audio(metadata, target_path)`.
- Port `SubtitleSource` com método `fetch_subtitle(video_id, language)` retornando `Subtitle | None`, classificada como `manual`, `auto`, `translated` ou `unavailable`.
- Adapter `YtDlpAdapter` implementando ambos os ports.
- Port `AudioConverter` com método `convert_to_opus_ogg(input, output, bitrate)`.
- Adapter `FfmpegAdapter` implementando.
- Validação de presença do binário `ffmpeg` no startup (`FfmpegHealthCheck`).
- Detecção de auto-dub e seleção de faixa original.
- Tratamento de erros: `VideoUnavailableError`, `VideoMembersOnlyError`, `VideoAgeRestrictedError`, `VideoRemovedError`, `LiveInProgressError`, `FfmpegMissingError`, `FfmpegConversionError`.

### Testes obrigatórios

**Unitários com mocks de `yt-dlp` e `subprocess` (~30 testes)**
1. `test_ytdlp_fetch_metadata_parses_basic_fields`
2. `test_ytdlp_fetch_metadata_detects_auto_dub_alternate_languages`
3. `test_ytdlp_fetch_metadata_detects_no_alternate_languages`
4. `test_ytdlp_fetch_metadata_extracts_original_language`
5. `test_ytdlp_fetch_metadata_extracts_duration_seconds`
6. `test_ytdlp_fetch_metadata_extracts_channel_name`
7. `test_ytdlp_fetch_metadata_normalizes_youtu_be_to_canonical`
8. `test_ytdlp_fetch_metadata_strips_playlist_param`
9. `test_ytdlp_fetch_metadata_raises_video_unavailable_on_404`
10. `test_ytdlp_fetch_metadata_raises_members_only`
11. `test_ytdlp_fetch_metadata_raises_age_restricted_when_no_cookies`
12. `test_ytdlp_fetch_metadata_raises_live_in_progress`
13. `test_ytdlp_download_audio_selects_original_track_for_auto_dubbed`
14. `test_ytdlp_download_audio_uses_cookies_browser_when_set`
15. `test_ytdlp_download_audio_uses_cookies_file_when_set`
16. `test_ytdlp_download_audio_uses_no_cookies_when_neither_set`
17. `test_ytdlp_download_audio_writes_to_target_path`
18. `test_ytdlp_download_audio_progress_callback_invoked`
19. `test_ytdlp_subtitle_returns_manual_when_present`
20. `test_ytdlp_subtitle_returns_auto_when_only_auto_present`
21. `test_ytdlp_subtitle_returns_unavailable_when_none`
22. `test_ytdlp_subtitle_marks_translated_as_translated`
23. `test_ytdlp_subtitle_only_returns_in_requested_language`
24. `test_ffmpeg_adapter_invokes_correct_command_line`
25. `test_ffmpeg_adapter_uses_libopus_codec`
26. `test_ffmpeg_adapter_writes_output_to_target_path`
27. `test_ffmpeg_adapter_propagates_progress_callback`
28. `test_ffmpeg_adapter_raises_on_nonzero_exit`
29. `test_ffmpeg_adapter_raises_on_missing_binary`
30. `test_ffmpeg_health_check_passes_when_binary_present`

**Integrações reais (`@pytest.mark.integration`, ~5 testes)**
Usam fixtures de áudio pequenos versionados em `tests/fixtures/audio/`:
1. `test_ffmpeg_real_converts_wav_to_ogg_opus_correctly` — converte um WAV de 5s, valida formato de saída com `ffprobe`.
2. `test_ffmpeg_real_output_is_mono` — valida 1 canal.
3. `test_ffmpeg_real_bitrate_close_to_target` — valida bitrate efetivo dentro de ±20%.
4. `test_ffmpeg_real_smaller_than_input` — sanity check.
5. `test_ffmpeg_health_check_real` — chama `ffmpeg -version` real.

**YouTube real** (sem teste real no sandbox por causa do bot-detection, ver §N do contrato; teste é desabilitado por padrão e marcado para o usuário rodar localmente).

**Total estimado para Gate 2**: ~30 unitários + 5 integração.

### Critérios de aceitação adicionais
- Cobertura adapters: ≥ 85%.
- Smoke test manual: instanciar `FfmpegAdapter` e converter um WAV real.

### Não entra neste gate
- Transcrição.
- Diarização.
- Pipeline.

---

## Gate 3 — TranscriptionEngine + DiarizationEngine

### Objetivo
Implementar a transcrição com **WhisperX** e a diarização com **WhisperX (primário)** + **pyannote direto (fallback)**, com auto-detecção de hardware.

### Escopo
- Port `TranscriptionEngine`.
- Adapter `WhisperxAdapter` (transcrição + alinhamento por palavra).
- Port `DiarizationEngine`.
- Adapter `WhisperxDiarizationAdapter` (primário).
- Adapter `PyannoteDirectAdapter` (fallback).
- Decorator `FallbackDiarizationEngine` que compõe os dois.
- Port `HardwareDetector`.
- Adapter `TorchHardwareDetector` (lê `torch.cuda` APIs).
- Factory `EngineFactory` que decide modelo/device/compute_type a partir de `Config` + `HardwareDetector`.
- `LanguageDetector` (componente do pipeline de transcrição).

### Testes obrigatórios

**Unitários com mocks (~25 testes)**
1. `test_torch_hardware_detector_no_cuda_returns_cpu`
2. `test_torch_hardware_detector_old_gpu_below_min_cc_returns_cpu`
3. `test_torch_hardware_detector_modern_gpu_returns_cuda`
4. `test_torch_hardware_detector_insufficient_vram_returns_cpu`
5. `test_engine_factory_picks_cpu_int8_when_no_gpu`
6. `test_engine_factory_picks_cuda_float16_when_gpu_modern`
7. `test_engine_factory_picks_cuda_int8_float16_when_low_vram_modern_gpu`
8. `test_engine_factory_respects_explicit_device_override`
9. `test_engine_factory_respects_explicit_compute_type_override`
10. `test_engine_factory_falls_back_when_explicit_cuda_unavailable`
11. `test_whisperx_adapter_loads_correct_model`
12. `test_whisperx_adapter_transcribe_returns_segments_with_timestamps`
13. `test_whisperx_adapter_alignment_attaches_word_level_timestamps`
14. `test_whisperx_adapter_progress_callback_at_marks_10_25_50_75_90`
15. `test_whisperx_adapter_raises_oom_error_on_cuda_oom`
16. `test_whisperx_adapter_raises_language_not_allowed_when_outside_allowlist`
17. `test_whisperx_diarization_returns_speaker_annotation`
18. `test_whisperx_diarization_progress_callback_invoked`
19. `test_pyannote_direct_diarization_returns_speaker_annotation`
20. `test_fallback_diarization_uses_primary_when_succeeds`
21. `test_fallback_diarization_falls_back_when_primary_raises`
22. `test_fallback_diarization_logs_fallback_event`
23. `test_fallback_diarization_propagates_error_when_both_fail`
24. `test_language_detector_returns_pt_for_pt_audio_fixture`
25. `test_language_detector_returns_en_for_en_audio_fixture`

**Integrações reais (`@pytest.mark.integration @pytest.mark.slow`, ~6 testes)**
Usam fixtures pequenos (clipes de 5–15s) com fala conhecida:
1. `test_whisperx_real_transcribes_pt_clip_correctly` — transcreve clipe PT, asserta presença de palavras-chave.
2. `test_whisperx_real_transcribes_en_clip_correctly`
3. `test_whisperx_real_aligns_word_timestamps_within_tolerance`
4. `test_pyannote_real_diarizes_two_speaker_clip` — clipe com 2 falantes alternados, valida ≥ 2 SPEAKER labels.
5. `test_engine_factory_real_creates_working_engine`
6. `test_fallback_diarization_real_works_end_to_end`

**Total estimado para Gate 3**: ~25 unitários + 6 integração.

### Critérios de aceitação adicionais
- Cobertura adapters: ≥ 80% (algumas linhas defensivas exclusivas de hardware específico podem ficar de fora).
- Modelos baixados com sucesso pelo menos uma vez.
- Aceite dos termos do pyannote já feito (manual, fora dos testes).

### Não entra neste gate
- Pipeline de orquestração.
- Use cases.
- Telegram.

---

## Gate 4 — Pipeline (Chain of Responsibility)

### Objetivo
Costurar tudo em um **pipeline** orquestrado, com cada estágio testável isoladamente e o pipeline inteiro testável com adapters fakes.

### Escopo
- `Pipeline` (Chain of Responsibility).
- `Stage` interface base.
- `DownloadStage`, `SubtitleProbeStage`, `ConvertStage`, `TranscribeStage`, `AlignStage`, `DiarizeStage`, `RenderStage`, `DeliverStage`.
- `PipelineContext`.
- `MarkdownRenderer`.
- `RetentionPolicy` (apenas a parte que `DeliverStage` consulta; aplicação efetiva da política fica no Gate 6, mas a infraestrutura de leitura é estabelecida aqui).
- `JobLogger` (logs por job).
- `EventBus` simples (in-process pub/sub para eventos de progresso).
- Use case `ProcessVideoUseCase` (orquestra o pipeline para um job).
- Use case `RecoverInterruptedJobsUseCase`.

### Testes obrigatórios

**Unitários (~40 testes)**
1. `test_pipeline_executes_stages_in_order`
2. `test_pipeline_short_circuits_on_stage_error`
3. `test_pipeline_emits_completion_event_on_success`
4. `test_pipeline_emits_failure_event_on_error_with_traceback`
5. `test_pipeline_aggregates_progress_across_stages_using_weights`
6. `test_pipeline_supports_skipping_stages_when_subtitles_used`
7. `test_pipeline_context_carries_state_between_stages`
8. `test_download_stage_calls_video_source_and_stores_path_in_context`
9. `test_download_stage_validates_url_before_call`
10. `test_download_stage_validates_duration_within_limit`
11. `test_download_stage_validates_language_in_allowlist`
12. `test_download_stage_emits_warning_for_long_video_above_1h`
13. `test_download_stage_emits_auto_dub_message_when_alternate_tracks_present`
14. `test_subtitle_probe_stage_returns_manual_when_present`
15. `test_subtitle_probe_stage_falls_back_to_auto`
16. `test_subtitle_probe_stage_ignores_translated`
17. `test_subtitle_probe_stage_returns_unavailable_when_none`
18. `test_convert_stage_calls_audio_converter_with_config_bitrate`
19. `test_convert_stage_writes_to_processed_folder`
20. `test_convert_stage_raises_when_input_missing`
21. `test_transcribe_stage_uses_subtitle_when_available_and_skips_whisperx`
22. `test_transcribe_stage_uses_whisperx_when_no_subtitle`
23. `test_transcribe_stage_validates_speech_ratio_via_vad`
24. `test_transcribe_stage_rejects_when_speech_ratio_below_threshold`
25. `test_transcribe_stage_retries_with_smaller_model_on_oom`
26. `test_transcribe_stage_retry_uses_cpu_after_cuda_oom`
27. `test_transcribe_stage_propagates_error_when_retry_also_fails`
28. `test_align_stage_skipped_when_subtitle_used`
29. `test_align_stage_invoked_when_whisperx_used`
30. `test_diarize_stage_uses_fallback_engine`
31. `test_diarize_stage_crosses_subtitle_blocks_with_speaker_intervals_when_subtitle_used`
32. `test_render_stage_produces_md_with_full_header`
33. `test_render_stage_produces_md_with_speaker_summary`
34. `test_render_stage_groups_consecutive_same_speaker_segments_into_one_block`
35. `test_render_stage_writes_to_transcripts_folder_with_slug_filename`
36. `test_render_stage_handles_filename_collision_by_appending_suffix`
37. `test_render_stage_applies_speaker_map_when_provided`
38. `test_deliver_stage_sends_audio_and_md_via_message_gateway`
39. `test_deliver_stage_announces_subtitle_origin_when_applicable`
40. `test_deliver_stage_offers_redo_with_whisperx_button_when_auto_subtitle_used`

**Use cases (~10 testes)**
1. `test_process_video_use_case_creates_job_in_pending`
2. `test_process_video_use_case_marks_completed_on_success`
3. `test_process_video_use_case_marks_failed_on_pipeline_exception`
4. `test_process_video_use_case_persists_metadata_after_download`
5. `test_process_video_use_case_persists_speaker_count_after_diarization`
6. `test_recover_interrupted_jobs_use_case_marks_processing_as_failed`
7. `test_recover_interrupted_jobs_use_case_keeps_pending_in_queue`
8. `test_recover_interrupted_jobs_use_case_cleans_partial_files`
9. `test_recover_interrupted_jobs_use_case_returns_summary`
10. `test_recover_interrupted_jobs_use_case_idempotent_on_repeated_runs`

**Integração (`@pytest.mark.integration`, ~3 testes)**
1. `test_pipeline_with_real_ffmpeg_and_fake_engines_produces_md` — usa fixture de áudio, ffmpeg real, engines fake.
2. `test_pipeline_with_real_engines_and_fake_download_produces_md` — usa fixture pré-baixado de áudio em PT.
3. `test_render_md_matches_golden_file` — compara saída com snapshot versionado.

**Total estimado para Gate 4**: ~50 unitários + 3 integração.

### Critérios de aceitação adicionais
- Cobertura domain (Pipeline, Stages): 100%.
- Cobertura application (use cases): 100%.

### Não entra neste gate
- TelegramAdapter (próximo gate).
- Política FIFO de retenção (Gate 6).
- /rename, /redo (Gate 6).

---

## Gate 5 — TelegramAdapter

### Objetivo
Construir toda a camada de **interação Telegram**: handlers de comandos, mensagens livres com URL, autorização silenciosa, fila sequencial, mensagens de progresso editadas.

### Escopo
- Port `MessageGateway` (abstrai Telegram).
- Adapter `TelegramAdapter` (concreto, usando `python-telegram-bot`).
- `Authorization` (filtra `user_id`).
- `TelegramProgressReporter` (Observer, edita mensagem com throttle).
- Comandos como Command pattern: `StartCommand`, `HelpCommand`, `StatusCommand`, `LastCommand`, `ListCommand`, `ClearCacheCommand`, `ClearQueueCommand`, `LastErrorCommand`, `CancelCommand` (parcial, /redo e /rename completos no Gate 6).
- `UrlMessageHandler` (recebe link em mensagem livre, valida, enfileira).
- `SequentialQueueWorker` (consumer assíncrono, single-threaded).
- Use cases: `ListJobsUseCase`, `ResendLastUseCase`, `ClearCacheUseCase`, `ClearQueueUseCase`, `CancelJobUseCase`.

### Testes obrigatórios

**Unitários com mocks de `python-telegram-bot` (~35 testes)**
1. `test_authorization_allows_configured_user`
2. `test_authorization_silently_drops_other_users`
3. `test_authorization_does_not_log_dropped_attempts` (verifica que log fica vazio)
4. `test_url_message_handler_extracts_url_from_plain_text`
5. `test_url_message_handler_extracts_url_from_text_with_extra_words`
6. `test_url_message_handler_responds_when_no_url_found`
7. `test_url_message_handler_enqueues_job_when_url_valid`
8. `test_url_message_handler_detects_repeated_link_and_offers_redo_buttons`
9. `test_url_message_handler_detects_config_change_and_shows_diff`
10. `test_start_command_responds_with_greeting`
11. `test_help_command_lists_all_commands`
12. `test_status_command_when_idle`
13. `test_status_command_when_processing`
14. `test_status_command_shows_queue_size`
15. `test_last_command_resends_last_md`
16. `test_last_command_resends_audio_when_still_present`
17. `test_last_command_omits_audio_when_expired`
18. `test_list_command_shows_recent_jobs`
19. `test_list_command_marks_legacy_with_audio_expired`
20. `test_clearcache_command_removes_models_dir`
21. `test_clearqueue_command_clears_pending_only`
22. `test_clearqueue_command_does_not_cancel_running_job`
23. `test_lasterror_command_shows_traceback_when_present`
24. `test_lasterror_command_responds_when_no_recent_error`
25. `test_cancel_command_aborts_running_job`
26. `test_cancel_command_responds_when_nothing_to_cancel`
27. `test_progress_reporter_edits_single_message`
28. `test_progress_reporter_throttles_edits_to_one_per_second`
29. `test_progress_reporter_renders_marks_at_10_25_50_75_90`
30. `test_progress_reporter_renders_stage_names_in_portuguese`
31. `test_sequential_queue_worker_processes_one_at_a_time`
32. `test_sequential_queue_worker_continues_after_failure`
33. `test_sequential_queue_worker_respects_cancel_signal`
34. `test_sequential_queue_worker_persists_state_across_restarts`
35. `test_telegram_adapter_recovers_on_startup_and_notifies_user`

**Total estimado para Gate 5**: ~35 unitários.

### Critérios de aceitação adicionais
- Cobertura adapter Telegram: ≥ 85%.
- Cobertura use cases novos: 100%.

### Não entra neste gate
- /rename interativo (Gate 6).
- /redo com confirmação inline (Gate 6).
- Política FIFO efetivamente aplicada no momento do Deliver (Gate 6).

---

## Gate 6 — FIFO + /rename interativo + /redo com confirmação

### Objetivo
Fechar as funcionalidades restantes: política de retenção FIFO efetiva, comando `/rename` interativo, comando `/redo` com confirmação por botões inline, e tratamento completo de vídeos legados.

### Escopo
- `FilesystemArtifactStore` com `RetentionPolicy` aplicada de fato no `DeliverStage`.
- Política preserva `transcripts/*.md` indefinidamente; aplica FIFO em `downloads/`, `processed/`, `logs/` por job.
- Comando `/rename` interativo (Conversation handler).
- Comando `/redo` com confirmação obrigatória mostrando diff de configuração.
- `RenameSpeakersUseCase` que regenera o `.md`.
- `ReprocessVideoUseCase`.
- Tratamento de "rename em vídeo legado" (sem áudio): aviso + reenvio só do MD.
- Botão `[Refazer com WhisperX]` quando legenda auto-gerada foi usada.

### Testes obrigatórios

**Unitários (~40 testes)**
1. `test_retention_policy_keeps_md_indefinitely`
2. `test_retention_policy_evicts_audio_after_fifth_job`
3. `test_retention_policy_evicts_log_after_fifth_job`
4. `test_retention_policy_evicts_oldest_by_completion_timestamp`
5. `test_retention_policy_redo_replaces_in_place_keeping_position`
6. `test_retention_policy_rename_does_not_affect_position`
7. `test_retention_policy_failed_jobs_do_not_count_toward_limit`
8. `test_retention_policy_atomically_evicts_all_artifacts_of_a_job`
9. `test_retention_policy_handles_concurrent_eviction_safely`
10. `test_filesystem_artifact_store_lists_jobs_with_artifact_status`
11. `test_rename_command_starts_dialog_for_last_job`
12. `test_rename_command_warns_when_audio_expired`
13. `test_rename_command_iterates_through_each_speaker`
14. `test_rename_command_skips_speaker_when_user_sends_skip`
15. `test_rename_command_accepts_same_name_for_multiple_speakers`
16. `test_rename_command_cancel_aborts_dialog_without_saving`
17. `test_rename_command_persists_speaker_map_to_repository`
18. `test_rename_command_regenerates_md_with_new_names`
19. `test_rename_command_resends_md_after_regeneration`
20. `test_rename_command_resends_audio_when_present`
21. `test_rename_command_omits_audio_when_legacy`
22. `test_rename_use_case_idempotent_when_called_with_same_map`
23. `test_redo_command_aborts_when_video_id_unknown`
24. `test_redo_command_shows_confirmation_with_diff_when_config_changed`
25. `test_redo_command_shows_confirmation_without_diff_when_config_same`
26. `test_redo_command_processes_when_user_confirms`
27. `test_redo_command_does_nothing_when_user_cancels`
28. `test_reprocess_use_case_replaces_existing_artifacts`
29. `test_reprocess_use_case_keeps_position_in_fifo_queue`
30. `test_reprocess_use_case_records_new_config_in_job`
31. `test_subtitle_redo_with_whisperx_button_triggers_reprocessing`
32. `test_subtitle_redo_with_whisperx_button_keeps_speaker_map_if_present`
33. `test_legacy_job_displayed_in_list_with_marker`
34. `test_legacy_job_redo_redownloads_audio_from_scratch`
35. `test_url_message_handler_when_legacy_resends_md_only`
36. `test_url_message_handler_when_completed_resends_audio_too`
37. `test_md_regeneration_preserves_original_metadata_in_header`
38. `test_md_regeneration_updates_speakers_section`
39. `test_md_regeneration_keeps_url_in_header_for_audit_trail`
40. `test_speaker_map_repository_returns_default_after_redo`

**Total estimado para Gate 6**: ~40 unitários.

### Critérios de aceitação adicionais
- Cobertura geral: ≥ 95%.
- Cenário manual (smoke): mandar 6 vídeos, ver que o 1º perde os arquivos exceto o MD.

### Não entra neste gate
- Validação E2E real com vídeo do YouTube (Gate 7).
- Documentação final consolidada (Gate 7).

---

## Gate 7 — E2E com vídeo real + documentação final

### Objetivo
Validar **ponta-a-ponta** o sistema com o vídeo de referência `https://www.youtube.com/watch?v=j2p8p7cg0q8` no sandbox (com as ressalvas de bot-detection), revisar e finalizar toda a documentação, e produzir o pacote entregável.

### Escopo
- Teste E2E rodando o pipeline completo no sandbox:
  - Se o YouTube permitir o download direto, usa o vídeo inteiro.
  - Se bloquear, usa um clipe de 2 minutos do vídeo (obtido por meios alternativos: `manus-analyze-video` para extração de áudio ou um clipe equivalente conhecido em PT).
- Validação que o `.md` produzido tem o formato correto, idioma PT detectado, ≥ 1 falante diarizado, palavras-chave esperadas.
- Validação que o `.ogg` produzido é Opus mono ~32 kbps.
- Documentação revisada e completa (todos os 7 docs).
- Smoke checklist final (rodada manual de todos os comandos pelo usuário).
- Instruções específicas para o usuário rodar o E2E real do Telegram em sua máquina.

### Testes obrigatórios

**E2E (`@pytest.mark.e2e @pytest.mark.slow`, ~6 testes)**
1. `test_e2e_full_pipeline_with_reference_video` — rodar o pipeline com `j2p8p7cg0q8` (ou clipe), verificar artefatos.
2. `test_e2e_md_has_correct_header_for_reference_video`
3. `test_e2e_md_detects_portuguese`
4. `test_e2e_md_identifies_at_least_one_speaker`
5. `test_e2e_md_contains_known_keyword_from_video` (algo que sabemos que foi dito)
6. `test_e2e_audio_is_opus_mono_at_target_bitrate`

**Smoke manual** (executado pelo usuário com seu token):
1. `/start` → resposta de saudação.
2. Mandar link `j2p8p7cg0q8` → ver progresso completo, receber `.ogg` + `.md`.
3. `/last` → reenviar.
4. `/list` → mostrar o job.
5. `/rename` → renomear os 2 falantes.
6. `/redo <id>` → confirmar, ver reprocessamento.
7. `/cancel` durante novo processamento → ver abortamento.
8. `/status` durante e fora de processamento.
9. `/clearcache` → ver remoção de modelos.
10. `/lasterror` se houver algum.
11. Mandar 6 vídeos seguidos → confirmar que o 1º perde áudio mas mantém MD.
12. Reiniciar o bot → ver mensagem de recuperação.

### Critérios de aceitação adicionais
- Pipeline completo executou no sandbox sem erros (com mock do download se necessário).
- `.md` final passa nas asserções de conteúdo.
- Documentação revisada (sem TODOs, sem inconsistências entre os 7 docs).
- README atualizado com link para a release/tag.

### Não entra neste gate
- Nenhuma feature nova; apenas validação e documentação.

---

## Sumário de testes por gate

| Gate | Unit | Integration | E2E | Total |
|---:|---:|---:|---:|---:|
| 0 | 2 | 0 | 0 | 2 |
| 1 | ~72 | 0 | 0 | ~72 |
| 2 | ~30 | ~5 | 0 | ~35 |
| 3 | ~25 | ~6 | 0 | ~31 |
| 4 | ~50 | ~3 | 0 | ~53 |
| 5 | ~35 | 0 | 0 | ~35 |
| 6 | ~40 | 0 | 0 | ~40 |
| 7 | 0 | 0 | ~6 | ~6 |
| **Total** | **~254** | **~14** | **~6** | **~274** |

A esses números somam-se os **testes de regressão** gerados ao longo da execução, que aumentam o total mas não são previsíveis a priori.

---

## Avaliação incremental por gate

A avaliação é **incremental e automatizada**. Em cada gate:

1. Implemento o gate **inteiro** (todos os testes obrigatórios + correções com testes de regressão que surgirem).
2. Rodo a suíte completa (todos os gates anteriores + o atual) para garantir que **nenhum gate anterior regrediu**.
3. Verifico os critérios objetivos da §0.3 (testes verdes, cobertura, lint, mypy).
4. Se todos os critérios passam, produzo o **Gate Report** em `docs/gate-reports/gate-N-report.md` e **avanço imediatamente** para o próximo gate.
5. Se algum critério falha, fico no gate corrente, escrevo testes adicionais para reproduzir o problema, corrijo, e revalido. Não há limite de iterações dentro de um gate — o que importa é cumprir os critérios.
6. O usuário pode intervir a qualquer momento (pausar, redirecionar, mudar requisitos), mas o fluxo padrão é contínuo, sem necessidade de aprovação manual entre gates.

**Bugs descobertos pelo usuário após o fechamento de um gate** seguem o mesmo protocolo: novo teste de regressão antes da correção; correção entra na suíte permanentemente; Gate Report do gate afetado é atualizado com nota da correção e nova data.
