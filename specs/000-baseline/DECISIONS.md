# Baseline Decisions

Version: **1.0.1**
Status: **Approved record**
Baseline date: **2026-08-15**

## D-001 — Stabilize before feature expansion

New product functionality is paused until current architectural, domain, quality, security, and documentation problems are resolved.

## D-002 — Keep TDD and add SDD upstream

TDD remains the implementation discipline. SDD provides the normative layer before implementation.

## D-003 — Specifications before use cases and requirements

The current phase creates Constitution and baseline specifications only. Detailed use cases, atomic requirements, plans, and tasks are deferred.

## D-004 — Brownfield evidence is not automatically normative

Code, tests, docs, historical records, and observed behavior reconstruct the baseline. Observed behavior is classified before becoming normative.

## D-005 — Architecture reconvergence precedes features

Known violations of the intended hexagonal architecture are first-class baseline debt.

## D-006 — Credential security is constitutional

Bot tokens, Hugging Face tokens, cookies, and future provider credentials are protected information and belong at infrastructure/composition boundaries.

## D-007 — Coverage is risk evidence, not a target by itself

Contract, invariant, architecture, regression, integration, and operational evidence take precedence over arbitrary percentage targets.

## D-008 — Historical records remain historical

Gate reports, old validation evidence, and patch notes are not rewritten to reflect later architecture or terminology.

## D-009 — Feature roadmap is paused, not discarded

Semantic search, backend-neutral multilingual ASR, translation, advanced redo, and knowledge-system integration remain future candidates and are revisited only after baseline closure.

## D-010 — Constitution v1.0.0 is ratified

The project Constitution is normative from 2026-08-15. Brownfield evidence remains evidence, but future conflicts are classified under the Constitution rather than automatically resolved in favor of code.

## D-011 — Development/support surfaces are disclosure boundaries

Git/GitHub, CI output, copied terminal diagnostics, screenshots, support chats, and AI-assistant prompts must not receive real provider credentials or unsanitized private payloads.

## D-012 — Structured transcript snapshot is canonical machine-readable evidence

The domain `Transcript` is the canonical logical representation. Its versioned structured snapshot is the canonical persisted machine-readable representation; Markdown is the canonical human-readable rendering. Structured consumers must not reconstruct transcript semantics by parsing Markdown when structured evidence exists.

## D-013 — Baseline Job lifecycle has an explicit transition graph

The baseline lifecycle is defined in `DOMAIN.md`, including the YouTube subtitle shortcut, failure/cancellation outcomes, restart reconciliation, and delivery outcomes. Reassigning the same status is not a semantic transition.

## D-014 — `delivery_failed` remains terminal in the baseline

The current baseline does not reopen a `delivery_failed` Job. Any future resend/re-delivery capability requires a separately specified use case.

## D-015 — Taxonomy is corrected internally while external compatibility is preserved

Misleading internal video/YouTube names should be corrected when the concept is generic media. Existing environment variables, persisted schema names, commands, and other operator-facing compatibility surfaces are not broken during baseline repair without an explicit migration requirement.

## D-016 — Processing fingerprint and provenance are distinct

One versioned processing-fingerprint concept identifies materially equivalent transcript-producing configuration. Provenance may record additional actual runtime/backend/fallback facts. Credentials and unrelated operational settings never enter the fingerprint.

## D-017 — ASR ports express application capabilities, not Whisper runtime APIs

The generic transcription contract must not be defined by provider-specific compute modes or other CTranslate2/WhisperX details. Actual backend/model/runtime facts remain available for provenance.

## D-018 — Summarization policy belongs to application; provider transport belongs to infrastructure

Transcript preparation, chunking/orchestration, prompt semantics, reduction/output policy, and derived-artifact semantics are application concerns. OpenAI-compatible HTTP/auth/provider translation and concrete external tokenizer integration are infrastructure concerns.

## D-019 — Lifecycle persistence, transcript storage, indexing, and search are separate semantic responsibilities

A concrete adapter may temporarily implement more than one explicit interface, but lifecycle persistence must not hide search-index/file-loading side effects inside the Job repository contract.

## D-020 — Telegram remains a transport adapter, not a parallel application layer

Telegram-specific parsing, presentation, authorization boundary checks, inline interaction state, and delivery mechanics remain infrastructure. Job/submission/cancellation/search/rename/summary/export/retention and delivery-result semantics belong to application behavior.

## D-021 — External settings compatibility is preserved while internal settings may be reorganized

Internal configuration may be grouped by concern and renamed truthfully. Existing operator-facing environment variables remain accepted during the baseline unless an explicit deprecation/migration is approved.

## D-022 — Filesystem/hardware/provider compatibility policy does not belong in pure domain value objects

Intrinsic value validation remains in domain. Filesystem existence, VRAM/model fallback, hardware compatibility, and backend-specific model policy belong to application/runtime/infrastructure boundaries.

## D-023 — Interactive and systemd secret loading may use different mechanisms under identical invariants

Interactive execution may use the process environment or another explicit local secret source outside tracked repository content. systemd uses an operator-managed protected environment file. Repository-root `.env` is compatibility-only for secrets, not the preferred long-lived secret store.

## D-024 — Standard backups exclude reusable credentials by default

Normal backup/restore data excludes bot/API tokens and secret-bearing environment files; credentials are reprovisioned separately. Any deliberate credential-inclusive disaster-recovery bundle is a distinct higher-sensitivity artifact.

## D-025 — Empty domain packages are not architectural commitments

Empty packages such as `domain/events` and `domain/pipeline` do not reserve future architecture. If they have no current contract/use, they should be removed during cleanup and recreated only when a specification requires them.

## D-026 — The generic `FileStorage` abstraction is not a target baseline port

The current generic filesystem port/adapter is constructed and exposed by composition but has no demonstrated main-runtime consumer. It should be removed during cleanup unless implementation analysis reveals a real application capability that requires it. Specific storage capabilities should use purpose-specific contracts.

## D-027 — Baseline specification package approved

The `000-baseline` specification package is approved as **v1.0.0** on 2026-08-15. The promotion is semantic-preserving and closes the Constitution/baseline-specification stage. Current-system use-case modeling becomes the next authorized artifact class.

## Editorial note — v1.0.1

Corrected the duplicate identifier on the baseline-approval decision from `D-023` to `D-027`. No decision semantics changed.
