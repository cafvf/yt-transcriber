# REQ-SEC-008 — Provider-secret architectural boundary

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **SEC-BOUNDARY**
Behavior/spec sources: **Constitution III/V, ARCHITECTURE §4, SECURITY-AND-OPERATIONS §4**
Dependencies: **REQ-SEC-002**

## Normative requirement

Provider-specific credentials SHALL be resolved and consumed at composition/infrastructure boundaries and SHALL not become domain entity fields, application business payloads or generic application-port parameters.

## Acceptance criteria

- AC-01: No provider token/cookie/API-key field exists in domain entities.
- AC-02: Generic application ports do not accept provider credentials such as `hf_token`.
- AC-03: Application requests carry business/security-neutral capability inputs rather than provider authentication material.
- AC-04: Concrete adapters receive their authentication configuration from composition/edge configuration.

## Required evidence

- architecture/conformance scan for credential-shaped domain/application parameters
- port contract tests
- composition-root tests

## Brownfield deviation addressed

The diarization port transports `hf_token`, and application `AppSettings` currently owns raw provider secrets.

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
