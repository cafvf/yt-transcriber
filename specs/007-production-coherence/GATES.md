# PLAN-007 — Cumulative Gate Model

Version: **1.0.0**
Status: **Approved**
Approved: **2026-08-19**

## 1. Purpose

PLAN-007 gates are architectural state transitions, not test bundles.

Each gate defines the minimum coherent state the codebase SHALL have before the next package may start.
A later gate inherits every invariant from every earlier gate and adds new invariants. It cannot trade
a regression in an earlier contract for new passing tests.

```text
Frozen constitutional/baseline architecture
                ↓
GATE-P07-A — truthful canonical semantics
                ↓
GATE-P07-B — safe application boundaries and errors
                ↓
GATE-P07-C — distributable runtime/configuration
                ↓
GATE-P07-D — operator contract/documentation convergence
                ↓
GATE-P07-E — release candidate evidence
```

For a candidate state S:

```text
PASS(B,S) => PASS(A,S)
PASS(C,S) => PASS(A,S) and PASS(B,S)
PASS(D,S) => PASS(A,S) and PASS(B,S) and PASS(C,S)
PASS(E,S) => PASS(A,S) and PASS(B,S) and PASS(C,S) and PASS(D,S)
```

## 2. Inherited architecture

Every gate inherits these non-negotiable rules:

1. Domain depends only on stdlib/domain; application depends only on stdlib/domain/application;
   infrastructure implements application ports; composition owns concrete wiring.
2. Taxonomy must be truthful and source-neutral where the concept is source-neutral.
3. No speculative abstraction may be introduced merely to satisfy an architecture test.
4. Provider credentials remain at infrastructure/composition boundaries.
5. Unknown data stays unknown; provenance and canonical artifacts remain truthful.
6. Completion, failure, cancellation, delivery failure and recovery are distinct semantics.
7. SDD defines acceptance; behavior changes use characterization and Red → Green → Refactor.
8. Historical evidence remains historical.

## 3. General gate law

### Entry
A package starts only after its predecessor gate is PASS.

### Cumulative evidence
Every later gate reruns the automated evidence of earlier gates against the current candidate revision.
A PASS from an older commit is not proof for a later HEAD.

### No weakening
A gate SHALL NOT become green by deleting meaningful tests, weakening assertions without specification
change, expanding allowlists without a scoped exception, adding unproven compatibility aliases,
turning required tests into unconditional skips, hiding errors, or documenting unimplemented behavior.

### Exceptions
A temporary exception needs the violated invariant, reason, bounded scope, owner, evidence, removal
condition and target window.

### Gate record
Each gate completion records exact SHA, inherited gates, requirements/tasks, compatibility changes,
commands, results, environment evidence, reservations and PASS/BLOCKED decision.

Development gates do not use PASS WITH RESERVATION for unresolved correctness, architecture or
security defects.

# 4. GATE-P07-A — Truthful Canonical Semantics

## Adds
One truthful internal vocabulary for the existing product before deeper boundary or packaging work.

## Required code behavior
- `MediaMetadata` is canonical for shared media metadata.
- Source-specific YouTube concepts remain source-specific only where truly required.
- Alternate tracks existing and the selected track are represented as distinct facts.
- Selecting original audio in the presence of auto-dubs is never represented as "used alternate"
  or "audio was dubbed".
- Track selection is typed and truthful; unknown selection uses UNKNOWN rather than invented certainty.
- Requested, effective/transcription and observed language plus language provenance use canonical typed
  values inside domain/application flow.
- `processing_fingerprint` is the canonical internal processing-identity concept.
- Source-neutral processing uses media terminology.
- Existing artifact taxonomy is reused for domain artifact policy.

Compatibility is translated at the boundary and disappears immediately after translation.

## Blocks
- misleading audio-track booleans;
- source-neutral flows still canonically named `VideoMetadata`;
- raw language strings where typed values own the concept;
- duplicate processing-signature concepts without one canonical owner;
- new legacy alias without compatibility evidence;
- fabricated source/language/duration facts.

## Evidence
Characterization, domain/value-object, pipeline, persistence compatibility, taxonomy/conformance,
architecture dependency, Ruff, mypy and relevant regression tests.

## Handoff
Gate B receives typed, truthful contracts and must not interpret legacy synonyms to decide behavior.

# 5. GATE-P07-B — Safe Boundaries and Operational Error Semantics

## Adds
Stable provider-neutral failure semantics and explicit capability boundaries. Inherits A.

## Required code behavior
Operational errors expose stable code, category, retryability, safe message and optional sanitized
technical context. Provider exception names are not the application contract.

Provider/OS/SDK errors are classified in adapters, translated into safe application semantics and only
then rendered to Telegram/operator/log surfaces.

Where a real application port exists, application orchestration uses it. Canonical Markdown writes go
through the existing canonical Markdown writer port. No generic filesystem abstraction is introduced
just to satisfy tests.

Ports describe application capabilities rather than provider APIs.

## Blocks
- any Gate A regression;
- unsanitized provider error propagation;
- broad catches that hide or misclassify failure;
- new application→infrastructure dependency;
- provider credentials in domain/application contracts;
- unjustified new direct application I/O;
- generic architecture wrappers with no demonstrated capability.

## Evidence
All A evidence plus error contract, retryability/safe-message, adapter mapping, sanitization,
application-port, hexagonal dependency, composition ownership, direct-I/O and relevant integration tests.

# 6. GATE-P07-C — Distributable Runtime and Configuration

## Adds
Proof that the architecture can be assembled and installed outside the developer checkout. Inherits A+B.

## Required code/runtime behavior
- one canonical production private env-file policy outside the repository;
- restrictive permissions;
- code still separates credential ownership from behavior settings;
- project-root `.env` is development convenience, not production secret policy;
- legacy env aliases are boundary-local and documented;
- concrete providers are selected only in composition/runtime;
- credential validation never echoes reusable secrets;
- preflight reflects real yt-dlp-ejs + Deno/supported Node requirements;
- production package builds/installs without dev-only dependencies;
- installed package works without repository-relative accidents;
- health/preflight distinguishes missing runtime, credential, optional capability, config error and healthy state.

## Blocks
- any A/B regression;
- production requiring pre-commit/pytest/dev tooling;
- implicit dependency on source checkout/current directory;
- contradictory credential precedence;
- false-positive healthcheck;
- raw token/cookie output;
- installability claimed only in docs.

## Evidence
A+B plus config precedence, credential sanitization, build, clean install, import/CLI/startup,
package-resource, health/preflight, security scanner and supported-runtime checks.

# 7. GATE-P07-D — Operator Contract and Documentation Convergence

## Adds
Current documentation becomes a truthful operator contract. Inherits A+B+C.

## Required behavior
README/operator docs explain product scope, platform/runtime, exact clone/install commands, credentials,
private config, permissions, startup, health gate, first transcription, systemd, update, backup/restore,
troubleshooting and developer/architecture entry points.

Every user-visible compatibility alias has canonical replacement, deprecation status and removal policy.

If docs reveal a code defect, the defect is routed back to A/B/C, fixed there, inherited gates rerun,
and only then does work return to D. Documentation is not changed to bless a defect.

## Blocks
- A/B/C regression;
- current docs contradicting each other;
- placeholder clone commands where repo is known;
- missing required Deno/Node/ejs prerequisite;
- recommendation to echo secrets;
- unimplemented feature documented as available;
- historical evidence presented as current proof.

## Evidence
A+B+C plus documentation/config/command/help/env/default/prerequisite/link/compatibility conformance and
manual operator-flow review.

# 8. GATE-P07-E — Release Candidate Evidence

## Adds
Final proof for one exact release candidate revision. Inherits A+B+C+D.

## Required candidate behavior
Candidate preserves approved baseline capabilities, canonical semantics, safe boundaries, clean build/
install, security controls, truthful docs, supported runtime health, authorized provider smoke behavior
and verifiable distribution artifacts.

## Failure routing
- semantic/domain/type defect → A;
- error/boundary defect → B;
- config/package/runtime defect → C;
- documentation defect → D;
- artifact/evidence-only defect → E.

Any correction creates a new candidate revision and cumulative automated gates run again.

## Evidence
Compile/import, Ruff lint/format, mypy, unit, contract, architecture/conformance, integration/e2e where
applicable, full default pytest, secret scan, Gitleaks, pre-commit, `uv build`, clean package install,
startup/config/preflight smoke, controlled YouTube smoke when authorized, systemd/health/SQLite when
affected, archive extraction and SHA-256 verification.

## Decision
- PASS: all applicable cumulative critical gates pass.
- PASS WITH RESERVATION: only non-critical disclosed limitations.
- BLOCKED: any required gate fails, is untrustworthy or did not execute.

# 9. Consequence for TASK derivation

After this gate model is approved, every TASK is expanded from its owning gate:

1. owning gate;
2. inherited invariants;
3. requirement(s);
4. current brownfield condition;
5. desired observable behavior;
6. use cases;
7. alternate/error/edge cases;
8. compatibility impact;
9. unit tests;
10. contract/conformance tests;
11. integration/operational evidence;
12. Red → Green → Refactor;
13. exact gate acceptance evidence.

This preserves the direction:

```text
architecture → gate → behavior → task → use case → test → evidence
```

<!-- PLAN-007:GATE-A:STATUS:2026-08-21 -->
## Gate closure ledger — 2026-08-21

| Gate | Status | Evidence | Next |
| --- | --- | --- | --- |
| GATE-P07-A — Truthful Canonical Semantics | **CLOSED / PASS** | [`GATE-A-CLOSURE.md`](GATE-A-CLOSURE.md), implementation `cd5f71d` | GATE-P07-B |
