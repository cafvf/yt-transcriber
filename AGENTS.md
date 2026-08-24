# AGENTS

## Purpose

Private Telegram bot for YouTube transcription, diarization, auditable transcript artifacts, local history, and optional summarization through OpenAI-compatible backends.

Use this file for persistent Codex/agent instructions. Human-facing product and setup documentation remain in `README.md` and `docs/`; executable policy lives in `pyproject.toml`, `.pre-commit-config.yaml`, `.gitleaks.toml`, `scripts/security/`, and `.github/workflows/ci.yml`.

## Shared Codex Rules

- Prefer `uv` for repository commands; do not rely on global Python for checks.
- Keep `.venv/`, caches, local configs, cookies, tokens, local databases, logs, downloaded media, generated transcripts, model files, and runtime artifacts out of Git.
- Treat `uv.lock` as the project lockfile and keep it versioned.
- Before commit or push, run the local equivalent of affected CI jobs and remove ignored temporary artifacts.
- Never use `--no-verify` unless hooks are environmentally broken and equivalent checks were already run and reported.
- Preserve user changes. Do not revert unrelated dirty work.
- Keep diffs small, reversible, and aligned with the existing ports/adapters architecture.
- Security defaults are conservative: no real Telegram tokens, Hugging Face tokens, OpenAI-compatible keys, YouTube cookies, chat payloads, local DBs, or personal IDs in Git.

## Canonical References

- `README.md`: product overview and onboarding.
- `docs/01-contrato-funcional.md`: functional contract.
- `docs/02-arquitetura.md`: architecture, layers, ports, adapters, and directory structure.
- `docs/03-manual-de-uso.md`: operational behavior.
- `docs/04-manual-de-instalacao.md`: installation and local runtime requirements.
- `docs/08-seguranca-e-segredos.md`: secret handling policy.
- `pyproject.toml`: dependency groups, test markers, lint, formatting, and typing policy.
- `.pre-commit-config.yaml`, `.gitleaks.toml`, and `scripts/security/`: local security hooks.
- `.github/workflows/ci.yml`: CI contract.

## Work Areas

- Domain/application code: `src/yt_transcriber_bot/domain/` and `src/yt_transcriber_bot/application/`.
- Infrastructure adapters: `src/yt_transcriber_bot/infrastructure/`.
- Composition/runtime entrypoints: `src/yt_transcriber_bot/__main__.py` and `src/yt_transcriber_bot/composition_root.py`.
- Tests: `tests/`, with default selection excluding `integration`, `slow`, and `e2e`.
- Documentation: `docs/`; patch notes belong in `docs/patches/`, not the repository root.
- Runtime/local data: `data/`, `downloads/`, `processed/`, `transcripts/`, `logs/`, and `models/` stay ignored.

## Commands

- Bootstrap: `uv sync --dev`
- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Format check: `uv run ruff format --check .`
- Type audit/advisory baseline: `uv run mypy src`
- Tests: `uv run pytest`
- Full non-ML CI-equivalent audit: `uv run ruff check . && uv run ruff format --check . && uv run pytest`
- Hooks: `uv run pre-commit install`
- Hooks audit: `uv run pre-commit run --all-files`
- Secret scan: `python3 scripts/security/scan_secrets.py --all`
- Gitleaks full scan when installed: `python3 scripts/security/gitleaks_if_available.py --all`
- Config smoke: `uv run python scripts/config/print_effective_settings.py`

## Candidate Auto-fix Policy

- Mutating auto-fix or formatting commands are allowed only in an isolated candidate clone or worktree, before any validated bytes are copied into the real checkout.
- Before auto-fix, define an explicit task-owned path allowlist. Auto-fix commands must name only those authorized paths; never run broad auto-fix commands such as `ruff check --fix .` or repository-wide mutating formatting for a scoped change.
- For Ruff on authorized Python paths, prefer `uv run ruff check --fix --no-cache <authorized-paths>` followed by `uv run ruff format --no-cache <authorized-paths>`.
- Immediately after auto-fix, recompute tracked and untracked changed paths and fail closed if any path falls outside the allowlist.
- After candidate preparation, final quality gates are strict and non-mutating: use `ruff check` without `--fix`, `ruff format --check`, typing/tests/security checks, and verify the final changed-path set again.
- CI is always non-mutating: CI must detect lint/format violations and fail; it must not use `--fix` to rewrite submitted code.
- The real checkout receives only validated candidate bytes. Do not run blanket auto-fix on the real checkout to make a gate pass.

## Change Rules

- Follow spec-driven development: update `docs/` contracts for product/architecture changes before or alongside tests and code.
- Preserve the hexagonal boundary: domain/application code should not depend directly on Telegram, YouTube, ffmpeg, WhisperX, pyannote, SQLite, or LM Studio clients.
- Bugs in behavior should become regression tests unless the failure is purely environmental.
- Keep ML-heavy, network, real ffmpeg, Telegram, YouTube, and model-download checks behind `integration`, `slow`, or `e2e` markers.
- Do not import heavy ML libraries at module import time unless the existing lazy-loading contract already allows it.
- Keep `.env.example` placeholder-only. Real `.env`, cookies, DBs, media, transcripts, and logs stay local.
- Sanitize operational errors and logs before storing or sending them through Telegram.
- Avoid root-level patch notes; use `docs/patches/`.

## Validation

- Python/application change: run `uv run ruff check .` and `uv run pytest`; run `uv run mypy src` as an advisory type audit until the current baseline is fixed.
- Formatting/tooling change: run `uv run ruff format --check .` and `uv run pre-commit run --all-files`.
- Security change: run `python3 scripts/security/scan_secrets.py --all`; if `gitleaks` is installed, also run `python3 scripts/security/gitleaks_if_available.py --all`.
- Runtime integration involving Telegram, YouTube, ffmpeg, WhisperX, pyannote, or LM Studio requires explicit setup and should be reported separately when not run.
- Before commit/push, report what ran, what did not run, and any environmental gaps.

## Review Guidelines

- Prioritize leaks of tokens, cookies, local media, transcript text, SQLite state, and unsanitized exceptions.
- Check that docs, tests, CLI commands, and bot help text stay coherent.
- Verify that new adapters remain thin and that business decisions stay in application/domain code.
- Treat unbounded retries, queue growth, large model downloads, and Telegram rate limits as operational risks.
