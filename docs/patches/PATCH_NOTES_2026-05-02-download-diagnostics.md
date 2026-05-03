# Patch notes — 2026-05-02 — download diagnostics and concrete format fallback

## Context

A segunda correção ainda podia falhar em vídeos do YouTube nos quais o seletor padrão do `yt-dlp` retorna:

```text
Requested format is not available. Use --list-formats for a list of available formats
```

O traceback mostrou que, após falhar no seletor inicial, o código caía em um fallback com `format=None`. Esse fallback deixa o `yt-dlp` usar novamente o seletor padrão, portanto ele apenas repetia a mesma falha.

## Changes

- Removed the final `format=None` download fallback.
- Added explicit format listing using `listformats=True` and `simulate=True`, analogous to `yt-dlp -F`.
- Added concrete `format_id` retries based on the listed formats.
- Added conservative hardcoded YouTube candidates (`18`, `22`, `140`, `139`, `251`, `250`, `249`) when the extractor returns no usable format list.
- Added diagnostic error messages containing:
  - video id;
  - number of formats listed;
  - sample of available format ids/codecs;
  - last yt-dlp error;
  - recommended local diagnostic command.
- Added regression test ensuring the downloader no longer retries a final download with `format=None`.

## Validation performed in this environment

```bash
python -m compileall -q src tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src pytest -q tests/unit/infrastructure/youtube/test_yt_dlp_downloader.py
```

Result:

```text
39 passed
```

The full suite cannot be run in this sandbox because runtime dependencies such as `python-slugify`, `sqlalchemy`, and `python-telegram-bot` are not installed here. It should be run in the project virtual environment with:

```bash
uv run pytest
```
