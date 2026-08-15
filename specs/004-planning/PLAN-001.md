# PLAN-001 — Security guardrails and baseline characterization

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **003-atomic-requirements v1.0.0**
Prerequisite plans: **003 atomic requirements approved/frozen**
Approved: **2026-08-15**

## Goal

Establish reusable security guardrails and characterization evidence that every later refactor must preserve: approved Telegram audience, private-data handling, one disclosure-sanitization policy, untrusted-input containment, supply-chain trust controls, filesystem containment, and provider-secret lifecycle.

This plan establishes policy, executable guardrails and safe primitives. It does **not** own provider-secret architectural migration, external-service adapter seams, domain/data migration, or application workflow decomposition; those are explicit handoffs to later plans.

## Primary requirement scope

- `REQ-SEC-001` — Authorized operator and approved Telegram audience
- `REQ-SEC-002` — Provider-secret storage, privilege and incident lifecycle
- `REQ-SEC-003` — Private-data classification and minimization
- `REQ-SEC-004` — Centralized sanitization of disclosure paths
- `REQ-SEC-005` — Untrusted input containment
- `REQ-SEC-006` — Dependency, model and tokenizer trust
- `REQ-SEC-007` — Filesystem containment and restrictive permissions

## Implementation approach

1. Add/strengthen characterization and security-contract evidence before behavior-changing hardening.
2. Introduce private-chat audience information at the Telegram boundary and enforce the approved audience before private lookup, work admission, control mutation, diagnostics or artifact disclosure.
3. Converge operator-facing error/audit sanitization onto one policy without weakening existing redaction or treating sanitization as declassification.
4. Treat URLs, filenames, provider metadata, transcript/provider text and similar inputs as untrusted data; keep them from selecting credentials, escaping owned filesystem scope or becoming unintended commands/execution controls.
5. Make direct runtime dependency and tokenizer/model trust assumptions explicit, including deliberate handling of the current implicit `transformers` availability and `trust_remote_code` policy.
6. Establish owned-root/symlink-safe containment checks and restrictive-permission expectations for sensitive files without introducing a generic filesystem abstraction.
7. Preserve current commands, aliases and configuration names while later data/schema compatibility remains owned by PLAN-002.

## Ownership boundary and handoff

PLAN-001 owns **security policy and reusable guardrails**. It hands off:

- provider-secret application/infrastructure boundary enforcement and external-service disclosure seams to PLAN-003;
- persisted-data compatibility and source/domain truth to PLAN-002;
- operational workflows that consume filesystem/log/probe capabilities to PLAN-004;
- end-to-end security acceptance to PLAN-005;
- host permission/secret-file and operational evidence to PLAN-006.

Later plans must reuse these guardrails rather than create parallel sanitizers, path-containment policies or authorization semantics.

## Migration and compatibility constraints

- Do not move provider credentials through application ports as an interim shortcut; the structural secret-boundary migration is owned by PLAN-003.
- Do not broaden authorization to multiple users/chats.
- Do not turn the security pass into a generic sandboxing framework unrelated to current capabilities.
- Do not perform persistence/schema migration in this plan merely to satisfy security tests.

## Exit gate

- Security/audience matrix is executable.
- Secret scanners/Gitleaks remain green.
- Sanitization regressions cover Telegram/audit/last-error disclosure paths.
- Untrusted-input regressions cover current URL/filename/provider-content surfaces.
- Destructive filesystem tests include path traversal and symlink escape.
- Dependency/model/tokenizer trust controls are explicit and testable.
- Existing operator command/config behavior remains characterized for downstream compatibility work.

## Not tasks

The numbered approach above defines migration order and design constraints, not a task checklist. Concrete files, red tests, implementation increments, commits and task ownership are defined in `../005-tasks/`.
