# Atomic-Requirement Derivation Decisions

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **002-requirements v1.0.0**

These decisions resolve specification questions needed to make the atomic REQs testable. They were semantically reviewed with all Waves A-E before approval of `003-atomic-requirements v1.0.0`.

## DD-001 — Canonical transcript access contracts

Application semantics require purpose-specific capabilities for (a) loading/saving canonical structured transcript evidence and (b) rendering canonical Markdown from structured evidence plus aliases/provenance. Generic filesystem operations are not part of either contract. A durable Job/application record must carry an explicit canonical transcript reference; new behavior must not infer canonical ownership solely from a Markdown filename stem.

## DD-002 — Secret-file permissions belong to deployment verification, not mandatory in-process discovery

`/healthcheck` is not required to discover or expose the path/ownership of the systemd secret-bearing environment file. `OPS-SERVICE`/`SEC-FILES` verify restrictive ownership/permissions during host preflight/rehearsal. A future injected permission-status probe may contribute a sanitized health item without exposing the path.

## DD-003 — Compatibility boundary for taxonomy cleanup

Operator-facing commands/aliases, environment variables, persisted schema values and existing snapshot schema v1 remain compatible during baseline repair. Internal Python identifiers may be renamed atomically with their tests/callers and are not a public API. Persisted `downloading` remains readable as the compatibility representation of semantic `acquiring`; new internal logic uses source-neutral terminology. Historical `MAX_VIDEO_DURATION_MIN` remains accepted even if the internal setting becomes media-neutral.

## DD-004 — Telegram supported audience is private-chat-only

The private single-operator baseline supports the configured operator only in a Telegram private chat. A non-private/group/shared chat must not trigger private lookup, expensive processing, control mutation, transcript/artifact delivery or private diagnostics.

Unauthorized users remain silently ignored according to the frozen baseline. For the authorized operator in an unsupported non-private chat, the transport may either ignore the request or return a neutral non-private-data guidance message; the security contract does not require silence, but it forbids disclosure of private state or content.

This is deliberate hardening of an otherwise unspecified audience surface, not a multi-user feature.

## DD-005 — Language facts are never fabricated

Unknown source language remains unknown until supplied by the operator or observed by a supported source/ASR mechanism. No adapter may replace unknown language with English or replace an unsupported independently observed ASR language with an allowed language.

An explicit operator language request is a processing/decoding constraint and must be represented as such. It may override source metadata for the requested processing path, as in the frozen `/pt` and `/en` behavior, but it does not rewrite an independent language observation. When forced decoding yields no independent language observation, the transcript may record the requested language with provenance indicating a user-forced/requested constraint; confidence must be absent/unknown unless it actually measures that chosen language. When an independent observation exists, its language/confidence remains separately attributable.

Without an explicit user language request, an observed language outside the allowlist produces an explicit unsupported-language outcome.

## DD-006 — Unknown duration is not zero duration

A missing/unknown media duration is represented as unknown. It may be resolved by a later bounded and source-appropriate probe, but the system must establish that the configured maximum is not exceeded before expensive ASR/diarization. If it cannot establish that fact, the request is rejected explicitly. Unknown duration must never be converted to a synthetic zero solely to pass validation.

## DD-007 — Delivery routing is application context, not pure Job domain identity

Transport-specific routing such as Telegram `chat_id` must not remain an intrinsic field of the pure domain Job model. Sufficient restart/delivery routing may be persisted as application-owned request/delivery context associated with the Job. Historical database columns may remain readable during compatibility migration.
