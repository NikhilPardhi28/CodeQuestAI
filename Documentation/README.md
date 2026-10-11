# CodeQuest AI architecture baseline

**Status:** architecture baseline plus Milestones 5 and 6 foundations, 2026-10-11. The repository contains versioned API contracts, reversible migrations, seed rules, backend service/tests, and Unity runtime source/package pins. The latest Milestone 6 Unity batch invocation could not establish a licensing-client connection, so current Unity compilation and Test Runner results remain unverified. These documents still describe many planned systems rather than implemented features. `TBD` items are unresolved product/engineering choices; do not silently treat proposals as requirements.

## Documents

1. [Product requirements and SRS](01-product-requirements.md)
2. [Game design, world, and curriculum](02-game-world-curriculum.md)
3. [Systems and client architecture](03-systems-and-client-architecture.md)
4. [Services, APIs, data, and security](04-services-data-security.md)
5. [UX, dashboards, analytics, and multiplayer](05-ux-dashboards-multiplayer.md)
6. [Quality, delivery, assets, risks, and roadmap](06-quality-delivery-roadmap.md)
7. [Architecture decision records](adr/README.md)
8. [Contributor and engineering conventions](../CONTRIBUTING.md)
9. [Implemented v1 API contract and route inventory](api/README.md)
10. [Database setup, migrations, and seed data](../Database/README.md)
11. [Milestone 5 reusable gameplay foundation](milestone-5-gameplay.md)
12. [Milestone 6 authoritative quest events](milestone-6-quest-events.md)
13. [Generated OpenAPI v1](api/openapi-v1.json) and [OpenAPI v2](api/openapi-v2.json)

## Proposed documentation manifest

```text
Documentation/
  README.md
  01-product-requirements.md
  02-game-world-curriculum.md
  03-systems-and-client-architecture.md
  04-services-data-security.md
  05-ux-dashboards-multiplayer.md
  06-quality-delivery-roadmap.md
  adr/README.md
```

## Repository inventory at baseline

The initial baseline added root conventions/configuration, a pinned Python dependency project and `uv.lock`, validators, and CI. Later milestones added the nested Unity project, reusable gameplay foundation, FastAPI routes, SQLAlchemy models, two Alembic revisions, versioned quest rules, and tests. Python execution and dashboard packages remain future work. The active branch retains the existing Git history; do not rewrite prior checkpoints.

Host tool discovery recorded Unity Editor 6000.3.19f1 at `C:\Program Files\Unity\Hub\Editor\6000.3.19f1\Editor\Unity.exe`; its exact patch and Python line are recorded in ADR-0009 and project settings. Docker CLI is installed, but the Linux engine is not running in the Milestone 6 environment. Unity licensing and PostgreSQL integration remain environment gates for the current verification run.

## Proposed component manifest

```text
GameClient/                 Unity project (Assets, Packages, ProjectSettings, Tests)
BackendAPI/                 FastAPI application, API schemas, auth, domain use cases
AIService/                  provider-neutral tutor orchestration and prompt policy
PythonExecutionService/     isolated execution worker/image and protocol
AdminDashboard/             React + TypeScript operations UI
TeacherDashboard/           React + TypeScript classroom UI
Database/                   PostgreSQL migrations, seed/reference data, ERD source
Infrastructure/             local compose, deployment/IaC, observability configuration
Tests/                      cross-service contract, security, and acceptance suites
Documentation/              architecture and product baseline
Tools/                      local setup, content validation, developer utilities
```

Each component should own its own build/dependency manifest. Cross-component contracts belong in versioned schemas, not duplicated handwritten DTOs.

## Baseline rules

- Treat all architecture choices as proposals until accepted and recorded in an ADR. Accepted decisions 0007–0012 define the current audience/privacy gate, platform, Unity patch, identity boundary, execution isolation, and authoritative quest event ledger.
- Keep trusted progression/scoring decisions in BackendAPI; AI and client are untrusted inputs.
- Run submitted code in a separate, disposable, resource-bounded worker with no network and no host secrets.
- Deliver a coherent vertical slice before broad content production; the roadmap preserves the full sixteen-region world.
- Keep this blueprint synchronized with implementation and mark delivered capabilities only after verification.
