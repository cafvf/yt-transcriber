# Patch 2026-05-02 — ML dependencies in default install

## Context

The bot reached the diarization stage but failed at runtime with missing ML modules:

- `No module named 'whisperx'`
- `No module named 'torch'`

This happened because the ML/audio stack was declared as an optional extra (`ml`). A plain `uv sync` therefore produced an environment capable of running the lightweight tests and Telegram shell, but not the complete transcription/diarization workflow.

## Changes

- Moved the runtime ML/audio stack to the main dependencies in `pyproject.toml`:
  - `torch`
  - `torchaudio`
  - `whisperx`
  - `pyannote.audio`
  - `faster-whisper`
- Kept the `ml` extra as an empty compatibility extra so old instructions using `uv sync --extra ml` do not fail.
- Updated `uv.lock` package metadata so `uv sync` installs the ML stack by default.
- Added startup preflight checks for `torch`, `whisperx`, and `pyannote.audio` using `importlib.util.find_spec`, avoiding a late failure during diarization.
- Updated README and installation/troubleshooting docs.

## User action after upgrading

```bash
cd /home/cafvf/git/yt-transcriber
uv sync
uv run python - <<'PY'
import importlib.util
for m in ["torch", "whisperx", "pyannote.audio"]:
    print(m, "OK" if importlib.util.find_spec(m) else "FALTANDO")
PY
```

Then restart the Telegram bot.

