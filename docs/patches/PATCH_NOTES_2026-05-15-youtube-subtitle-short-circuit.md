# Patch Notes — 2026-05-15 — YouTube subtitle short-circuit

## Goal

Prevent the pipeline from downloading/converting audio or invoking audio-dependent ML steps after a YouTube subtitle track has already been selected and materialized successfully.

## What changed

- `TryYouTubeSubtitlesStep` now materializes `ctx.transcript` directly from the fetched subtitle segments.
- `DownloadAudioStep`, `ConvertAudioStep`, and `DiarizeStep` now skip when `ctx.youtube_subtitle_used` is already true.
- Regression coverage now asserts that the subtitle path:
  - finishes successfully,
  - leaves `audio_path` empty,
  - skips conversion, transcription, and diarization,
  - reports skipped downstream steps through progress updates,
  - still renders Markdown with the YouTube subtitle source and speaker labels.

## Validation

- Unit regression suite for `TranscribeVideoUseCase` passes with the new short-circuit assertions.
- Live downloader validation was re-run on 2026-05-15 against `dQw4w9WgXcQ`.
  - `fetch_metadata` and `list_subtitles` still work.
  - direct subtitle fetch is currently blocked by `HTTP 429 Too Many Requests` in this environment.
  - Because of that upstream rate limit, the live end-to-end subtitle-success path could not be re-proven in this session even though the local regression path is green.

## Follow-up

- If YouTube subtitle fetch 429s continue in real usage, treat that as a separate downloader hardening issue rather than a regression in the short-circuit logic.
