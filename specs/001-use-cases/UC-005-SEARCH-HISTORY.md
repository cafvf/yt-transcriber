# UC-005 — Search completed history

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **000-baseline v1.0.0**
Reference date: **2026-08-15**

## Goal

Search completed transcript history using the current textual search capability and bounded fallback.

## Primary actor

Authorized Operator

## Trigger

`/search <texto>`.

## Preconditions

- The operator is authorized.
- Query contains useful text.
- Search/history persistence is available.

## Main success scenario

1. Search is limited to completed operator-scoped history.
2. FTS5 is used when available; the approved deterministic bounded fallback is used otherwise.
3. Compact matches include identifying metadata and sanitized snippets.

## Alternative and exception flows

- No match is explicit.
- Semantic/vector search is never invoked in this baseline.

## Postconditions

- Canonical transcript evidence is unchanged; results refer only to completed in-scope Jobs.

## Security and privacy notes

- Query, index, matched content, summaries, and snippets are private; full queries/results are not unnecessarily logged.

## Current evidence references

- `docs/01-contrato-funcional.md`
- `src/yt_transcriber_bot/application/services/history_search.py`
- `src/yt_transcriber_bot/infrastructure/persistence/sqlalchemy/job_repository.py`

## Requirement dimensions to derive

- search scope
- index/fallback contract
- snippet sanitization
- search/index ownership boundaries
