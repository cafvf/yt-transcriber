# Baseline Architecture Specification

Version: **1.0.0**
Status: **Approved**
Baseline date: **2026-08-15**

## 1. Architectural intent

The system follows Hexagonal Architecture / Ports & Adapters.

This specification distinguishes target architecture from observed deviations. Deviations are not acceptable merely because tests pass.

## 2. Logical layers

### Domain

Owns entities, value objects, invariants, state semantics, and pure domain policies.

It must not require filesystem state, environment variables, network services, provider credentials, SQLite, Telegram, YouTube clients, ffmpeg, WhisperX/pyannote, or LM Studio/OpenAI-compatible clients.

### Application

Owns use-case orchestration, pipeline policy, application services, and ports required by business flows.

It may depend on domain abstractions but not concrete infrastructure adapters.

### Infrastructure

Owns technology-specific implementations: Telegram, YouTube/yt-dlp, ffmpeg, persistence, filesystem, WhisperX/pyannote, GPU/runtime adapters, OpenAI-compatible transport, tokenizer/model integration, and logging mechanisms.

### Composition/runtime

Owns wiring and runtime startup.

## 3. Dependency rule

```text
domain          -> stdlib + domain
application     -> stdlib + domain + application
infrastructure  -> stdlib + domain + application + infrastructure
composition     -> all layers
```

Application→infrastructure and domain→infrastructure dependencies are prohibited.

The rule must become executable through architecture tests or an equivalent check before this milestone closes.

## 4. Ports

A port expresses an application capability, not a provider API.

Ports should avoid provider credentials, provider-specific options that are not application concepts, concrete repository/renderer classes, transport payloads unrelated to the use case, and implementation-specific lifecycle details.

## 5. Adapters

Adapters translate external mechanisms into application/domain abstractions.

A transport adapter may handle transport mechanics, boundary authorization, transport-specific message composition, and conversion of incoming payloads into application requests. It should not become a parallel application layer.

## 6. Composition root

Concrete dependencies are selected and wired in composition/runtime.

Secrets and provider-specific configuration are resolved at or near composition/infrastructure boundaries rather than passed through domain objects.

## 7. Pipeline

Conceptually:

```text
YouTube
  -> metadata/subtitle decision/acquisition
                      \
                       -> common processing -> artifacts -> delivery

Telegram audio
  -> validated/staged media
                      /
```

The common pipeline must not force all sources through YouTube-specific concepts.

## 8. Persistence and search boundaries

Job lifecycle persistence and history/search indexing are separate application capabilities.

A single concrete infrastructure adapter may temporarily implement more than one explicit interface, but repository semantics must remain distinct:

- lifecycle persistence owns durable Job state and Job queries required by application behavior;
- transcript/artifact storage owns canonical transcript evidence;
- indexing owns transformation of canonical evidence into searchable documents;
- history search owns query semantics over the index.

A lifecycle repository must not read arbitrary transcript/summary files merely to maintain a search index as a hidden side effect.

## 9. Text-generation boundary

Summarization is application/product behavior. OpenAI-compatible HTTP transport is infrastructure.

Application owns transcript selection/preparation, chunking/orchestration policy, prompt/application semantics, output-language policy, merge/reduction policy, derived-artifact semantics, and application-level handling of partial work.

Infrastructure owns network protocol, endpoint/client details, authentication, provider request/response translation, and concrete tokenizer/model-library integration. Network-level retry/timeout mechanism may live in infrastructure while application-level fallback/splitting policy remains inward.

A generic text-generation capability introduced for this separation must be justified by current summarization needs; it must not encode future translation behavior before translation is specified.

## 9.1 ASR boundary

The application transcription contract expresses application concepts: transcribable audio input, language hint/constraint, cancellation/progress, requested processing profile where required, and a structured transcription result.

Provider/runtime details that exist only because of WhisperX/faster-whisper/CTranslate2—such as provider-specific compute modes—must not define the generic application contract unless promoted to a genuinely backend-independent execution policy.

Actual backend, model, runtime/fallback facts needed for provenance remain observable outputs/metadata.

## 9.2 Telegram boundary

Telegram infrastructure owns Bot API mechanics, Telegram payload parsing, command/message translation, transport-specific presentation, inline UI state, transport authorization checks, and Telegram delivery mechanics.

Application owns decisions that remain meaningful without Telegram, including submission/deduplication semantics, job lifecycle, cancellation semantics, search, rename, summary/export orchestration, retention decisions, and the semantic result of artifact delivery.

A Telegram adapter must not be the sole owner of application rules merely because Telegram is the current UI.

## 9.3 Configuration boundary

The external operator configuration surface remains backward compatible during this baseline unless a breaking migration is explicitly specified.

Internal settings may be grouped by concern without forcing external environment-variable renames. Historical names that are misleading may be supported as compatibility aliases while code-facing concepts adopt truthful taxonomy.

Credentials are not ordinary behavior configuration and follow the separate security rules in the Constitution and `SECURITY-AND-OPERATIONS.md`.

## 10. Known baseline deviations

1. application pipeline code imports infrastructure text normalization and concrete rendering/snapshot types;
2. rename-speakers application service depends on concrete infrastructure snapshot and Markdown renderer implementations;
3. application use-case typing references a concrete snapshot repository;
4. `ModelName` includes filesystem-state validation and runtime/backend policy inappropriate for a pure domain value object;
5. the diarization port transports `hf_token`, leaking an adapter credential into the application contract;
6. summarization policy is concentrated under infrastructure despite containing application workflow decisions;
7. the SQLAlchemy job repository combines lifecycle persistence, history search, FTS concerns, and artifact loading;
8. `TelegramBotAdapter` contains substantial orchestration beyond transport concerns;
9. the ASR/transcription port exposes runtime concepts strongly coupled to Whisper/faster-whisper/CTranslate2;
10. configuration fingerprint/signature logic overlaps and needs one canonical owner;
11. empty/unrealized domain packages create architectural promises without clear behavior;
12. the generic `FileStorage` abstraction has no demonstrated runtime application contract; it is constructed/exposed by composition but not consumed by the main runtime and should be removed during baseline cleanup unless contrary evidence is found before implementation.

## 11. Refactoring constraints

Architecture repair must preserve approved observable behavior, use characterization/regression tests, introduce ports only for real capability boundaries, avoid speculative abstractions, avoid unrelated feature work, and maintain data compatibility unless a migration is separately approved.

## 12. Baseline completion condition

This architecture baseline closes when:

- known application→infrastructure violations and domain infrastructure leakage are removed;
- dependency direction is executable and enforced;
- transport adapters no longer own application orchestration;
- text-generation policy is separated from provider transport;
- lifecycle persistence, transcript storage, indexing, and search have explicit semantic ownership;
- configuration provenance has one canonical application concept;
- generic media/application contracts no longer inherit obsolete YouTube/video assumptions;
- provider credentials remain confined to approved boundary components;
- compatibility impacts are explicitly migrated or preserved rather than changed accidentally.
