# PLAN-007 — Gate C3 Installed Distribution Proof

Status: **P07-014 COMPLETE / PASS**. C3 implementation was reproduced on committed bytes and
published at `612a95636fd9cf1b2a5ce4229df456dc53a8049c`. Final cumulative Gate C closure is recorded in
[`GATE-C-CLOSURE.md`](GATE-C-CLOSURE.md).

## Contract

The production runtime is the built wheel and its installed console script,
not a source checkout and not `uv run`.

The installed CLI exposes:

```text
yt-transcriber-bot --preflight
yt-transcriber-bot --preflight --json
```

This preflight is deliberately read-only and offline. It does not start
Telegram polling, call LM Studio, initialize SQLite, create runtime directories,
load/download ML models, or echo secret values.

The systemd unit uses:

```text
WorkingDirectory=/var/lib/yt-transcriber-bot
StateDirectory=yt-transcriber-bot
ExecStart=/opt/yt-transcriber-bot/venv/bin/yt-transcriber-bot
EnvironmentFile=/etc/yt-transcriber-bot/env
```

## P07-014 clean-distribution proof

The Gate C3 convergence runner performs, before real checkout mutation:

1. history-preserving detached candidate clone;
2. exact C3 scope proof;
3. Gate A + B + C1 + C2 + C3 audits;
4. full configured pytest;
5. `uv build`;
6. a fresh **Python 3.12** virtual environment outside the candidate;
7. installation of the wheel with production dependencies;
8. proof that `pre-commit`, `pytest`, `ruff`, and `mypy` are absent;
9. import/package-resource checks from the installed environment;
10. execution of `yt-transcriber-bot --preflight --json` from an **unrelated CWD**
    with `PYTHONPATH` removed;
11. proof that the unrelated CWD remains empty after preflight.

A synthetic supported Deno executable is placed only in the temporary smoke
`PATH` so the distribution proof is deterministic. Host readiness remains the
responsibility of the real host/systemd preflight.

## Boundary synchronization

C3 was generated only after an explicit `git fetch`, `git pull --ff-only`, clean
working-tree check, and equality proof between local and remote SHA. This
becomes the standard transition rule between major PLAN-007 subgates.
