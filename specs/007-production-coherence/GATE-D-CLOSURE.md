# PLAN-007 — Gate D Closure Record

<!-- PLAN-007:GATE-D:CLOSURE:2026-08-23 -->

## Decision

**GATE-P07-D — Documentation and Onboarding: CLOSED / PASS**

Closure date: **2026-08-23**

Canonical implementation commit:

`7080afc9342f0bd94b0ab74aba3b1c60996c0bc9`

Commit message:

`docs: reconcile PLAN-007 production onboarding`

Implementation parent:

`7ee625302d2df92a6bc09d4c4e8312039aafb003`

Gate D closes on committed documentation/conformance bytes that were reconstructed,
revalidated, compared byte-for-byte, committed and published before this closure record.

## Scope closed

| Task | Canonical result | Status |
| --- | --- | --- |
| P07-015 | root README is the product front door for capabilities, limitations, prerequisites, production installation, private credentials/configuration, first use, systemd, update, backup, troubleshooting, development and deeper documentation | PASS |
| P07-016 | installation, security, runbook and readiness documentation agree with the installed-distribution contract; engineering history remains under `specs/` while obsolete public gate reports and patch-note trees are no longer part of operator-facing documentation | PASS |
| P07-017 | user-relevant compatibility, deprecation and removal policy is explicit in `docs/12-deprecacoes-e-compatibilidade.md` | PASS |

## Canonical documentation contract proven

Gate D documents the production service as an installed distribution rather than a
source-checkout runtime:

```text
EnvironmentFile=/etc/yt-transcriber-bot/env
WorkingDirectory=/var/lib/yt-transcriber-bot
StateDirectory=yt-transcriber-bot
ExecStart=/opt/yt-transcriber-bot/venv/bin/yt-transcriber-bot
```

The production environment template is
`deploy/yt-transcriber-bot.environment.example`; repository `.env.example` is
development-oriented. The canonical media-duration setting taught to users is
`MAX_MEDIA_DURATION_MIN`; the legacy `MAX_VIDEO_DURATION_MIN` name is compatibility
surface rather than current guidance.

Current operator documentation also preserves the actual recovery boundary:
interrupted ASR/diarization does not resume from a mid-stage checkpoint, and
`delivery_failed` recovery does not imply a universal automatic resend.

## Public documentation cleanup

The Gate D implementation intentionally removed obsolete operator-facing historical
material under `docs/gate-reports/`, `docs/patches/`,
`docs/00-auditoria-da-documentacao.md` and `docs/05-plano-de-execucao.md`.

This is not loss of engineering history. PLAN/task/use-case/closure evidence remains
versioned under `specs/`, where historical engineering evidence belongs.

## Validation evidence

The final Gate D candidate and commit finisher reproduced the following evidence
before publication:

- Gate D documentation-to-implementation audit: PASS.
- Ruff lint: PASS.
- Ruff formatting: PASS after deterministic formatting inside the detached candidate.
- Gate D focused documentation/conformance set: **54 passed**.
- complete conformance suite: **163 passed**.
- configured pytest suite: **1047 passed, 37 deselected**.
- inherited Gate A/B/C audit commands: PASS.
- local secret scanner: PASS.
- Gitleaks: PASS, no leaks found.
- pre-commit all files: PASS.
- approved Gate D implementation scope: **81 paths**.
- reconstructed detached candidate matched the real checkout byte-for-byte before staging.
- exact staging left no unstaged residue.
- committed tree matched the validated detached candidate.

No runtime source under `src/` was changed by the Gate D implementation commit.

## Publication evidence

The implementation commit was published as:

`7080afc9342f0bd94b0ab74aba3b1c60996c0bc9`

with exact parent:

`7ee625302d2df92a6bc09d4c4e8312039aafb003`

Post-push proof recorded:

```text
local  = 7080afc9342f0bd94b0ab74aba3b1c60996c0bc9
remote = 7080afc9342f0bd94b0ab74aba3b1c60996c0bc9
working tree = clean
```

## Reservations

**None for Gate D.**

This closure does not pre-claim the final release decision. Real/controlled runtime
smoke, build/clean-install release evidence, final security/artifact checks and the
overall PASS / PASS WITH RESERVATION / BLOCKED decision belong to Gate E.

## Closure interpretation

Gate D closes product-facing documentation, onboarding, installation/security/runbook
coherence, operator readiness documentation and user-relevant compatibility/deprecation
guidance.

It does not reopen the already closed Gate A, B or C contracts and does not add feature
scope.

## Next and final gate

Next target:

**GATE-P07-E — Release Gate (P07-018…P07-023).**

Gate E is the final gate of PLAN-007. Feature work may resume only after Gate E reaches
an allowed release decision under `ACCEPTANCE-GATE.md`.
