# Patch Notes — 2026-05-17 — Phase 6 hardening

## Summary

Completed the Phase 6 technical-hardening lane that had been reserved as the next session after the Phase 5 performance pass.

This delivery closed three concrete risks:

1. subtitle-derived `/pt` Markdown could reach the user with mojibake;
2. CPU-only startup could fail when the real GPU detector was unavailable;
3. `/cancel` was documented as interrupting active work, but in practice it was mostly observed only between pipeline steps.

## What shipped

### 1. Subtitle mojibake hardening

Primary targets:
- `src/yt_transcriber_bot/infrastructure/text/normalization.py`
- `src/yt_transcriber_bot/infrastructure/youtube/yt_dlp_real_factory.py`
- `src/yt_transcriber_bot/infrastructure/youtube/yt_dlp_downloader.py`
- `src/yt_transcriber_bot/application/pipeline/steps.py`

Behavior changes:
- subtitle byte decoding now evaluates multiple candidate decodes instead of falling directly into a lossy replacement path;
- subtitle text is normalized before transcript creation;
- subtitle shortcut flow rejects suspicious residual corruption and falls back to WhisperX instead of persisting/sending a bad `.md`;
- the final rendered Markdown has a subtitle-integrity gate before delivery;
- subtitle retry backoff now honors cancellation.

Expected user-visible effect:
- `/pt` and other subtitle-first flows no longer send Markdown with common mojibake patterns when the text can be repaired conservatively;
- if the text remains suspicious, the bot abandons the subtitle shortcut and processes audio normally.

### 2. CPU fallback fix

Primary target:
- `src/yt_transcriber_bot/composition_root.py`

Behavior changes:
- the stub GPU detector now constructs a valid CPU `HardwareProfile` when the torch-backed detector is unavailable.

Expected user-visible effect:
- CPU-only startup no longer crashes because of an invalid fallback profile shape.

### 3. Active cancellation contract

Primary targets:
- `src/yt_transcriber_bot/application/cancellation.py`
- `src/yt_transcriber_bot/application/pipeline/context.py`
- `src/yt_transcriber_bot/application/pipeline/runner.py`
- long-running ports/adapters in audio, YouTube, transcription, and diarization

Behavior changes:
- the pipeline now propagates a shared cancellation event through the active work path;
- ffmpeg conversion and splitting can terminate active subprocess work and remove partial outputs;
- yt-dlp download can stop during active progress and clean partial downloads;
- WhisperX/pyannote wrappers now observe cancellation checkpoints around expensive phases;
- use-case cancellation during active transcription returns a `cancelled` result instead of waiting for the entire pipeline to finish.

Expected user-visible effect:
- `/cancel` now better matches the documented contract during active processing, not only between steps.

## Validation evidence

Incremental evidence gathered during implementation:
- targeted subtitle + cancellation + CPU fallback regression suites passed locally;
- Telegram adapter and queue cancellation suites passed locally.

Final evidence for this phase is captured in the implementation session report rather than reprinted here.

## Remaining roadmap after Phase 6

The technical-hardening lane continues with:
1. **Phase 7 — Durable queue and restart recovery**
2. **Phase 8 — YouTube inspection reuse and transcription hot path**
3. **Phase 9 — Operational overhead cleanup and documentation closure**

After those phases, the next product feature lane remains **Gate 8 — knowledge search / `/search`**.
