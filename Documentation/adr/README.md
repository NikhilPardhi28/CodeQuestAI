# Architecture decision records

ADRs distinguish accepted decisions from proposals. Create one numbered file per decision; once accepted, preserve it and supersede rather than rewrite it. Accepted decisions are listed below; proposals remain explicitly marked.

## ADR index

| ID | Decision | Status |
|---|---|---|
| 0001 | Unity 6 with URP for the game client | Proposed |
| 0002 | FastAPI modular monolith for authoritative backend | Proposed |
| 0003 | PostgreSQL as persistent system of record | Proposed |
| 0004 | Isolated disposable Python execution service | Proposed |
| 0005 | Replaceable AI and networking provider ports | Proposed |
| 0006 | Server-authoritative progression and rewards | Proposed |
| 0007 | Secondary/tertiary audience and privacy launch gate | Accepted |
| 0008 | Windows 10/11 x64 initial platform | Accepted |
| 0009 | Installed Unity editor patch 6000.3.19f1 | Accepted |
| 0010 | OIDC identity boundary, provider deferred | Accepted |
| 0011 | Per-job restricted Linux container for Python execution | Accepted |

See [ADR-0007](0007-audience-and-privacy-gate.md), [ADR-0008](0008-initial-platforms.md), [ADR-0009](0009-unity-editor-version.md), [ADR-0010](0010-identity-provider-boundary.md), and [ADR-0011](0011-python-execution-isolation.md).

## ADR-0001 — Unity 6 with URP

**Status:** Proposed · **Date:** 2026-10-11

### Context

The project requires a 3D third-person educational RPG and explicitly specifies Unity 6 and URP.

### Decision

Target Unity 6 with URP. Pin the installed editor patch and package lock before implementation. Modular runtime assemblies; keep editor tools in editor-only assemblies.

### Consequences

Uses the required 3D ecosystem; requires editor availability/licensing verification, content/performance profiling, and disciplined assembly boundaries. The installed exact editor patch is recorded by ADR-0009.

## ADR-0002 — FastAPI modular monolith

**Status:** Proposed · **Date:** 2026-10-11

### Context

Python is required for API/AI/execution integration; early scale and team size are unknown.

### Decision

Start BackendAPI as a modular FastAPI application with domain module boundaries. Keep AI and untrusted execution in separate processes/services.

### Consequences

Simplifies local development and transactional operations; modules require dependency rules to prevent a tangled monolith. Split only when measurable isolation or scaling need outweighs operations cost.

## ADR-0003 — PostgreSQL system of record

**Status:** Proposed · **Date:** 2026-10-11

### Context

The system needs transactional accounts, progression, attempts, assignments, and audit data.

### Decision

Use PostgreSQL with versioned migrations and least-privilege service accounts. Keep cache/analytics technology undecided until needed.

### Consequences

Supports relational integrity and local open-source operation; requires migration, backup, restore, and privacy retention practices.

## ADR-0004 — Isolated Python execution service

**Status:** Proposed · **Date:** 2026-10-11

### Context

Players must run real Python, including adversarial untrusted submissions.

### Decision

Execute each attempt in a disposable, resource-bounded worker isolated from API/database/secrets and without network access. Worker returns evidence; backend owns test interpretation and rewards. Container runtime details require host threat review.

### Consequences

Improves fault and security containment, but is not safe merely because it uses containers. Requires adversarial tests, image maintenance, quotas, worker operations, and no-network verification before pilot.

## ADR-0005 — Replaceable AI and networking ports

**Status:** Proposed · **Date:** 2026-10-11

### Context

AI-compatible model provider and multiplayer network provider are intentionally undecided and must not couple core systems.

### Decision

Define typed provider-neutral interfaces and keep provider SDKs in adapter modules. Provider selection requires privacy, age, cost, latency, and operational review.

### Consequences

Reduces lock-in; abstraction can constrain provider-specific capabilities and needs contract tests. No provider credentials enter Unity.

## ADR-0006 — Server authority for progress and rewards

**Status:** Proposed · **Date:** 2026-10-11

### Context

Client modification, replay, AI uncertainty, and hidden-test disclosure threaten learning and game integrity.

### Decision

Backend validates attempts and owns score, mastery evidence, progression, inventory, economy, and competitive results. AI supplies advice only.

### Consequences

Supports auditable results and provider-independent tutoring; requires connectivity, robust idempotency, and careful failure UX. Offline authoritative play remains unresolved.
