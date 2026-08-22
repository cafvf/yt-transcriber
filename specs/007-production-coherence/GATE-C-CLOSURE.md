# PLAN-007 — Gate C Closure Record

<!-- PLAN-007:GATE-C:CLOSURE:2026-08-22 -->

## Decision

**GATE-P07-C — Distributable Runtime and Configuration: CLOSED / PASS**

Closure date: **2026-08-22**

Canonical implementation commits:

- C1 configuration boundary: `68190353bc3b6fa5959db39a990310c7d5f336e2`
- C1 lessons consolidation: `636bf9e9e47b34230bd2efeb6819fd148b3858ef`
- C2 runtime readiness: `38e4f4fed4ebdefe8cc4b69fc7281bac6e0e7c71`
- C3 installed distribution: `612a95636fd9cf1b2a5ce4229df456dc53a8049c`

The gate is closed on committed implementation bytes and reproduced clean-install
evidence. This closure commit reconciles documentation only; it does not alter
runtime behavior.

## Scope closed

| Task | Canonical result | Status |
| --- | --- | --- |
| P07-010 | production configuration uses a private host-managed environment contract; installed runtime does not discover arbitrary-CWD `.env` or repository metadata | PASS |
| P07-011 | `ProviderCredentials` remains the single credential declaration owner; process environment precedence and safe redaction are proven | PASS |
| P07-012 | development-only tooling is excluded from runtime dependency metadata | PASS |
| P07-013 | YouTube/EJS readiness is version-aware and accepts Deno >= 2.3.0 or Node >= 22.0.0 with required yt-dlp modules | PASS |
| P07-014 | wheel builds and clean-installs with production dependencies; installed CLI/config/package-data/preflight work without source checkout or dev tooling | PASS |

## Production runtime contract proven

The production service contract is the installed distribution rather than a
source checkout:

```text
EnvironmentFile=/etc/yt-transcriber-bot/env
WorkingDirectory=/var/lib/yt-transcriber-bot
StateDirectory=yt-transcriber-bot
ExecStart=/opt/yt-transcriber-bot/venv/bin/yt-transcriber-bot
```

The installed CLI exposes:

```text
yt-transcriber-bot --preflight
yt-transcriber-bot --preflight --json
```

The preflight is read-only and offline for its basic runtime proof: it does not
start Telegram polling, call LM Studio, initialize SQLite, create runtime
directories, load/download ML models, or echo configured secret values.

## Final C3 convergence evidence

The final C3 convergence completed with **105 PASS, 0 FAIL** and was reproduced
on the committed bytes before push.

The final implementation evidence included:

- Gate A, Gate B, Gate C1, Gate C2 and Gate C3 audits: PASS.
- exact C3 implementation scope: 14 paths / 10 Python paths.
- Ruff lint and format: PASS.
- mypy: **152 source files**, no issues.
- focused C3/runtime/composition tests: **37 passed**.
- complete conformance: **163 passed**.
- explicit Gate A SQLite compatibility integration: **2 passed**.
- configured pytest suite: **1047 passed, 37 deselected**.
- Gitleaks: PASS.
- pre-commit all files: PASS.
- `uv build`: PASS.
- clean Python **3.12.13** environment: PASS.
- production wheel installation with **135 packages**: PASS.
- `pre-commit`, `pytest`, `ruff` and `mypy` absent from the clean production environment.
- installed package imported from the clean environment's `site-packages`, with
  checkout paths absent from `sys.path`.
- installed `yt-transcriber-bot --preflight --json` executed from an unrelated
  empty CWD.
- installed preflight reported `passed=true`,
  `development_checkout_detected=false`, `network_access_performed=false` and
  `filesystem_mutation_performed=false`.
- unrelated CWD remained empty after preflight.

## Publication evidence

The C3 implementation was published at:

`612a95636fd9cf1b2a5ce4229df456dc53a8049c`

Commit message:

`refactor: establish PLAN-007 installed distribution`

After publication, an explicit Gate-boundary synchronization reproduced:

```text
local  = 612a95636fd9cf1b2a5ce4229df456dc53a8049c
remote = 612a95636fd9cf1b2a5ce4229df456dc53a8049c
working tree = clean
git pull --ff-only = Already up to date.
```

## Compatibility and inherited invariants

Gate C inherits all closed Gate A and Gate B invariants and compatibility
records. Gate C does not reopen taxonomy, persistence compatibility or the
provider-neutral operational-error contract.

The configuration/readiness/distribution-specific lessons LL-049 through
LL-070 remain implementation preconditions for future maintenance.

## Closure interpretation

Gate C closes configuration, production dependency separation, runtime
readiness, installed CLI/systemd composition, build and source-checkout-
independent clean installation.

It does **not** claim that the product-facing README, onboarding, installation
runbooks or user-relevant deprecation documentation are complete. Those are the
scope of Gate D.

## Next gate

Next implementation target:

**GATE-P07-D — Documentation and Onboarding (P07-015…P07-017)**.
