# REQ-OPS-003 — Private host installation and systemd service lifecycle

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **E**
Derived families: **OPS-SERVICE**
Behavior/spec sources: **OS-001, DD-002**
Dependencies: **REQ-ARC-011, REQ-NFR-003, REQ-NFR-004, REQ-SEC-002, REQ-SEC-007**

## Normative requirement

The deployment baseline SHALL document and verify supported host prerequisites plus least-privilege systemd start/stop/restart/log operation with protected secret configuration outside tracked repository content.

## Acceptance criteria

- AC-01: The service runs under an unprivileged configured account; any root/privilege exception requires an explicit constitutional/specification exception rather than an undocumented deployment shortcut.
- AC-02: The systemd secret/environment source has restrictive owner/mode verified by host preflight or rehearsal.
- AC-03: Start and restart are followed by the approved health/status validation.
- AC-04: Journal/evidence output is sanitized before being moved to collaboration surfaces.
- AC-05: Install prerequisites match approved Python/Linux/ffmpeg/runtime expectations.

## Required evidence

- deployment/preflight tests
- systemd host rehearsal evidence
- permission evidence

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
