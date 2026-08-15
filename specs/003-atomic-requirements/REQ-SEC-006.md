# REQ-SEC-006 — Dependency, model and tokenizer trust

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **SEC-SUPPLYCHAIN**
Behavior/spec sources: **QUALITY, SECURITY-AND-OPERATIONS §15**
Dependencies: **upstream approved specifications only**

## Normative requirement

Runtime dependencies, ML models and tokenizers SHALL have explicit reproducibility/trust controls, and executable remote model/tokenizer code SHALL remain disabled by default and require deliberate security-relevant operator configuration.

## Acceptance criteria

- AC-01: `uv.lock` is the reproducible dependency authority for approved installs.
- AC-02: Directly imported runtime packages are declared directly, or an optional/fallback relationship is explicit and covered by tests.
- AC-03: `trust_remote_code` defaults to false and enabling it is surfaced as a security-relevant configuration.
- AC-04: Loading from a local cache does not bypass the configured model/tokenizer identity or remote-code/trust policy.

## Required evidence

- dependency/configuration conformance tests
- locked-install CI
- security regression for remote-code default

## Brownfield deviation addressed

`transformers` is directly imported by summary tokenizer logic but is not a direct project dependency.

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
