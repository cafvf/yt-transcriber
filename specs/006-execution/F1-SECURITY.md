# F1 — Security guardrails

Status: **Verified / Closed**
Date: **2026-08-15**
Task scope: `TASK-P01-001` through `TASK-P01-008`
Predecessor: F0 / `TASK-P01-000` verified green by the operator

## Purpose

F1 constrains the existing brownfield product before structural refactoring. It does not add a product feature and does not pre-empt the later architecture plans. The phase closes the current security obligations for Telegram audience, secret lifecycle, private-data minimization, disclosure sanitization, untrusted inputs, dependency/model/tokenizer trust, and destructive filesystem operations.

## Changes by task

### TASK-P01-001 / REQ-SEC-001 — Telegram audience

- Added one `TelegramAudiencePolicy` for the supported single-operator private-chat surface.
- Added a first PTB message guard that stops unsupported users/chats before command, text, media, lookup, queue or mutation handlers.
- Callback queries apply the same policy before acknowledgement and adapter dispatch.
- The existing adapter user-id check remains as defense in depth and compatibility behavior; it is not a second audience policy.

### TASK-P01-002 / REQ-SEC-002 — Provider-secret lifecycle

- Retained environment/local secret loading and inert tracked placeholders.
- Documented least-practical-scope provider credentials and revoke/rotate response after uncontrolled exposure.
- Standard backup policy now explicitly excludes reusable credentials, `.env`, systemd secret environment files and authentication cookies; these are reprovisioned separately.

Host secret-file ownership/mode evidence remains an operational closure obligation in PLAN-006 rather than being fabricated by a unit test here.

### TASK-P01-003 / REQ-SEC-003 — Private-data minimization

- Security policy explicitly classifies media, canonical and derived artifacts, search/index data, logs, transport/provider identifiers, paths and backups as private.
- Sanitized material remains private.
- `/lasterror` now reports canonical artifact availability without disclosing local artifact paths when the path itself is unnecessary.
- Structured audit/operational contexts replace filesystem paths with a private-path marker.

### TASK-P01-004 / REQ-SEC-004 — Shared sanitization

- `application.services.sanitization` is the single disclosure policy used by free-form diagnostics and structured audit/error fields.
- Execution audit no longer owns a duplicate secret/payload sanitizer.
- Configured provider secrets are available to the audit sanitizer through injected settings.
- Sanitizer failure returns a generic safe fallback rather than the raw input.
- Secret-bearing values use `[REDACTED]`; private payload content uses `[OMITTED]`.
- Payload bodies/prompts/transcripts remain omitted according to the approved disclosure contract.

### TASK-P01-005 / REQ-SEC-005 — Untrusted inputs

- Telegram filenames continue to be converted to opaque local names; a traversal-shaped filename is now a regression case.
- Filesystem targets are resolved and containment-checked before destructive actions.
- Existing URL/media/provider-text behavior remains data-driven and is protected by the existing plus new regressions; this phase does not introduce dynamic endpoint, credential or command selection from content.

### TASK-P01-006 / REQ-SEC-006 — Supply-chain/model/tokenizer trust

- `uv.lock` remains the install authority used by CI (`uv sync --locked --dev`).
- The existing direct `transformers` import is explicitly treated as an optional tokenizer capability: `auto` has a tested estimated fallback; explicit `hf` fails explicitly when unavailable.
- Local Hugging Face tokenizer loading remains `local_files_only=True`, preserves the configured model identity, and propagates the explicit `trust_remote_code` policy.
- `.env.example` now exposes `SUMMARY_TOKENIZER_TRUST_REMOTE_CODE=false` as the safe default and security-relevant opt-in.

No new ASR/model product backend is introduced.

### TASK-P01-007 / REQ-SEC-007 — Filesystem containment and permissions

- Added narrow owned-root filesystem safety primitives; no generic storage abstraction was introduced.
- Retention receives explicit volatile roots and refuses persisted traversal/symlink targets that resolve outside them.
- All observed `RetentionPolicy` call sites provide explicit owned roots or intentionally exercise invalid-root rejection in tests.
- Canonical Markdown remains outside the retention candidate set.
- Bot log, operational error log, execution audit, and generated operational-evidence files/directories use restrictive `0600`/`0700` modes on POSIX.

The helper is an interim brownfield security primitive. Later architecture plans remain responsible for moving external filesystem mechanisms behind the approved ports without weakening these invariants.

## PLAN-001 gate mapping

| Gate evidence | F1 evidence |
|---|---|
| Audience matrix executable | `tests/unit/infrastructure/telegram/test_audience.py`; `tests/conformance/test_security_guardrails.py` |
| Secret scanners green | project scanner + Gitleaks + pre-commit, locally verified |
| Telegram/audit/last-error sanitization | existing sanitization/last-error tests plus `test_security_sanitization.py` and `test_execution_audit_security.py` |
| Untrusted URL/filename/provider-content surfaces | existing URL/media/summarizer regressions plus `test_untrusted_media_filename.py` |
| Traversal and symlink destructive targets | `test_filesystem_safety.py`; `test_retention_policy.py` |
| Dependency/model/tokenizer trust | existing config tests plus `test_tokenizer_trust.py`; locked dependency authority retained |
| Frozen operator interface remains characterized | F0 conformance tests pass in the full gate |

## Local closure evidence

The operator ran the F1 targeted and full local gates on 2026-08-15.

Observed results after the final retention call-site correction:

```text
Retention regression subset: 14 passed
Default suite: 786 collected / 46 deselected / 740 passed
Branch-aware global coverage: 79%
Integration inventory: exactly 46 integration-marked tests
mypy: Success: no issues found in 102 source files
Ruff lint: passed
Ruff format check: passed
pre-commit local secret guard: passed
pre-commit Gitleaks hook: passed
project secret scanner: no obvious secrets found
Gitleaks: 30 commits scanned, no leaks found
compileall: passed
git diff --check: passed
```

Earlier focused F1 evidence on the same applied tree also recorded:

```text
Sanitization + audit regression: 25 passed
Targeted F1 security suite: 102 passed
```

The retention call-site audit confirmed the production composition root and all direct test constructions are explicit about `owned_roots`; the invalid-empty-root test remains an intentional rejection case.

This evidence satisfies `TASK-P01-008` and closes PLAN-001/F1.

## Deferred evidence

The following is intentionally deferred, not declared complete by helper tests:

- actual systemd secret-environment ownership/modes;
- real backup/restore permissions after transfer to another host/volume;
- host/staging operational rehearsal evidence.

These remain PLAN-006/F7 obligations and do not block PLAN-001 closure.

## Closure

F1 is **Verified / Closed**. Work may proceed to F2 / PLAN-002 only through the approved task dependency order.
