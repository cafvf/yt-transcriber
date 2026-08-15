# REQ-SEC-009 — External-service disclosure boundary

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **SEC-EXTERNAL**
Behavior/spec sources: **UC-001, UC-007, UC-009, Constitution VI/VII**
Dependencies: **REQ-SEC-003, REQ-SEC-008**

## Normative requirement

Data SHALL cross an external-service boundary only as required for the explicitly configured approved operation, with endpoint/provider choice controlled by trusted configuration and with private payloads minimized to that operation.

## Acceptance criteria

- AC-01: Transcript text is sent to a non-local text-generation endpoint only when such an endpoint was explicitly configured by the operator.
- AC-02: External-service requests do not include unrelated credentials, local paths, logs or private payload classes that the provider does not need.
- AC-03: Provider endpoint/model identity used for an operation comes from trusted configuration rather than transcript/provider response content.
- AC-04: External errors and response bodies are sanitized before persistence or display.

## Required evidence

- external-boundary contract tests
- text-generation boundary tests
- security review for configured external endpoints

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
