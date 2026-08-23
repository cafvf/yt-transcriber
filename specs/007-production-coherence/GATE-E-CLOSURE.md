# PLAN-007 — Gate E Closure Record

<!-- PLAN-007:GATE-E:CLOSURE:2026-08-23 -->

## Decision

**GATE-P07-E — Release Candidate Evidence: CLOSED / PASS WITH RESERVATION**

**PLAN-007 — Production Coherence & Distribution: CLOSED / PASS WITH RESERVATION**

Closure date: **2026-08-23**

Canonical release candidate:

`2f2b99840830a555c29afcd56082b259dc971df4`

Branch:

`plan-007-production-coherence`

This closure record is post-decision engineering evidence. Its commit is documentary only and does
not replace the exact release candidate revision proven by Gate E.

## Inherited gates

The release candidate inherits the already closed cumulative gates:

- GATE-P07-A — Truthful Canonical Semantics: PASS.
- GATE-P07-B — Safe Boundaries and Operational Error Semantics: PASS.
- GATE-P07-C — Distributable Runtime and Configuration: PASS.
- GATE-P07-D — Documentation and Onboarding: PASS.

Gate E did not weaken any earlier invariant.

## Task closure

| Task | Result | Status |
| --- | --- | --- |
| P07-018 | compile/import, Ruff lint/format, mypy, cumulative architecture rules, focused/conformance/default pytest and applicable integration execution passed | PASS |
| P07-019 | local secret scanner, Gitleaks, private-artifact inspection and pre-commit passed | PASS |
| P07-020 | wheel/sdist build, wheel inspection, clean Python 3.12 install, installed-origin proof, dev-tool absence, installed console script and offline/read-only installed preflight passed | PASS |
| P07-021 | controlled real YouTube metadata → formats → acquisition passed; the selected live fixture exposed no identifiable alternate/original multi-audio candidate | PASS WITH RESERVATION |
| P07-022 | production host migration, systemd host preflight, journal access, SQLite integrity, stop/start/restart rehearsal and manual Telegram status passed; LM Studio was intentionally offline during manual healthcheck | PASS WITH RESERVATION |
| P07-023 | candidate/base guards, package verification, hashes, evidence directories, exit status, clean-tree and local/remote equality proofs were recorded | PASS |

## Deterministic candidate evidence

The E1 release-candidate run was bound to the exact candidate
`2f2b99840830a555c29afcd56082b259dc971df4`.

Critical automated release checks passed for:

- syntax/import;
- Ruff lint and formatting;
- mypy;
- inherited Gate A/B/C1/C2/C3/D rule sets;
- focused pytest and conformance;
- applicable integration handling;
- configured/default full pytest;
- secret scan, Gitleaks, private-artifact inspection and pre-commit;
- `uv build`;
- wheel integrity/contents;
- clean Python 3.12 venv installation outside the checkout;
- installed package origin and console-script proof;
- absence of pytest/Ruff/mypy/pre-commit from the production venv;
- installed `--preflight --json` from unrelated CWD with no source-checkout dependency;
- offline/read-only preflight contract;
- final candidate/remote/clean guards.

The repository default suite explicitly excludes slow/e2e tests; this was recorded as `NOT_RUN`,
not silently represented as a pass. The integration collection had no applicable selected tests and
was recorded accordingly.

Canonical wheel hash recorded by Gate E:

`8ea8f257389cb8b0596e2537a1e7d2919b453e394b739d25a486fb25a7e9f2c2  yt_transcriber_bot-0.1.3-py3-none-any.whl`

The same wheel hash was produced again during the successful operational migration path.

## Production migration and operational evidence

Gate E exposed and then removed a real legacy deployment dependency: the running service still used
the checkout and obtained part of its effective private configuration from the development `.env`.

The successful E2 migration:

- prepared `/opt/yt-transcriber-bot/venv` before downtime;
- constructed and proved a private production env candidate before stopping the legacy service;
- migrated missing allowlisted effective settings from the legacy checkout `.env` without exposing
  values, while preserving `/etc` precedence;
- canonicalized runtime state to `/var/lib/yt-transcriber-bot`;
- installed the canonical systemd unit;
- used `/etc/yt-transcriber-bot/env` with mode `0600`;
- used `/opt/yt-transcriber-bot/venv/bin/yt-transcriber-bot` as `ExecStart`;
- used `/var/lib/yt-transcriber-bot` as `WorkingDirectory`;
- passed installed preflight before start;
- passed the host/systemd preflight after start;
- validated `PRAGMA integrity_check = ok`;
- preserved the `jobs` table and observed 18 jobs;
- passed explicit systemd stop → start → restart rehearsal;
- finished with the service active.

Migration backup recorded:

`/var/backups/yt-transcriber-bot/gate-e-20260823T232513Z`

Gate E operational evidence directory recorded:

`/home/christiano/Downloads/yt-transcriber-gate-e-e2-evidence-20260823T232513Z`

## Controlled real YouTube smoke

Final controlled smoke used public video id:

`jNQXAC9IVRw`

Observed evidence:

| Fact | Result |
| --- | --- |
| title metadata | present |
| channel metadata | present |
| duration | 19 seconds |
| listed formats | 25 |
| acquired bytes | 629172 |
| selected track | `default` |
| identifiable original-audio candidates | 0 |
| metadata → formats → acquisition | PASS |

The smoke therefore proves real network metadata, format enumeration and short media acquisition from
the clean installed runtime.

It does **not** claim a live multi-audio/original-track proof when the chosen fixture exposes no such
candidate.

## Manual Telegram operational evidence

Manual `/status` after the successful migration reported the bot idle, with no running or pending job.

Manual `/healthcheck` confirmed:

- CPython 3.12.13;
- required credentials configured with expected shapes;
- installed runtime file/config discovery;
- ffmpeg, ffprobe, yt-dlp and supported Node runtime;
- required Python runtime modules;
- writable production data/artifact/model directories;
- accessible SQLite;
- writable operational-error storage;
- sufficient disk space;
- configured YouTube cookies present;
- current summarization/tokenizer configuration.

The healthcheck warning that a **project root is not found** is expected for the installed production
contract and is not a release reservation: production must not depend on a source checkout.

LM Studio `/models` returned connection refused because the local LM Studio process was intentionally
closed during this manual check. Bot `/status` remained operational.

## Reservations

### R1 — live original-track selection not exercised

**Classification:** non-correctness coverage limitation.

The controlled live fixture exposed zero identifiable original-audio candidates, so Gate E does not
claim live proof of the multi-audio original-selection branch. The deterministic/cumulative automated
contract remains green, and the live provider path through metadata, formats and acquisition passed.

**Removal condition:** repeat the controlled smoke with a stable short YouTube fixture that exposes
identifiable original and alternate/dubbed audio, or capture equivalent controlled operational
evidence when such a fixture is available.

### R2 — LM Studio intentionally unavailable during final manual healthcheck

**Classification:** external optional-capability availability limitation.

The configured OpenAI-compatible summarization endpoint was not running during the final manual
healthcheck. This does not invalidate the installed bot, systemd, SQLite, Telegram status or
transcription runtime evidence.

**Removal condition:** start the configured LM Studio endpoint and repeat `/healthcheck`, or
deliberately configure `SUMMARY_BACKEND=disabled` when summarization should not be part of the active
runtime.

## Unexecuted / non-applicable checks

- slow/e2e suite: not run because the repository's default configured suite excludes it; explicitly
  recorded by Gate E evidence.
- live multi-audio original-selection branch: not exercised by the available controlled fixture;
  recorded as reservation R1.
- no applicable integration tests were selected by the integration marker collection in E1; this was
  recorded rather than represented as an executed test set.

No unresolved type, correctness, architecture, security, artifact-integrity, clean-install or required
core-runtime failure is being downgraded to a reservation.

## Final interpretation

Under `ACCEPTANCE-GATE.md`, Gate E therefore reaches the allowed release decision:

**PASS WITH RESERVATION**

The release candidate is installable outside the checkout, uses the canonical private configuration
and state boundaries, passed cumulative deterministic quality/security/distribution evidence, and
passed the affected real-host/systemd/SQLite/Telegram/YouTube operational path.

PLAN-007 is complete. Feature development may resume according to the post-PLAN-007 roadmap; backend
and multilingual/translation work remain ahead of Obsidian-specific note generation.
