# REQ-SEC-002 — Provider-secret storage, privilege and incident lifecycle

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **SEC-SECRETS**
Behavior/spec sources: **Constitution V/VII, SECURITY-AND-OPERATIONS §§2-6**
Dependencies: **upstream approved specifications only**

## Normative requirement

Reusable provider credentials SHALL remain outside tracked content, use the narrowest practical privilege, be retained only as needed, and be revoked or rotated after uncontrolled exposure.

## Acceptance criteria

- AC-01: Tracked source, tests, examples and generated specifications contain only inert credential placeholders.
- AC-02: Runtime configuration does not require copying reusable credentials into tracked or world-readable files.
- AC-03: Where provider scopes exist, documented configuration uses the narrowest practical scope for the approved capability.
- AC-04: Diagnostics may report credential presence/validity without reproducing the secret value.
- AC-05: Documented exposure response requires revoke/rotate rather than masking or deletion alone.

## Required evidence

- secret scanner and Gitleaks
- configuration/documentation conformance tests
- incident-response documentation review

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
