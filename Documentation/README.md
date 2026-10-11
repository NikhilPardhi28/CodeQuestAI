# CodeQuest AI architecture baseline

**Status:** architecture baseline, backend foundation, and first Unity runtime/API client scaffold, 2026-10-11. The repository has API contracts, an initial migration, seed catalog, backend tests, and Unity runtime source/package pins. Unity package resolution, URP/scene generation, compilation, and Test Runner execution await an active editor license. These documents still describe many planned systems rather than implemented features. `TBD` items are unresolved product/engineering choices; do not silently treat proposals as requirements.

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

The original inventory found empty component directories and no commits. The repository baseline adds root conventions/configuration, a pinned Python dependency project and `uv.lock`, validators, and CI. The backend foundation now adds FastAPI routes, SQLAlchemy models, Alembic migration, seed content, and API/database tests. There is still no Unity project/package manifest, Python execution worker, or dashboard package. `master` still has no commits, and no repository-specific `AGENTS.md` files were present at inspection.

Host tool discovery on 2026-10-11: Git 2.54.0.windows.1, Python 3.11.9, .NET SDK 10.0.303, Node 24.15.1, npm 11.12.1, Docker 29.6.1, Unity Editor 6000.3.19f1 at `C:\Program Files\Unity\Hub\Editor\6000.3.19f1\Editor\Unity.exe`. uv 0.13.0 was installed for this task to generate the lockfile. Unity is installed, but no Unity project/package manifest exists. These are host observations; Unity patch and Python line are recorded as initial project targets.

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

- Treat all architecture choices as proposals until accepted and recorded in an ADR. Accepted decisions 0007–0011 define the current initial audience/privacy gate, platform, Unity patch, identity boundary, and execution isolation.
- Keep trusted progression/scoring decisions in BackendAPI; AI and client are untrusted inputs.
- Run submitted code in a separate, disposable, resource-bounded worker with no network and no host secrets.
- Deliver a coherent vertical slice before broad content production; the roadmap preserves the full sixteen-region world.
- Keep this blueprint synchronized with implementation and mark delivered capabilities only after verification.
