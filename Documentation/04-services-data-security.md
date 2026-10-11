# Services, APIs, data model, and security architecture

**Status:** proposed broader service architecture with implemented v1 catalog/player routes and additive v2 authoritative quest routes. Routes listed below that are absent from the [route inventory](api/README.md) remain illustrative/planned; generated wire contracts are [OpenAPI v1](api/openapi-v1.json) and [OpenAPI v2](api/openapi-v2.json). Requirements context: [software requirements](01-product-requirements.md#2-software-requirements-specification), especially its quality attributes, interfaces, and security/privacy requirements.

**Implementation note (2026-10-11):** the first `/api/v1` routes and schema are implemented and the generated contract is at [api/openapi-v1.json](api/openapi-v1.json). Current route behavior and limitations are listed in [api/README.md](api/README.md). The initial migration is under `Database/migrations/versions/`; the ERD below remains the broader planned logical model, not a claim that every depicted table exists.

## 1. Backend service boundaries

```text
BackendAPI (FastAPI modular monolith initially)
  identity/authorization
  learner_profiles/progression
  challenge_catalog/submissions
  quests/inventory/economy
  classes/assignments/analytics
  content_admin/audit
  adapters: PostgreSQL, AIService, execution jobs, telemetry
AIService (separate policy/provider boundary)
PythonExecutionService (separate worker/container boundary)
```

Begin as a modular monolith for transactional state and local simplicity. Split services only when isolation/scaling/ownership justifies operational cost. AI and execution remain separate processes from the API due to distinct failure and security boundaries.

### Backend responsibilities

- Validate identity/session, tenant/class scope, request schemas, role and ownership.
- Own authoritative state transitions, transaction boundaries, deduplication, audit, content versions, and score/reward policy.
- Orchestrate challenge execution and tutor calls with deadlines, quotas, and correlation IDs.
- Never execute submitted code in the API process; never persist unbounded stdout/source by default.

Dependencies: PostgreSQL; internal execution and AI interfaces; external identity and hosting are TBD. Failure: transaction rollback for state mutation, bounded dependency calls, explicit queued/running/completed status for execution, circuit breaker for provider outage. Tests: unit use-case tests, API contract/auth tests, migration tests, failure injection, worker security tests.

## 2. API contract outline

Base `/api/v1`. OpenAPI generated from typed request/response models and checked into release artifacts.

| Method/path | Purpose | Authority/idempotency |
|---|---|---|
| `GET /me` | current profile and capability summary | authenticated learner |
| `GET /world/map` | visible region graph and unlock projection | server filters hidden content |
| `GET /challenges/{id}` | visible challenge definition/examples/hint policy | never returns hidden tests/reward secrets |
| `POST /challenge-attempts` | create execution attempt | learner-owned; idempotency key; challenge version pinned |
| `GET /challenge-attempts/{id}` | poll structured execution status/result | attempt ownership enforced |
| `POST /tutor/hints` | request next hint for attempt/objective | quotas; tutor cannot mutate progression |
| `GET /progress` | mastery/quest state projection | account-scoped |
| `POST /quests/{id}/actions` | record a permitted action intent | backend validates preconditions and reward |
| `GET /inventory`; `POST /inventory/equip`; `POST /crafting` | read and mutate equipment/crafting | ownership, cost, quantity, replay checks |
| `GET /teacher/classes/{id}/progress` | class-scoped report | teacher assignment + class membership check |
| `/admin/content/*` | content draft/review/publish | admin capability, audit trail, version immutable after publish |

Envelope fields: `requestId`, `createdAt`, versioned resource IDs. Errors use stable machine code, localized-safe message key, retryability, correlation ID. Pagination, filtering, rate limits, token refresh, and offline policy TBD.

Challenge flow: API validates learner, content version, quota, and visible payload; creates attempt/job record; worker executes in isolation; API verifies signed/internal result correlation; evaluator validates required tests and deterministic rubric; one transaction stores outcome plus bounded reward/progression events; client polls and displays. Duplicate request returns same attempt; stale version is rejected with current visible version. Hidden tests never reach Unity.

## 3. ER model

```mermaid
erDiagram
  USER ||--o{ ENROLLMENT : has
  CLASSROOM ||--o{ ENROLLMENT : contains
  USER ||--o{ ROLE_ASSIGNMENT : receives
  USER ||--|| PLAYER_PROFILE : owns
  PLAYER_PROFILE ||--o{ QUEST_STATE : tracks
  QUEST ||--o{ QUEST_STATE : defines
  PLAYER_PROFILE ||--o{ CHALLENGE_ATTEMPT : submits
  CHALLENGE ||--o{ CHALLENGE_ATTEMPT : versioned_as
  CHALLENGE_ATTEMPT ||--o{ HINT_EVENT : requests
  PLAYER_PROFILE ||--o{ MASTERY_RECORD : demonstrates
  LEARNING_OBJECTIVE ||--o{ MASTERY_RECORD : measured_for
  PLAYER_PROFILE ||--o{ INVENTORY_ITEM : owns
  ITEM_DEFINITION ||--o{ INVENTORY_ITEM : instantiates
  CLASSROOM ||--o{ ASSIGNMENT : issues
  CHALLENGE ||--o{ ASSIGNMENT : references
  USER ||--o{ AUDIT_EVENT : actor
  PLAYER_PROFILE ||--o{ PROGRESSION_EVENT : receives
  USER { uuid id PK; string subject_id UK; string status; datetime created_at }
  CLASSROOM { uuid id PK; string name; uuid owner_user_id FK }
  ENROLLMENT { uuid classroom_id PK,FK; uuid learner_id PK,FK; string status }
  ROLE_ASSIGNMENT { uuid user_id PK,FK; string role PK; uuid scope_id PK }
  PLAYER_PROFILE { uuid user_id PK,FK; int schema_version; json settings; datetime updated_at }
  QUEST { uuid id PK; int version PK; string region_id; json definition }
  QUEST_STATE { uuid user_id PK,FK; uuid quest_id PK,FK; int quest_version PK,FK; string status; json state }
  CHALLENGE { uuid id PK; int version PK; string objective_id; json public_definition; bytea private_tests_ref }
  CHALLENGE_ATTEMPT { uuid id PK; uuid user_id FK; uuid challenge_id FK; int challenge_version; string status; json result; datetime submitted_at }
  HINT_EVENT { uuid id PK; uuid attempt_id FK; int ordinal; string hint_id; datetime created_at }
  LEARNING_OBJECTIVE { string id PK; string title; json prerequisites }
  MASTERY_RECORD { uuid user_id PK,FK; string objective_id PK,FK; json evidence; decimal estimate; datetime updated_at }
  ITEM_DEFINITION { string id PK; int version PK; json definition }
  INVENTORY_ITEM { uuid user_id PK,FK; string item_id PK,FK; int quantity; json state }
  ASSIGNMENT { uuid id PK; uuid classroom_id FK; uuid challenge_id FK; int challenge_version; datetime due_at }
  PROGRESSION_EVENT { uuid id PK; uuid user_id FK; string event_type; json payload; datetime created_at }
  AUDIT_EVENT { uuid id PK; uuid actor_user_id FK; string action; string target; json metadata; datetime created_at }
```

Logical ERD only; the first migration implements player profiles, versioned curriculum/quest/challenge/achievement definitions, quest progress, submission metadata, progression, and achievement awards. Classroom/assignment, enrollment, mastery, inventory, audit, and event tables remain planned. Physical partitioning, retention, exact types, multi-tenant isolation, and identity provider are TBD. The initial profile maps one configured OIDC issuer's `sub` claim to its profile; multiple issuers/account linking require an explicit follow-up schema decision. Never put plaintext credentials, provider API keys, or unrestricted submitted source in general analytics tables.

## 4. Migration plan

- Use Alembic migrations under `Database/migrations/versions/` (initial migration `20261011_0001` is implemented).
- One migration per compatible schema transition; immutable revision IDs, review required, forward/backfill strategy, tested fresh install and upgrade path.
- Expand/contract for deployments with rolling versions. Avoid destructive column removal in same release as new code deploy.
- Seed only non-sensitive reference/catalog data; keep environment secrets out of seed files.
- Document backup/restore and recovery-point objectives before production. See [database setup and migration commands](../Database/README.md).

## 5. AI tutor and adaptive learning

Tutor request context is minimized: challenge objective/version, current hint stage, learner's explicit question, and optionally a bounded error category. Raw code inclusion must be opt-in and evaluated against provider data policy; never send credentials or personal profile. Provider abstraction: `TutorProvider.complete(TutorRequest)->TutorResponse`; provider adapters have deadlines, token caps, structured output parsing, refusal/error mapping, and telemetry with redaction.

Hint ladder: (1) restate goal, (2) point to relevant concept, (3) ask a diagnostic question, (4) suggest a small next step or pseudocode, (5) provide a near-solution only when pedagogically approved. Hints should not reveal hidden tests. AI output is plain display text passed through policy/length checks; never evaluate it as code or use it for reward/mastery. Deterministic fallback provides authored hints when AI is unavailable. Track recommendation efficacy and hint depth; learner/teacher can report unsuitable output. Model/provider choice, retention policy, age controls, and assessment protocol TBD.

Adaptive mastery uses transparent evidence features (attempt outcome, recency, item difficulty, hint depth, spaced retrieval); recommendation model starts with rules and remains explainable. Any statistical model is advisory, evaluated for calibration and group disparities, and cannot make high-stakes decisions.

## 6. Secure Python execution

The execution service is a separate, disposable worker pool. Prefer a hardened container runtime with a non-root user, read-only root filesystem, no network namespace access, no host mounts, no Docker socket, dropped capabilities, seccomp/AppArmor/Windows-compatible deployment decision, cgroup CPU/memory/pids quotas, wall-clock timeout, bounded stdout/stderr, and per-job temp directory destroyed after completion. Disable dangerous imports and provide only approved standard library/data packages via pinned image. A container alone is not assumed sufficient; production isolation strength and host OS require a threat review. Consider gVisor/Firecracker only if supported operationally; no paid dependency assumed.

Submission input is size-capped; run with fixed interpreter and environment, no shell interpolation, no secrets, no database access. Hidden tests remain service-side; evaluator compares structured output/return values using challenge-specific policy. Kill process tree on timeout; classify syntax/runtime/timeout/resource/internal errors distinctly; avoid leaking hidden test data or host paths in feedback. Queue quotas protect availability. Record image digest, challenge version, worker version, resource use, and result signature for provenance. Security tests include filesystem/network escape attempts, fork bomb, memory/CPU exhaustion, output flood, import abuse, timeout cleanup, cross-job contamination, and malicious payloads.

## 7. Identity, authorization, and save data

Use an OIDC-compatible identity provider behind an adapter; provider selection is deferred until privacy and hosting decisions. Validate issuer, audience, signature, expiry, and scopes; store stable subject identifier and application roles, never delegated provider passwords. Local development uses synthetic identities or a clearly isolated local OIDC development provider, with no production bypass. Short-lived access tokens, secure refresh storage, rotation/revocation, CSRF protection for cookie-based dashboards, and TLS are required. RBAC roles: learner, teacher, content reviewer, administrator, operator; scopes include account, class, and platform. Every object access checks owner/scope in the backend query path. Admin privilege is separately granted and audited. See [ADR-0010](adr/0010-identity-provider-boundary.md).

Save state is versioned, server-authoritative for progression/inventory, and updated with optimistic concurrency (`revision`/ETag). Cosmetic/local settings can be client-cached; conflict resolution is explicit. Provide deletion/export and retention policy after privacy jurisdiction is chosen. Audit security-sensitive changes without logging secrets or source code.

### Milestone 5 persistence boundary

At Milestone 5, the API exposed profile create/read and read-only progression, quest, achievement, and submission snapshots; Unity quest state was session-local. Milestone 6 adds an additive versioned quest-event API and normalized server-owned objective rules while preserving v1. The exact contract, allowed event types, OIDC ownership, idempotency, optimistic revision conflicts, trusted challenge evidence, and XP reward boundary are documented in [the API contract notes](api/README.md). World interaction/checkpoint events are registered authenticated client reports; they cannot independently award XP. Profile ownership continues to derive only from the validated OIDC subject. Python submission remains an interface only; no code execution is added.

Event receipts are unique by authenticated profile and event UUID and store a canonical payload hash. Same-key/same-payload retries return the stored response; changed payloads conflict. PostgreSQL locks the player/quest revision row before transition, and the reward ledger has a per-player/version/reward unique key. Versioned objective rules validate registered targets, published challenge versions, and acyclic prerequisites. One transaction stores the event response, progress revision, reward ledger, and progression update. See [ADR-0012](adr/0012-authoritative-quest-event-ledger.md).

Interaction and checkpoint sources remain client reports. Registered targets and server rules prevent arbitrary target/reward claims but do not prove physical location or interaction. XP requires completion of a quest with trusted passed-challenge evidence; challenge submission/evaluation is not implemented. Event receipts are retained until account deletion or an approved policy change. Unity retries a bounded 32-event in-memory queue with the same UUID; restart loses unconfirmed events and they are never shown as cloud-saved. Timeouts preserve the original request for retry; stale revision conflicts use the supplied authoritative snapshot before retry.

Execution isolation and threat controls are recorded in [ADR-0011](adr/0011-python-execution-isolation.md). Production use is gated on host/runtime review and adversarial verification; provisional resource limits are listed in that ADR and in the quality plan.
