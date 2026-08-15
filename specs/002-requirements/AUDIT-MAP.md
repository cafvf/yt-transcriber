# Current Audit Findings to Requirement Tree

Version: **1.0.0**
Status: **Approved / Frozen audit coverage**

This map ensures the requirement tree covers both the original pre-SDD audit and blind spots found during the requirement-tree review. It does not define implementation tasks.

| Current finding | Requirement branches that must resolve it |
|---|---|
| `application -> infrastructure` imports in pipeline/use-case/services | ARCH-BOUNDARY, ARCH-PORTS, ARCH-APP, ARCH-TRANSCRIPT |
| Application services also own external I/O directly through stdlib (`HealthCheckService`, `LastErrorService`, `RetentionPolicy`) | ARCH-BOUNDARY, ARCH-PORTS, ARCH-OPS, DATA-OPSLOG, DATA-RETENTION |
| Filesystem-dependent `ModelName` domain validation | ARCH-BOUNDARY, ARCH-RUNTIME, ARCH-ASR, DOMAIN-PROVENANCE, NFR-MAINTAIN |
| `Device`/`ComputeType` are provider/runtime concepts (`cuda`, CTranslate2 precision) located in pure domain | ARCH-BOUNDARY, ARCH-RUNTIME, ARCH-ASR, NFR-MAINTAIN |
| `hf_token` present in diarization application port | ARCH-DIAR, SEC-BOUNDARY, SEC-SECRETS, ARCH-COMPOSITION |
| Diarization has independent backends/fallback but the old tree had no dedicated requirement family | ARCH-DIAR, DOMAIN-PROVENANCE, NFR-RELIABILITY |
| `TelegramBotAdapter` owns queue/application policy/delivery/history/derived workflows | ARCH-TRANSPORT, ARCH-EXECUTION, ARCH-APP, FUNC-CONTROL, FUNC-DELIVERY, NFR-MAINTAIN |
| `HistoryCollaboration` contains application-like history selection/rules inside `infrastructure/telegram` | ARCH-TRANSPORT, ARCH-APP, FUNC-HISTORY |
| Sequential queue/worker/startup recovery is located under Telegram infrastructure | ARCH-EXECUTION, ARCH-TRANSPORT, OPS-STARTUP, FUNC-CONTROL |
| Summary orchestration/chunking/retry/output policy lives in infrastructure | ARCH-APP, ARCH-TEXTGEN, FUNC-SUMMARY |
| Job repository mixes lifecycle persistence, search/index, and filesystem-derived indexing | ARCH-PERSIST, DATA-JOB, DATA-SEARCH, NFR-MAINTAIN |
| Job transition method permits impossible non-terminal transitions | DOMAIN-JOB, NFR-RELIABILITY |
| Historical video-specific names now represent generic media | DOMAIN-MEDIA, FUNC-SOURCE, NFR-MAINTAIN |
| `Job.source_url` overloads external YouTube reference and local Telegram staging locator | DOMAIN-MEDIA, DATA-JOB, DATA-MEDIA, SEC-PRIVACY/FILES |
| ASR port exposes Whisper/CTranslate2-oriented runtime details | ARCH-ASR, ARCH-RUNTIME, ARCH-PORTS |
| Duplicate processing/config signature concepts; field sets differ and omit complete provenance | DOMAIN-PROVENANCE, ARCH-CONFIG, DATA-JOB, DATA-TRANSCRIPT |
| Snapshot provenance records only a subset of actual runtime/backend/fallback facts | DOMAIN-PROVENANCE, DATA-TRANSCRIPT, ARCH-RUNTIME, ARCH-ASR, ARCH-DIAR |
| `RenderMarkdownStep` can complete after swallowing canonical snapshot persistence failure | DATA-INTEGRITY, DATA-TRANSCRIPT, FUNC-PROCESS, FUNC-DELIVERY, NFR-RELIABILITY |
| Retention can unlink `source_url`/`audio_path`/`log_path` without clearing durable references | DATA-INTEGRITY, DATA-RETENTION, DATA-JOB, DATA-MEDIA, SEC-FILES |
| Staging/downloaded/converted media were explicit approved data classes but absent from old tree | DATA-MEDIA, DATA-RETENTION, OPS-STARTUP, NFR-RESOURCE |
| Model/tokenizer/cache data were explicit approved data classes but absent from old tree | DATA-CACHE, FUNC-MAINT, SEC-SUPPLYCHAIN, NFR-RESOURCE |
| Central JSONL/application logs are append-only without an explicit bounded lifecycle | DATA-OPSLOG, DATA-RETENTION, NFR-RESOURCE/OBS, SEC-PRIVACY |
| Operational-error loading reads accumulated JSONL before applying recent-result limit | DATA-OPSLOG, NFR-RESOURCE, FUNC-DIAG |
| Sanitization logic is duplicated between application sanitizer and execution-audit logger | SEC-SANITIZE, ARCH-OPS, NFR-MAINTAIN |
| General `AppSettings` carries raw provider secrets and performs environment/filesystem loading inside application | ARCH-CONFIG, SEC-SECRETS, SEC-BOUNDARY, ARCH-COMPOSITION |
| Hugging Face tokenizer may be configured with `trust_remote_code`; model/tokenizer/dependency trust was not explicit in old tree | SEC-SUPPLYCHAIN, DATA-CACHE, ARCH-TEXTGEN, SEC-EXTERNAL |
| Summary tokenizer code directly imports `transformers` when requested/available, but `transformers` is not a declared direct project dependency; availability currently depends on transitive environment state or fallback | SEC-SUPPLYCHAIN, ARCH-TEXTGEN, ARCH-CONFIG, NFR-PORTABILITY |
| Transcript/provider text is untrusted data when passed to text-generation workflows; prompting must not grant it control over security/policy or unintended disclosure | SEC-INPUT, SEC-EXTERNAL, ARCH-TEXTGEN, FUNC-SUMMARY |
| Authorized operator input can still contain hostile/malformed URL/media/filename/provider content | SEC-INPUT, FUNC-SOURCE, FUNC-VIDEO, DATA-MEDIA, SEC-FILES |
| Generic `FileStorage` abstraction has no demonstrated runtime contract | ARCH-PORTS, NFR-MAINTAIN |
| Empty speculative domain packages / stale structural promises | NFR-MAINTAIN, ARCH-BOUNDARY |
| Monolithic `AppSettings` taxonomy | ARCH-CONFIG, SEC-SECRETS, NFR-MAINTAIN |
| Primary delivery failure changes Job lifecycle but derivative/retrieval delivery failures should not retroactively fail completed Jobs | FUNC-DELIVERY, DOMAIN-JOB, DATA-OPSLOG, NFR-RELIABILITY |
| Summary completion participates in search-index refresh; old traceability omitted that dependency | FUNC-SUMMARY, DATA-DERIVED, DATA-SEARCH, FUNC-SEARCH |
| Rename persists speaker aliases in Job and refreshes Markdown/search; old traceability omitted durable Job alias dependency | FUNC-EDIT, DATA-JOB, DATA-TRANSCRIPT, DATA-MARKDOWN, DATA-SEARCH |
| Telegram authorization checks only `user_id` while replies/artifacts target the incoming `chat_id`; an authorized user in a shared chat may expand the disclosure audience | SEC-AUTH, SEC-PRIVACY, ARCH-TRANSPORT, FUNC-DELIVERY |
| Current runbook standard backup copies systemd env and `.env`, contradicting approved security spec that excludes reusable credentials by default | SEC-SECRETS, DATA-BACKUP, OPS-BACKUP, NFR-COMPAT |
| Installation manual defines supported Linux environments, system prerequisites, `uv` bootstrap, ML dependencies and secret provisioning; these are operational premises rather than a product command | OPS-SERVICE, NFR-PORTABILITY, ARCH-COMPOSITION, ARCH-CONFIG, SEC-SECRETS, SEC-SUPPLYCHAIN |
| systemd unit is non-root-user oriented but host hardening/permission assumptions require explicit operational verification | OPS-SERVICE, SEC-FILES, SEC-SECRETS, NFR-PORTABILITY |
| Current private-production rehearsals remain unexecuted | OPS-SERVICE, OPS-BACKUP, OPS-UPGRADE, OPS-RECOVERY, OPS-EVIDENCE |
| Documentation/roadmap drift (CI listed as future; old validation counts/source-of-truth wording) | FUNC-INTERFACE, NFR-COMPAT, OPS-EVIDENCE |
| Project/package metadata still describes the product as YouTube-only although Telegram audio is a current supported source | DOMAIN-MEDIA, FUNC-INTERFACE, NFR-MAINTAIN, NFR-COMPAT |
| Frozen UC-004 originally called numeric history indexes “stable”, while current selection recomputes current completed-history ordering and indexes may shift | UC-004 v1.0.1 clarification; FUNC-HISTORY, NFR-COMPAT |
| 46 environment-gated tests required inventory before REQ derivation | EVIDENCE-INVENTORY.md; associated DATA/OPS/FUNC/ARCH branches |

| `Job.requested_chat_id` is Telegram-specific delivery-routing data stored in the domain entity | DOMAIN-JOB, DATA-JOB, ARCH-TRANSPORT, ARCH-APP, NFR-MAINTAIN |
| Job-to-snapshot association is inferred from Markdown slug/path rather than an explicit durable canonical-transcript reference | DATA-JOB, DATA-TRANSCRIPT, DATA-INTEGRITY, DOMAIN-PROVENANCE, ARCH-TRANSCRIPT |
| WhisperX adapter silently relabels an ASR-detected language outside the allowlist as the first allowed language | DOMAIN-TRANSCRIPT, DOMAIN-PROVENANCE, ARCH-ASR, FUNC-PROCESS, NFR-RELIABILITY |
| YouTube metadata adapter invents English when source language is unknown, bypassing the pipeline's intended unknown-language path | DOMAIN-TRANSCRIPT, DOMAIN-PROVENANCE, FUNC-SOURCE, FUNC-PROCESS, ARCH-ASR |
| Missing YouTube duration is represented as zero, which can bypass the configured duration guard | FUNC-SOURCE, FUNC-PROCESS, DATA-MEDIA, NFR-RESOURCE |

## Conclusion

After adding the new requirement families and traceability above, every material current-code deviation, approved data class, frozen behavior, operational obligation, and security surface found in this review has an explicit requirement-family home. The tree still does not claim the code already satisfies those requirements; those mismatches become atomic hardening requirements after approval.
