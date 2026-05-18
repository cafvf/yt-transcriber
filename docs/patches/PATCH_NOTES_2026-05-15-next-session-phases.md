# Patch Notes — 2026-05-15 — Next-session phases

> **Status update (2026-05-17):** Phase 6 from this roadmap was completed in
> `docs/patches/PATCH_NOTES_2026-05-17-phase6-hardening.md`. The next entry
> point for this roadmap is now **Phase 7**.

## Summary

Documented the next working session as a staged technical hardening roadmap that follows the completed Phase 5 performance pass without discarding the already documented product next steps.

The working plan source is:

- `.omx/plans/plan-bottleneck-remediation-20260515.md`

## New phases for the next session

### Phase 6 — Startup and cancellation hardening

Focus:
- fix the CPU-only fallback path when `torch` is unavailable;
- make `/cancel` match the documented contract during active download/conversion/transcription/diarization work;
- clean partial artifacts created by canceled runs.

Primary targets:
- `src/yt_transcriber_bot/composition_root.py`
- `src/yt_transcriber_bot/application/pipeline/runner.py`
- long-running ports/adapters in audio, YouTube, transcription, and diarization

Expected evidence:
- regression test for the no-`torch` startup path;
- cancellation tests proving active work is interrupted instead of only being noticed between steps.

### Phase 7 — Durable queue and restart recovery

Focus:
- replace the in-memory-only pending queue with persistent enqueue/recovery behavior aligned with the SQLite queue contract;
- persist jobs at enqueue time;
- recover `pending` jobs and reconcile stale `processing` jobs after restart.

Primary targets:
- `src/yt_transcriber_bot/infrastructure/persistence/sqlalchemy/`
- `src/yt_transcriber_bot/infrastructure/telegram/job_queue.py`
- `src/yt_transcriber_bot/infrastructure/telegram/bot_adapter.py`
- startup wiring in `src/yt_transcriber_bot/__main__.py` / composition root

Expected evidence:
- tests for restart recovery, FIFO ordering, `/queue`, `/status`, `/clearqueue`, and `/cancelall` against durable state.

### Phase 8 — YouTube inspection reuse and transcription hot path

Focus:
- collapse repeated yt-dlp metadata/subtitle inspection into one reusable preparation result;
- reduce WhisperX alignment reload overhead;
- replace quadratic speaker assignment with a linear/sweep-based approach.

Primary targets:
- `src/yt_transcriber_bot/application/pipeline/steps.py`
- `src/yt_transcriber_bot/application/pipeline/context.py`
- `src/yt_transcriber_bot/infrastructure/youtube/yt_dlp_downloader.py`
- `src/yt_transcriber_bot/infrastructure/transcription/whisperx_real_backend.py`
- `src/yt_transcriber_bot/application/ports/diarization_engine.py`

Expected evidence:
- tests proving subtitle-first reuse behavior;
- regression fixtures showing speaker-label equivalence after the algorithm change;
- bounded caching for alignment/model hot paths.

### Phase 9 — Operational overhead cleanup and documentation closure

Focus:
- reduce maintenance-path overhead in retention and `/lasterror`;
- move `/clearcache` filesystem traversal off the event loop;
- finish doc alignment and regression coverage for the new runtime behavior.

Primary targets:
- `src/yt_transcriber_bot/application/services/retention_policy.py`
- `src/yt_transcriber_bot/application/services/last_error.py`
- `src/yt_transcriber_bot/infrastructure/telegram/bot_adapter.py`
- `docs/01-contrato-funcional.md`
- `docs/02-arquitetura.md`

Expected evidence:
- bounded-read or indexed-path behavior for `/lasterror`;
- retention overflow queries that avoid full-history scans;
- updated docs and tests matching the final queue/cancel/runtime contract.

## Relation to the already documented next steps

These phases are a **technical stabilization lane** for the next session. They do **not** replace the already documented functional roadmap.

After Phases 6–9, the product roadmap remains:

1. **Gate 8 — Busca e recuperação de conhecimento** (`/search <texto>` com base preparada para busca semântica).
2. `/text [n]`.
3. Upload de áudio pelo Telegram.
4. Backend alternativo de ASR e suporte multilíngue ampliado.
5. `/translate`.
6. Melhorias no `/redo`.
7. Integração com Obsidian/Notion.

## Session handoff note

If the next session starts from documentation only, continue with:

1. Phase 7
2. Phase 8
3. Phase 9
4. then resume the previously documented Gate 8 product work
