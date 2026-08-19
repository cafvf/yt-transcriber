# PLAN-007 Requirements

Version: **1.0.0**
Status: **Approved for execution**

## REQ-P07-001 — Canonical media terminology
Internal domain/application code SHALL use `MediaMetadata`. `VideoMetadata` may remain only as a
tested and documented compatibility alias.

## REQ-P07-002 — Truthful audio-track semantics
`used_alternate_track` and `audio_track_was_dubbed` SHALL NOT remain canonical because they can
describe selection of the original track. Use an explicit typed state, preferably an enum such as
`ORIGINAL`, `DEFAULT`, `UNKNOWN`, and test original/alternate/failure cases.

## REQ-P07-003 — Typed language flow
Domain/application language state SHALL use existing `Language` and `LanguageSource` types. Raw
strings are restricted to external, persistence-compatibility and rendering boundaries.

## REQ-P07-004 — Canonical processing fingerprint
`processing_fingerprint` SHALL be canonical. `config_signature`, `transcription_signature()` and
equivalents may remain only at proven compatibility boundaries.

## REQ-P07-005 — Source-neutral duration
Internal policy SHALL use `max_media_duration_min`. `MAX_VIDEO_DURATION_MIN` may remain as an
external compatibility alias only with deterministic precedence and tests.

## REQ-P07-006 — Artifact policy typing
Existing typed artifact taxonomy SHALL be reused for domain policy instead of new free-form string
synonyms.

## REQ-P07-007 — Stable operational error contract
Cross-cutting errors SHALL expose stable code, category, retryability and safe message. Categories
include validation, policy_rejection, configuration, authentication, external_service,
resource_exhausted, cancelled, delivery and internal. Useful local provider exception hierarchies
may remain.

## REQ-P07-008 — Safe exception boundary
Provider exceptions SHALL be mapped or sanitized before user-visible/operational surfaces. Broad
catches are allowed only at deliberate containment boundaries and cannot convert failure to success.

## REQ-P07-009 — Complete application I/O boundaries
Where an existing port owns a capability, application code SHALL use it. Markdown rendering SHALL
reuse the canonical Markdown writer port instead of direct filesystem write/replace/unlink. No
generic filesystem abstraction is to be invented just to satisfy tests.

## REQ-P07-010 — Compatibility containment
Every retained compatibility mechanism SHALL satisfy `COMPATIBILITY.md`. Intentional likely
candidates include persisted `downloading` → `ACQUIRING`, legacy snapshot/schema readers, legacy DB
columns and possibly `MAX_VIDEO_DURATION_MIN`.

## REQ-P07-011 — Unified production configuration policy
Production onboarding SHALL use one private env file outside the repository, e.g.
`~/.config/yt-transcriber-bot/env`, with restrictive permissions. Project-root `.env` may remain a
developer convenience, not the production recommendation.

## REQ-P07-012 — Runtime prerequisite truth
Docs/healthcheck SHALL agree on Python, uv, ffmpeg, yt-dlp[default]/yt-dlp-ejs, Deno or supported
Node, Telegram credentials, HF token where pyannote requires it, and optional YouTube cookies. Do
not document a YouTube Data API key unless one is actually implemented.

## REQ-P07-013 — Runtime/development dependency separation
Development-only tools such as `pre-commit` SHOULD live in the development dependency group.

## REQ-P07-014 — Clean install and package smoke
Release SHALL prove package build, clean install without dev dependencies, import/CLI/config smoke
and health/preflight behavior outside the source checkout.

## REQ-P07-015 — README as product front door
README SHALL let a technically competent new operator install, configure, validate, start and update
the bot without reading all internal docs first.

## REQ-P07-016 — Healthcheck as installation acceptance gate
`/healthcheck` and/or a pre-Telegram CLI preflight SHALL be the formal installation acceptance
mechanism, with actionable diagnostics and no secret leakage.

## REQ-P07-017 — Documentation convergence
Current README/install/architecture/security/operations/readiness docs SHALL agree. Historical gate
reports SHALL remain historical.

## REQ-P07-018 — Release evidence against current HEAD
PLAN-006 evidence SHALL NOT be inherited as proof for source changes committed after its gate.
PLAN-007 release evidence SHALL name the exact candidate revision and rerun applicable gates.
