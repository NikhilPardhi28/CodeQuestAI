# Product requirements and software requirements

**Status:** proposed baseline, 2026-10-11. This is a planning artifact, not a claim of implemented behavior.

## 1. Product requirements document

### Vision

CodeQuest AI is a third-person educational RPG in which learners acquire Python skills by exploring a connected world, solving code challenges, and applying concepts to quests, traversal, and encounters. A tutor supports learner reasoning without becoming the source of truth for grades, rewards, or progression.

### Users and jobs

- **Learner:** explore, practice Python, receive useful hints, see mastery and quest progress, and resume progress safely.
- **Teacher:** organize learners into classes, assign curriculum, inspect progress and misconceptions, and support learners without seeing unnecessary secrets or raw sensitive data.
- **Administrator:** manage accounts, content publication, service health, roles, audit events, and tenant configuration.
- **Operator/developer:** run services locally, diagnose failures, deploy reproducibly, and evolve content and APIs safely.

### Product outcomes and measures (targets to validate)

- Learners can complete a concept-aligned challenge loop: understand goal → author Python → receive deterministic result → reflect/iterate → earn validated progress.
- At least 90% of accepted learner submissions receive a clear outcome within the challenge's published time budget (TBD per tier); track p50/p95 latency and timeout rate.
- For each curriculum objective, report attempts, completion, hint use, and delayed mastery; do not equate a single correct answer with mastery.
- Service availability, abuse limits, privacy retention, accessibility conformance, and learning efficacy targets require stakeholder confirmation before launch.

### Scope

**In scope:** Unity 6/URP client; sixteen curriculum regions and their connecting progression; third-person movement and traversal; code challenges backed by actual Python execution; quests, NPCs, combat and code abilities; inventory/economy/progression; persistence; adaptive tutoring; teacher/admin web dashboards; secure backend and execution service; optional multiplayer designed behind an abstraction.

**Out of initial delivery scope:** shipping every planned region in the first slice; unrestricted user-generated executable content; production multiplayer before core single-player/account/data boundaries are proven; any claim of efficacy without evaluation; paid provider commitments before cost and privacy review.

### Product constraints

- Local development must be practical on Windows with 16 GB RAM.
- Prefer free/open-source dependencies. Provider selection, cloud host, jurisdiction, exact consent model, and final launch scale are TBD.
- Unity client must not contain model-provider credentials or authority to grant rewards.
- Initial audience is secondary/tertiary learners (older teens and adults). Production student accounts, classroom analytics, and external AI processing remain disabled until jurisdiction, consent/age model, retention/deletion, and school obligations are reviewed. See [ADR-0007](adr/0007-audience-and-privacy-gate.md).
- AI provider and networking provider must be replaceable behind interfaces.

## 2. Software requirements specification

Priority labels: **M** must for a production-capable foundation; **S** should; **C** could. Exact service-level targets are TBD.

### Functional requirements

| ID | Priority | Requirement |
|---|---|---|
| FR-01 | M | Client loads versioned world/content definitions and presents a connected region map with explicit unlock conditions. |
| FR-02 | M | Player traverses with third-person movement, camera, checkpoints, and deterministic challenge entry/exit. |
| FR-03 | M | Challenge runner accepts Python source and challenge-scoped input; returns structured stdout, result status, timing, and test summary. |
| FR-04 | M | Challenge definitions support examples, visible instructions, hidden tests, time/resource limits, output validation, hints, scoring, and versioning. |
| FR-05 | M | Backend validates attempt ownership, challenge version, result provenance, score, reward, and progression before persistence. |
| FR-06 | M | Tutor gives staged hints grounded in challenge/learner context; cannot submit code, execute code, or award progress. |
| FR-07 | M | Save/load preserves versioned player profile, quest state, validated progression, and inventory with conflict handling. |
| FR-08 | M | Server-side authorization separates learner, teacher, and administrator actions and scopes teacher data to assigned classes. |
| FR-09 | S | Quests, dialogue, enemies, bosses, combat abilities, equipment, crafting, economy, and achievements are data-driven. |
| FR-10 | S | Teacher views assignment, progress, mastery evidence, and bounded learner analytics. |
| FR-11 | S | Admin manages content lifecycle, roles, operational health, and auditable administrative actions. |
| FR-12 | S | Optional multiplayer supports presence/co-op initially; any competitive results are server-authoritative. |
| FR-13 | M | Settings include input/audio/display and accessibility options; UI adapts to target resolutions and input devices. |

### Quality attributes

| ID | Requirement |
|---|---|
| QR-01 Security | Untrusted code executes in a disposable isolation boundary with CPU, memory, process, output, and wall-clock limits; no unrestricted network, host filesystem, container socket, or secrets. |
| QR-02 Integrity | Client and AI output are untrusted. Reward/progression decisions are reproducible, server-validated, and auditable. |
| QR-03 Availability | Each service fails independently with bounded timeouts, health/readiness checks, retries only for idempotent operations, and useful user-facing errors. Targets TBD. |
| QR-04 Performance | Establish and measure frame-time, memory, load-time, API latency, execution queue, and concurrent-user budgets before content scale-up. Initial budgets are proposed in document 06. |
| QR-05 Maintainability | Modular Unity assemblies, typed versioned API schemas, migrations, code review, lint/format rules, and documented local workflows. |
| QR-06 Accessibility | Keyboard/controller remapping, subtitles, readable contrast and text scaling, non-color-only signals, difficulty/assist options; conformance target TBD. |
| QR-07 Privacy | Minimize learner data, define retention/deletion/export, consent and school/guardian requirements before collecting analytics or using external AI. Jurisdiction TBD. |
| QR-08 Portability | Run a supported local compose profile on Windows via Docker Desktop; use replaceable interfaces for external providers. |

### Interfaces and error behavior

- **Unity ↔ BackendAPI:** HTTPS JSON API, OpenAPI-described, bearer session token, request/correlation ID; typed error envelope (`code`, safe `message`, `retryable`, `correlationId`). Refresh and offline behavior TBD.
- **BackendAPI ↔ Python worker:** authenticated internal job protocol, signed/opaque attempt ID, strict schema, bounded queue and deadline; worker returns structured outcome, never an authorization decision.
- **BackendAPI ↔ AIService:** internal typed tutor request/response with token/time limits, safety filters, provider-independent error mapping, and deterministic fallback hints.
- **Services ↔ PostgreSQL:** private network, least-privilege service accounts, parameterized queries, migrations; no service exposes direct database access to client.
- **Dashboards ↔ BackendAPI:** same versioned API; server-side role and tenant/class authorization on every resource.

All boundaries must handle invalid payloads, unauthorized access, stale versions, duplicate requests, timeouts, dependency outage, rate limits, and partial failure. Never report success until the authoritative state transition commits.

### Acceptance criteria for foundation

1. Repository setup and component responsibilities are documented; dependency versions are pinned when implementation begins.
2. A learner can authenticate, load a region/challenge, submit code to isolated execution, view a structured result, and receive only backend-validated progress.
3. Hidden tests and reward rules cannot be downloaded from the client bundle or changed by the client.
4. AI provider failure does not block deterministic challenge evaluation; tutor text cannot mutate account state.
5. Teacher cannot access learners outside authorized classes; admin actions are audited.
6. Migrations can create a clean database and upgrade a supported prior schema with rollback/recovery guidance.
7. Automated checks cover contracts, authorization, worker containment, state transitions, and a playable client vertical slice before release.

## 3. Assumptions and questions

Assumptions: initially single-player first; internet connection required for authoritative submission; curriculum is English-first; learner progress is account-backed. Confirm target ages, school/consumer deployment, supported platforms, offline requirements, regions/languages, accessibility target, privacy jurisdictions, classroom tenancy model, and acceptable AI-provider data handling before production design is frozen.
