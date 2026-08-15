# REQ-SEC-001 — Authorized operator and approved Telegram audience

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **A**
Derived families: **SEC-AUTH**
Behavior/spec sources: **UC-001..UC-012, DD-004**
Dependencies: **upstream approved specifications only**

## Normative requirement

The system SHALL authorize supported Telegram interaction only for the configured operator in the approved private-chat audience. Unauthorized users and unsupported non-private audiences SHALL not gain access to private lookup, processing, controls, diagnostics, transcripts or artifacts.

## Acceptance criteria

- AC-01: Authorized private-chat requests from the configured operator reach the intended handler.
- AC-02: A different user_id cannot access processing, history, diagnostics, artifacts or controls.
- AC-03: The authorized operator in a non-private chat cannot trigger private lookup, expensive processing, control mutation, transcript/artifact delivery or private diagnostics; an implementation may ignore the request or return only neutral guidance.
- AC-04: Authorization and audience checks occur before expensive work, private-data lookup or state mutation.

## Required evidence

- unit/contract tests for user+chat audience matrix
- Telegram adapter conformance test

## Brownfield deviation addressed

Current adapter checks only user_id and sends to the incoming chat_id.

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
