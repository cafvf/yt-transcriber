# PLAN-001 Tasks — Security guardrails and baseline characterization

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **004-planning v1.0.0 (Approved / Frozen)**

## Execution rule

`TASK-P01-000` establishes the reproducible brownfield starting point before remediation. Each change-owner task then follows Red → Green → Refactor or records characterization when the approved behavior already satisfies its REQ. Security hardening must reuse the approved authorization, sanitization, privacy and containment policies rather than create parallel mechanisms.

## TASK-P01-000 — Capture clean execution baseline and frozen-interface characterization

**Primary REQ:** none; supports frozen requirements without closing them
**Supports:** Constitution II; `000-baseline/QUALITY.md`
**Task role:** **support / characterization**
**Dependencies:** **none beyond approved upstream specs**

### Scope

Before productive remediation changes, capture the exact starting revision and rerun the approved local quality/security baseline. Confirm that current command registration/help/config compatibility and the classified integration-test inventory are discoverable as characterization evidence. This task changes no product behavior.

**Integration note:** Every PLAN-001 change-owner task depends on this baseline. Later plans may reuse this evidence but must rerun affected gates after changes.

### Red / characterization

A dirty/unreproducible checkout, failing default quality gate, missing frozen-interface characterization, or unexplained difference from the approved executable baseline is a failing precondition that must be understood before behavior-changing work starts.

### Green

Fix only baseline-environment/test-harness problems required to reproduce the already-approved state; do not begin remediation behavior changes in this task. Record the exact revision, commands and outcomes.

### Refactor / convergence

Do not create a second source of policy truth. Remove temporary migration scaffolding when the owning closure task has replacement evidence.

### Completion evidence

- exact Git revision and clean/known working-tree state recorded;
- default pytest/ruff/format/mypy/compile checks recorded as applicable;
- secret scan/Gitleaks and `git diff --check` recorded;
- command/help/config compatibility characterization location recorded;
- 46 integration tests remain classified rather than silently treated as default-passed.

## TASK-P01-001 — Authorized operator and approved Telegram audience

**Primary REQ:** `REQ-SEC-001`
**Task role:** **change owner**
**Dependencies:** `TASK-P01-000`

### Implementation intent

The system SHALL authorize supported Telegram interaction only for the configured operator in the approved private-chat audience. Unauthorized users and unsupported non-private audiences SHALL not gain access to private lookup, processing, controls, diagnostics, transcripts or artifacts.

**Current brownfield focus:** Current adapter checks only user_id and sends to the incoming chat_id.

**Likely touchpoints:** Telegram adapter/entrypoint audience metadata and Telegram authorization/conformance tests.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Authorized private-chat requests from the configured operator reach the intended handler.
- AC-02: A different user_id cannot access processing, history, diagnostics, artifacts or controls.
- AC-03: The authorized operator in a non-private chat cannot trigger private lookup, expensive processing, control mutation, transcript/artifact delivery or private diagnostics; an implementation may ignore the request or return only neutral guidance.
- AC-04: Authorization and audience checks occur before expensive work, private-data lookup or state mutation.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- unit/contract tests for user+chat audience matrix
- Telegram adapter conformance test

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P01-002 — Provider-secret storage, privilege and incident lifecycle

**Primary REQ:** `REQ-SEC-002`
**Task role:** **change owner**
**Dependencies:** `TASK-P01-000`

### Implementation intent

Reusable provider credentials SHALL remain outside tracked content, use the narrowest practical privilege, be retained only as needed, and be revoked or rotated after uncontrolled exposure.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** AppSettings secret fields, `.env.example`, security scanners/hooks and secret-handling documentation; host secret-file permissions remain PLAN-006 evidence.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Tracked source, tests, examples and generated specifications contain only inert credential placeholders.
- AC-02: Runtime configuration does not require copying reusable credentials into tracked or world-readable files.
- AC-03: Where provider scopes exist, documented configuration uses the narrowest practical scope for the approved capability.
- AC-04: Diagnostics may report credential presence/validity without reproducing the secret value.
- AC-05: Documented exposure response requires revoke/rotate rather than masking or deletion alone.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- secret scanner and Gitleaks
- configuration/documentation conformance tests
- incident-response documentation review

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P01-003 — Private-data classification and minimization

**Primary REQ:** `REQ-SEC-003`
**Task role:** **change owner**
**Dependencies:** `TASK-P01-000`

### Implementation intent

The system SHALL treat media, transcripts, speaker aliases, queries/results, indexes, transport/provider identifiers, filesystem paths, logs, derivatives and backups as private data and SHALL disclose or persist only the minimum required for the approved operation.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Private-data classification across Job/transcript/artifact/search/log models and persistence/diagnostic boundaries.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Search, diagnostic and queue outputs omit transcript bodies unless the invoked operation explicitly requests transcript content.
- AC-02: Private filesystem paths and provider/transport identifiers are omitted when a stable opaque identifier or availability flag is sufficient.
- AC-03: Derived artifacts inherit private classification from their canonical source.
- AC-04: Sanitized data remains private by default and is not reclassified as public merely because secrets were removed.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- privacy-focused unit tests
- review checklist for new persistence/transport outputs

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P01-004 — Centralized sanitization of disclosure paths

**Primary REQ:** `REQ-SEC-004`
**Task role:** **change owner**
**Dependencies:** `TASK-P01-000`, `TASK-P01-002`, `TASK-P01-003`

### Implementation intent

All operator-facing diagnostics, persisted operational errors, audit records and transport error messages SHALL use one coherent sanitization policy before crossing their disclosure boundary.

**Current brownfield focus:** Current application sanitizer and execution-audit logger have duplicate policies.

**Likely touchpoints:** `application/services/sanitization.py`, Telegram send/edit paths, audit logging and `LastErrorService` persistence/rendering.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Tokens, cookies, authorization headers and API keys are redacted.
- AC-02: Provider request/response bodies, prompts and transcript payloads echoed by exceptions are omitted or safely summarized.
- AC-03: Application audit and last-error paths do not maintain divergent secret/payload sanitization rules.
- AC-04: If sanitization itself cannot safely process an error, the fallback is a generic safe message rather than raw original content.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- shared sanitizer contract tests
- regression cases for Telegram, audit and last-error paths

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P01-005 — Untrusted input containment

**Primary REQ:** `REQ-SEC-005`
**Task role:** **change owner**
**Dependencies:** `TASK-P01-000`, `TASK-P01-003`

### Implementation intent

Operator-supplied URLs, filenames, media metadata, transcript/provider text and other external content SHALL be treated as untrusted data and SHALL not control filesystem scope, application policy, credential selection or unintended command/execution behavior.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** YouTube URL parsing, Telegram incoming-media validation, filename/path handling, provider metadata/text and command parsing.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Filesystem-derived names and paths are normalized/contained before use.
- AC-02: External/provider text cannot select a different configured endpoint, credential source or file target merely by appearing in content.
- AC-03: Malformed or unsupported source/media metadata fails explicitly without escaping configured storage boundaries.
- AC-04: Content used in prompts, logs or rendering remains data and cannot inject application-level configuration or command execution.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- input-validation and path-containment tests
- malformed provider metadata regression tests
- prompt/render boundary tests

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P01-006 — Dependency, model and tokenizer trust

**Primary REQ:** `REQ-SEC-006`
**Task role:** **change owner**
**Dependencies:** `TASK-P01-000`

### Implementation intent

Runtime dependencies, ML models and tokenizers SHALL have explicit reproducibility/trust controls, and executable remote model/tokenizer code SHALL remain disabled by default and require deliberate security-relevant operator configuration.

**Current brownfield focus:** `transformers` is directly imported by summary tokenizer logic but is not a direct project dependency.

**Likely touchpoints:** `pyproject.toml`/`uv.lock`, tokenizer/model loading, `trust_remote_code`, ML/runtime dependency declaration and tests.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: `uv.lock` is the reproducible dependency authority for approved installs.
- AC-02: Directly imported runtime packages are declared directly, or an optional/fallback relationship is explicit and covered by tests.
- AC-03: `trust_remote_code` defaults to false and enabling it is surfaced as a security-relevant configuration.
- AC-04: Loading from a local cache does not bypass the configured model/tokenizer identity or remote-code/trust policy.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- dependency/configuration conformance tests
- locked-install CI
- security regression for remote-code default

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P01-007 — Filesystem containment and restrictive permissions

**Primary REQ:** `REQ-SEC-007`
**Task role:** **change owner**
**Dependencies:** `TASK-P01-000`, `TASK-P01-003`

### Implementation intent

Filesystem writes and destructive operations SHALL remain within explicitly owned/configured storage locations, and sensitive operational artifacts SHALL use restrictive permissions appropriate to their sensitivity.

**Current brownfield focus:** No specific brownfield defect is singled out; preserve approved behavior while establishing the required contract.

**Likely touchpoints:** Retention/cache/staging/snapshot filesystem operations plus safe owned-root/symlink/permission helpers or narrow capabilities.

### Red

Create or strengthen the lowest useful tests that express the frozen acceptance boundary:

- AC-01: Clear/delete operations resolve and validate their target against the approved owned root before deletion.
- AC-02: A symlink or resolved target that escapes the approved root is refused for destructive operations.
- AC-03: Backup, evidence and secret-bearing files created by operational helpers use restrictive permissions.
- AC-04: Canonical evidence belonging to unrelated Jobs is never removed by cache/media cleanup.

If all acceptance criteria are already satisfied, record characterization evidence instead of manufacturing an artificial failing test. For host-only or environment-only criteria, a failing preflight/rehearsal criterion is valid Red evidence; do not fabricate a unit-test substitute.

### Green

Implement the minimum coherent change required to satisfy the failing acceptance evidence while preserving all upstream frozen behavior and the current plan ownership boundary.

### Refactor / convergence

Remove temporary duplication introduced by the migration, keep one owner for the policy/capability, and run relevant architecture/contract/conformance checks before considering the task complete.

### Completion evidence

- path-containment and symlink-escape tests
- permission assertions in operational helpers
- host/staging rehearsal evidence

Also record the quality gates actually run and any environment-gated evidence deferred to PLAN-006.

## TASK-P01-008 — PLAN-001 exit-gate verification

**Primary REQ:** none; plan gate
**Task role:** **plan gate**
**Dependencies:** `TASK-P01-000`, `TASK-P01-001`, `TASK-P01-002`, `TASK-P01-003`, `TASK-P01-004`, `TASK-P01-005`, `TASK-P01-006`, `TASK-P01-007`

### Scope

Verify that every primary owner, support/foundation task and assurance task in PLAN-001 satisfies the frozen plan exit gate before work in the next plan is treated as implementation-ready. This task does not add product behavior or reimplement a failed criterion.

### Gate evidence

- Security/audience matrix is executable.
- Secret scanners/Gitleaks remain green.
- Sanitization regressions cover Telegram/audit/last-error disclosure paths.
- Untrusted-input regressions cover current URL/filename/provider-content surfaces.
- Destructive filesystem tests include path traversal and symlink escape.
- Dependency/model/tokenizer trust controls are explicit and testable.
- Existing operator command/config behavior remains characterized for downstream compatibility work.

### Completion rule

Record commands/evidence, unresolved environment limitations and any failed criterion. A failed criterion MUST be routed to the task that owns the missing behavior or evidence; the gate itself does not patch around the failure. Shared operational evidence may be referenced rather than rerun when it was captured on the same closure revision and remains valid.
