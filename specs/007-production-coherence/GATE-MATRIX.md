# PLAN-007 — Cumulative Gate Matrix

Version: **0.1.0**
Status: **Draft — companion to `GATES.md`**

Legend: **I** inherited, **N** new primary contract, **V** final validation emphasis.

| Concern | A | B | C | D | E |
|---|:---:|:---:|:---:|:---:|:---:|
| Constitution / frozen baseline | I | I | I | I | V |
| Hexagonal dependency direction | I | I/N | I | I | V |
| Truthful Media taxonomy | N | I | I | I | V |
| Audio-track semantic truth | N | I | I | I | V |
| Typed language flow | N | I | I | I | V |
| Processing fingerprint | N | I | I | I | V |
| Compatibility containment | N | I | I | I/N | V |
| Stable operational errors | — | N | I | I | V |
| Provider exception sanitization | — | N | I | I | V |
| Application I/O via real ports | — | N | I | I | V |
| Provider-neutral ports | I | N | I | I | V |
| Credential boundary | I | I | N | I | V |
| Production configuration policy | — | — | N | I | V |
| Runtime prerequisite truth | — | — | N | I | V |
| Package/clean installation | — | — | N | I | V |
| Health/preflight acceptance | — | — | N | I | V |
| README/operator contract | — | — | — | N | V |
| Documentation conformance | I | I | I | N | V |
| Full regression suite | I | I | I | I | V |
| Security scans | I | I | N | I | V |
| Controlled external smoke | — | — | targeted | — | V |
| systemd/host evidence | — | — | targeted | documented | V |
| Distribution hash/integrity | — | — | build smoke | — | V |

## Cumulative execution

```text
Gate A candidate: A
Gate B candidate: A + B
Gate C candidate: A + B + C
Gate D candidate: A + B + C + D
Gate E candidate: A + B + C + D + E
```

Environment/host evidence may be reused only if it is tied to a known revision, later changes cannot
affect that path, reuse is explicitly justified, and the current automated contract still passes.
Otherwise it is repeated.

## Current task ownership proposal

| Gate | Tasks | Primary result |
|---|---|---|
| A | P07-001…005 | canonical semantic core |
| B | P07-006…009 | safe errors and hexagonal capability boundaries |
| C | P07-010…014 | installable/configurable product runtime |
| D | P07-015…017 | truthful operator contract |
| E | P07-018…023 | exact-revision release proof |

Detailed use-case/test derivation is intentionally deferred until these gate contracts are approved.
