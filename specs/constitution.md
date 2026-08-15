# YT Transcriber Constitution

Version: **1.0.0**
Status: **Ratified**
Prepared: **2026-08-15**
Ratified: **2026-08-15**

## Purpose

This Constitution defines the durable engineering principles and governance rules for `yt-transcriber`.

It is stricter and more stable than individual feature specifications. A specification, ADR, implementation decision, or task may refine these principles, but may not silently contradict them.

Because the repository is brownfield, this Constitution also defines how existing behavior is converted into normative specifications without treating every historical implementation detail as intentional product design.

## Principle I — Specification is normative intent

The Constitution is the highest normative engineering artifact. Approved specifications define what the system is expected to do and why. ADRs explain important design decisions and may define how an approved specification is satisfied, but they do not override the Constitution or approved product contract.

Tests, code, logs, historical documents, and observed runtime behavior are evidence. They are essential for reconstructing the current baseline, but an observed behavior is not automatically a requirement. It may be a defect, obsolete rule, implementation accident, or technical debt.

After a specification is approved, a deliberate behavior change must be preceded by or accompanied by a corresponding specification change.

Brownfield conflicts are classified before correction:

- specification intended, code deviates → implementation defect;
- code behavior intended but specification incomplete → specification gap;
- behavior exists accidentally and is not desired → baseline deviation;
- requirement changed intentionally → specification changes before or alongside tests and implementation.

## Principle II — TDD is behavior-, contract-, and invariant-driven

Changes to observable behavior follow Red → Green → Refactor.

A defect that violates approved behavior must first gain a regression test unless the failure is purely environmental or cannot be reproduced at the applicable test layer. Refactoring must be protected by sufficient characterization tests before structural changes.

Tests primarily protect externally observable behavior, domain invariants, state transitions, port/adapter contracts, persistence/artifact contracts, architectural rules, security properties, and operational semantics.

Private methods and internal details do not require direct tests merely to increase coverage. Coverage is an engineering signal, not an end in itself.

## Principle III — Hexagonal boundaries are enforceable constraints

The architecture follows Ports & Adapters / Hexagonal Architecture.

```text
domain
  may depend on: stdlib + domain

application
  may depend on: stdlib + domain + application

infrastructure
  may depend on: stdlib + domain + application + infrastructure

composition/runtime
  may depend on: all layers
```

Domain rules must remain independent from Telegram, YouTube, SQLite, filesystem state, ffmpeg, WhisperX, pyannote, LM Studio, environment variables, and similar external mechanisms.

Application code orchestrates business behavior and depends on ports or application abstractions for external capabilities. It must not depend on concrete infrastructure adapters.

Infrastructure implements ports. Composition connects implementations to application abstractions.

Architectural dependency rules must eventually be checked automatically. A dependency violation is a defect even when functional tests pass.

## Principle IV — Domain integrity and truthful taxonomy

Names, entities, value objects, states, and interfaces must describe the real domain rather than preserve obsolete assumptions from earlier product stages.

Generic media concepts must not remain named as video or YouTube solely because the original product accepted only YouTube. Conversely, genuinely source-specific concepts must not be generalized without reason.

Domain state machines must have explicit valid states, terminal states, and transition rules. Impossible transitions must not be accepted merely because the implementation does not reject them.

Domain objects should contain domain knowledge, not filesystem state, provider credentials, concrete ML runtime mechanisms, or transport payloads.

The project avoids speculative abstractions. New abstractions must solve a demonstrated contract, architectural boundary, or approved extensibility need.

## Principle V — Information security is a first-class design constraint

The system processes private credentials and private content. Information security is therefore a constitutional concern, not merely an operational checklist.

Secrets include, at minimum, bot tokens, API tokens, Hugging Face tokens, cookies, authorization headers, private identifiers where exposure would create risk, and any future credential granting access to an external service.

Secrets must never be committed to version control, embedded in examples, fixtures, snapshots, generated documentation, issues, pull requests, logs, transcript artifacts, or source code. Examples use inert placeholders only.

Credentials belong at the system boundary. Provider-specific secrets are loaded and consumed by infrastructure/composition components that require them and must not be transported through domain entities or generic application contracts.

The system follows least privilege. Where a provider supports scoped tokens, the narrowest practical scope is preferred. A bot token or API token is treated as a bearer credential capable of exercising the permissions granted to that identity; possession of the token is sufficient reason to treat disclosure as security-relevant.

The Git repository and all collaboration/support surfaces are disclosure boundaries. Real credentials must not be pasted into commit messages, issues, pull requests, code-review comments, terminal transcripts shared for support, screenshots, prompts sent to AI assistants, or other third-party analysis tools. When diagnostic context is necessary, secrets and private payloads are removed or replaced with inert placeholders before the material leaves the trusted runtime environment. Repository visibility must never be relied upon as a secret-storage control.

Credential exposure is treated as compromise. A token that appears in a commit, log, chat, issue, screenshot, diagnostic dump, or other uncontrolled location must be revoked or rotated; deleting or masking the visible copy alone is insufficient.

Sensitive values must not be retained longer than required. Diagnostics should identify configuration presence or validity without reproducing secret values.

## Principle VI — Private data and derived artifacts remain protected information

Audio, video, transcripts, summaries, indexes, SQLite databases, logs, recovery metadata, backups, cookies, and generated artifacts may contain private or identifying information even when they do not contain credentials.

Sanitization reduces disclosure risk but does not make an artifact public. Sanitized logs can still contain filenames, paths, model names, job metadata, identifiers, timing, or contextual information and remain private by default.

Data minimization applies to logs and external messages: record only information necessary to operate, diagnose, recover, and audit the system.

Backups inherit the sensitivity of the data they contain and must be protected with appropriate permissions and, where practical, encrypted or access-controlled storage.

Retention and deletion policies must distinguish disposable media, operational logs, canonical transcript artifacts, snapshots required for reproducibility, and derived indexes. Deletion must not silently break a documented capability.

## Principle VII — Security controls are layered and testable

No single mechanism is sufficient protection.

Defense in depth includes, as applicable:

- `.gitignore` and local file placement rules;
- placeholder-only example configuration;
- pre-commit secret checks;
- local secret scanning;
- Gitleaks when available;
- CI security checks;
- centralized sanitization;
- private single-user authorization;
- filesystem permission controls;
- review of newly introduced external paths;
- regression tests for discovered leakage paths.

Security-sensitive behavior must have executable checks whenever practical. New integrations or error/reporting paths require review for secret leakage, private payload leakage, authorization bypass, unsafe logging, and inappropriate persistence.

Security scanners reduce risk but do not prove absence of secrets.

## Principle VIII — Reproducibility and provenance are preserved

A generated result must retain enough metadata to understand its origin and the significant processing choices that produced it.

Where material to output, provenance includes input/source identity, language, ASR backend/model, diarization backend where applicable, result-significant configuration, artifact type, and derivation relationship.

Derived artifacts do not silently replace the canonical transcript or source evidence.

The project maintains one canonical mechanism for identifying result-significant processing configuration. Duplicate signatures or overlapping fingerprints must be reconciled.

## Principle IX — Failure, cancellation, delivery, and recovery semantics are explicit

The system must distinguish normal completion, processing failure, cancellation, delivery failure, restart reconciliation, and any future recoverable states.

It must not promise resumability, durability, retry behavior, or exactly-once semantics that it does not implement.

Restart semantics must explicitly define what is requeued, what fails, what remains recoverable, and what requires operator action.

Operational readiness is not proven solely by unit tests when behavior depends on the host environment. systemd lifecycle, backup/restore, rollback, and controlled recovery require reproducible real-host or representative staging evidence when declared supported.

## Principle X — Evolution is controlled, reversible, and complexity-conscious

Changes should be small enough to review, test, and revert safely.

Refactoring must not alter product behavior incidentally. When a structural change reveals undesirable behavior, that behavior is classified and specified rather than silently fixed.

Breaking changes require explicit specification and, when persistent data or external interfaces are affected, a migration strategy.

Before expanding an area with new functionality, known constitutional violations in that area should be resolved or explicitly accepted as temporary exceptions.

The project prefers the simplest design that satisfies current approved requirements and already-approved future constraints.

## Principle XI — Documentation and historical evidence have distinct roles

Current product and operator documentation must converge with approved specifications.

Historical gate reports, patch notes, old benchmarks, and operational evidence are records of what was known or observed at a specific time. They are not retroactively rewritten merely because terminology or architecture later improves.

When a historical claim is obsolete, current documentation supersedes it explicitly rather than altering the historical record.

## Governance

### Amendment

Any constitutional amendment must state the principle being changed, explain why the existing rule is insufficient, identify affected specifications/ADRs, identify required migrations or compatibility impacts, and receive explicit approval before dependent implementation proceeds.

### Versioning

- **MAJOR** — incompatible change to a principle, authority model, or governance rule.
- **MINOR** — new principle or substantial expansion of normative obligations.
- **PATCH** — clarification without semantic change.

Draft versions use a pre-release suffix until ratified.

### Exceptions

A constitutional exception must be explicit, scoped, justified, and visible in the relevant specification. Temporary exceptions must include a removal condition. An exception cannot be created implicitly by implementation.

### Review gates

Before approving a baseline specification, reviewers ask:

- Does it conflict with the Constitution?
- Does it confuse observed implementation with intended behavior?
- Does it expose or transport sensitive information unnecessarily?
- Does it preserve dependency direction?
- Does it define behavior in a testable way without prescribing premature implementation details?
- Does it introduce complexity without an approved need?

## Ratification

This Constitution was ratified as **v1.0.0 on 2026-08-15**.

It is now the highest normative engineering artifact for new specification work. Existing code, tests, documentation, and operational evidence remain essential brownfield evidence, but conflicts discovered from this point forward are classified under Principle I rather than resolved automatically in favor of the implementation.
