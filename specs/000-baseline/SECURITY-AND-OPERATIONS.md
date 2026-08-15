# Baseline Security and Operations Specification

Version: **1.0.0**
Status: **Approved**
Baseline date: **2026-08-15**

## 1. Security posture

The product is private, local-first, and single-operator.

Relevant risks include bot credential theft, Hugging Face/future API-token leakage, YouTube cookie leakage, private transcript/media exposure, accidental commits, diagnostic/log leakage, backup leakage, unauthorized Telegram interaction, unsafe provider-payload persistence, and secret propagation across architectural layers.

Security uses layered controls.

## 2. Secret classes

Current sensitive credentials include Telegram bot token, Hugging Face token, YouTube/browser cookies when used, and future API keys/access tokens.

A Telegram bot token and comparable API tokens are bearer credentials: anyone who obtains the value may exercise the permissions granted to that identity. Provider credentials remain secrets even when free-tier or narrowly scoped.

## 3. Secret storage

Real secrets must not be stored in tracked files.

Tracked examples contain inert placeholders only. The repository is currently public, but these rules would remain mandatory even if repository visibility changed; repository privacy is not a secret-management mechanism.

The baseline approves two runtime mechanisms with identical invariants:

- interactive/development execution: secrets supplied through the user process environment or another explicitly selected local secret source outside tracked repository content;
- systemd execution: secrets supplied through an operator-managed environment file outside the repository with restrictive ownership/permissions.

Repository-root `.env` may remain a local compatibility mechanism where already supported, but it is not the preferred location for long-lived provider credentials. Tracked `.env.example` remains placeholder-only.

Secret-bearing files use restrictive host permissions. The application must not require duplicating a secret into tracked or world-readable configuration merely to support a different execution mode.

## 4. Secret flow

Secrets enter the process at composition/infrastructure boundaries and are consumed only by components that require them.

A provider token must not become a domain entity field or generic application-port parameter merely because an infrastructure library requires it.

The current `hf_token` handling in the diarization port is a baseline architectural/security issue to remove.

## 5. Least privilege

Where providers support token scopes or granular permissions, use the narrowest practical permissions.

A credential must not be logged to prove it loaded. Diagnostics should report presence/validity without reproducing the value.

## 6. Exposure and incident response

Any credential shown in an uncontrolled location is presumed compromised.

Examples include Git history, issues/PRs, public/third-party chat, screenshots, CI logs, application logs, diagnostic bundles, and transcript artifacts.

Response requires revocation/rotation and replacement in the protected runtime environment. Deleting/masking visible text alone is insufficient.

## 7. Development, support, and AI-assistant surfaces

Git, GitHub, CI output, issue/PR discussions, screenshots, copied terminal output, support chats, and prompts sent to AI assistants or third-party analysis tools are treated as disclosure surfaces outside the trusted runtime boundary.

Real tokens, cookies, authorization headers, private transcript bodies, full Telegram payloads, and secret-bearing environment files must not be provided to those surfaces. Diagnostic material is sanitized or replaced with inert placeholders before sharing.

When a development or support workflow requires a realistic value, use a synthetic value that cannot authenticate to any real service.

## 8. Private content

Private by default:

- input media;
- transcript text;
- speaker names/aliases;
- summaries;
- search queries/results;
- indexes or future vector data derived from transcripts;
- SQLite databases;
- snapshots;
- audit/error logs;
- identifying filesystem paths/names;
- backups.

Sanitized output remains private operational data unless specifically reviewed for publication.

## 9. Logging and diagnostics

Logs follow data minimization.

They may retain information needed for lifecycle auditing, debugging, recovery, and operator decisions.

They should omit/sanitize tokens, cookies, authorization headers, complete provider bodies, prompts containing private transcript text, full Telegram payloads, and transcript bodies except under a narrowly scoped approved local-debug mode.

New diagnostic paths use centralized sanitization or an approved equivalent.

## 10. Authorization

The baseline supports one allowed Telegram user.

Unauthorized interaction must not access history, transcript content, artifacts, diagnostics, filesystem information, or processing controls.

Future multi-user capability requires a separate security specification.

## 11. Secret scanning

Defense in depth includes ignore rules, local scanner, Gitleaks when available, pre-commit checks, and CI security checks.

A clean scan is evidence, not proof.

Discovered leakage patterns should become regression scanner/test coverage.

## 12. Backups

Backups are sensitive containers and may include database, transcript artifacts, logs, cookies, and media.

The standard operational backup excludes reusable provider credentials, secret-bearing environment files, and authentication-cookie material by default. Credentials/cookies are reprovisioned separately during restore.

If an operator deliberately creates a disaster-recovery bundle containing credentials or authentication cookies, that bundle is a distinct higher-sensitivity artifact and requires stronger access control/encryption and explicit retention handling.

All backups require restrictive permissions, access-controlled storage, no attachment to public collaboration surfaces, documented restore, and deliberate retention.

## 13. Operational evidence

Automated tests for rehearsal helpers do not prove that systemd/backup/recovery was successfully exercised on the deployment host.

Before declaring private production readiness complete, reproducible host/staging evidence is required for:

- systemd start/stop/restart;
- rollback;
- backup/restore;
- interrupted-job recovery;
- `delivery_failed` recovery/manual artifact access.

## 14. Restart/recovery baseline

The queue is in memory.

Persisted job data supports restart reconciliation: recoverable pending work may be re-enqueued; interrupted active states are reconciled; interrupted delivery is represented distinctly; checkpoint continuation inside expensive stages is not promised.

## 15. Security review triggers

Review is required when changing credentials, external APIs/services, incoming transports, authorization, persistence of user content, diagnostics/logging, backups, artifact sharing/export, network exposure, or multi-user behavior.

## 16. Current evidence

On 2026-08-15 the local secret scanner found no obvious secret, Gitleaks found no leak in the scanned repository history, and the default test/lint/type baseline passed.

This evidence should later update the current readiness ledger.

## 17. Remaining security questions

Before or during security-requirement derivation:

- decide whether `/healthcheck` can safely and portably verify restrictive permissions on a configured secret-bearing env file without exposing its path unnecessarily;
- define provider-specific operator runbook steps for revocation/rotation while keeping the constitutional incident rule provider-independent;
- define the exact conformance check that proves provider-secret parameters do not leak into domain/application contracts;
