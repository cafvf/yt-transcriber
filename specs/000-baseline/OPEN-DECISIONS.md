# Baseline Open Decisions

Version: **1.0.1**
Status: **Approved**
Baseline date: **2026-08-15**

No blocking specification-level decision remains for approval of the `000-baseline` package.

The items below are deliberately deferred because they belong to requirement derivation, planning, or verification rather than to the product/domain specification itself.

## A. Requirement-derivation decisions

### RD-001 — Canonical transcript storage ports

Define the exact application contracts for loading, saving, versioning, and re-rendering canonical transcript evidence.

The specification already fixes semantic ownership: structured snapshot is canonical machine-readable evidence and Markdown is canonical human-readable rendering.

### RD-002 — Healthcheck secret-file permission reporting

Decide whether a security requirement should make `/healthcheck` report unsafe permissions for an explicitly configured secret-bearing environment file, and how to do so without unnecessarily disclosing sensitive filesystem paths.

### RD-003 — Compatibility aliases and deprecation details

For each misleading historical identifier selected for internal renaming, define which compatibility alias/mapping is required for environment variables, persisted values, commands, artifacts, or public documentation.


### RD-004 — Authorized operator versus Telegram delivery audience

The current code authorizes by Telegram `user_id` and responds to the incoming `chat_id`. During atomic security/transport derivation, define whether the private single-operator contract permits use from group/shared chats, requires private-chat-only interaction, or supports an explicit allowlisted chat/audience policy.

The requirement must prevent an authorized operator from unintentionally causing private transcripts, diagnostics, or artifacts to be disclosed to an unapproved audience. This is a requirement-derivation decision under SEC-AUTH, SEC-PRIVACY, ARCH-TRANSPORT, and FUNC-DELIVERY; the tree does not assume a policy before that decision is resolved.

## B. Planning decisions

### PD-001 — Architecture enforcement implementation

Choose the enforcement mechanism for approved dependency rules: custom AST/import test, `import-linter`, or another checker.

The specification requires executable enforcement; the tool choice belongs to the implementation plan.

### PD-002 — Concrete decomposition sequence

Choose the safest order for extracting application orchestration from `TelegramBotAdapter`, separating summarization policy, splitting persistence/search concerns, and correcting ports without producing a large-bang refactor.

The sequence must be derived after requirements and dependency analysis.

### PD-003 — Processing-fingerprint encoding

Choose canonical serialization/hash details and migration mechanics for the versioned processing fingerprint.

The specification fixes fingerprint semantics, not its encoding algorithm.

## C. Verification decisions

### VD-001 — Deselected test inventory — RESOLVED 2026-08-15

The 46 excluded tests were inventoried in `../002-requirements/EVIDENCE-INVENTORY.md`. All are integration-marked. The inventory classifies their evidence role and identifies the LocalFileStorage-only evidence as transitional because that generic abstraction is not part of the target architecture. Per-requirement gate placement remains an acceptance-criteria decision during atomic derivation.

### VD-002 — Real-host evidence schedule

Choose when during the correction sequence to execute systemd, backup/restore, rollback, interrupted-job, and `delivery_failed` rehearsals so that evidence corresponds to the code actually intended for baseline closure.

## Resolved during specification review

- Constitution ratified as **v1.0.0**.
- Canonical transcript representation defined.
- Job semantic state graph defined.
- `delivery_failed` retained as terminal.
- source-neutral internal taxonomy with compatibility preservation selected.
- processing fingerprint semantics defined.
- ASR application boundary defined.
- summarization application/infrastructure boundary defined.
- lifecycle persistence/search ownership separated conceptually.
- Telegram transport/application boundary defined.
- external settings compatibility policy defined.
- filesystem/hardware/provider policy removed from pure domain.
- interactive/systemd secret-loading policy defined.
- standard backups exclude reusable credentials and authentication cookies by default.
- empty speculative domain packages are not retained as architectural promises.
- generic `FileStorage` is not retained as a target application port without demonstrated use.

- VD-001 inventory completed; see `../002-requirements/EVIDENCE-INVENTORY.md`.
