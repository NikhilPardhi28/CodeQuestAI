# Contributing to CodeQuest AI

This repository has an architecture baseline and an initial backend/API/database foundation. Keep changes small and coherent, preserve approved architecture decisions, and describe proposed changes to public interfaces or data ownership before implementation.

## Toolchain

- Unity editor: **6000.3.19f1** is installed on the inspected workstation. Use that exact editor version. The initial client pins URP 17.3.0, Unity Test Framework 1.6.0, and uGUI 2.0.0 in `GameClient/Packages/manifest.json`; these versions were read from this editor's bundled package manifests. Unity must generate `packages-lock.json` after license activation and Package Manager resolution. Asset `.meta` files are checked in for current source assets; Unity creates metadata for generated scene/settings assets. Input System is not installed; the initial adapter uses legacy input behind an interface.
- Python: 3.11.x; `.python-version` records the inspected 3.11.9 patch. `pyproject.toml` pins direct Python dependencies; `uv.lock` is the committed cross-platform transitive lockfile. uv tooling is pinned to 0.13.0 in CI and should match locally.
- Git, Docker Desktop, and Node are required only for the components being worked on. No frontend manifests or local Compose stack exist yet.

## Setup (PowerShell)

```powershell
py -m pip install --user uv==0.13.0
git clone <repository-url>
cd CodeQuestAI
uv sync --all-groups
Copy-Item .env.example .env
```

Install Unity Hub and Unity 6000.3.19f1 separately. Open `GameClient/` only after Unity project scaffolding is added. Do not use Unity Hub to auto-upgrade project versions. The backend app and initial API/database contracts are implemented; see [backend setup](BackendAPI/README.md) and [database setup](Database/README.md). Docker Desktop is needed for PostgreSQL integration tests; SQLite is used for fast local migration and repository tests.

For local secrets, use ignored `.env` only for non-shared development or a local secret manager. Never put credentials in Git, Unity assets, screenshots, logs, test fixtures, or issue text. Do not copy production data into development.

## Repository layout

See [architecture baseline](Documentation/README.md). Each component owns its runtime code and build configuration. Shared contracts are versioned under their owning API/schema location; do not duplicate hand-maintained wire DTOs.

## Naming and code style

- Paths: `PascalCase` for Unity C# types/files and component directories; `snake_case.py` for Python modules/functions; `PascalCase` for Python types; `camelCase` for JSON properties; stable IDs use lowercase dot-separated names.
- C#: one public MonoBehaviour/ScriptableObject per matching file; namespaces `CodeQuest.<Area>`; private serialized fields `_camelCase`; constants `PascalCase`; explicit asmdef references; runtime code cannot reference `UnityEditor`.
- Python: 4 spaces, type annotations at public boundaries, Ruff formatting/lint rules from `pyproject.toml`; dependency changes update `pyproject.toml` and `uv.lock` together.
- Markdown: descriptive headings, relative links within docs, Mermaid for architecture diagrams, mark proposals/TBD clearly.
- Configuration keys use uppercase `CODEQUEST_` prefix. JSON wire fields are lower camel case and use explicit schema versions.

## Error handling and logging

- Convert expected failures to typed domain/API errors; do not catch broadly and return success-shaped defaults.
- Public errors have stable machine codes and safe messages; internal stack traces remain in restricted logs and are correlated by request ID.
- Logs are structured, levelled, and redacted. Never log tokens, secrets, raw learner source, hidden tests, or full tutor conversations by default.
- Include correlation/attempt IDs where safe; bound user-controlled strings and output. A dependency timeout is an explicit retryable/failed state, never an award.
- Retries require idempotency or read-only semantics; cap attempts and use backoff.

## Testing and validation

- Place tests near their component under its `tests/` directory; shared acceptance/contract tests live under `Tests/`.
- Unit tests are deterministic and do not call external AI or paid services. Integration tests use disposable local dependencies. Security tests for code execution run only in disposable constrained environments.
- Name Python tests `test_*.py`; Unity tests use EditMode/PlayMode asmdefs. Keep fixtures synthetic and secret-free.
- For docs-only changes, validate relative Markdown links and whitespace. For Python changes, run `uv run ruff check .`, `uv run ruff format --check .`, and `uv run python -m pytest`; run applicable service integration checks when dependencies are available.
- Report exactly which checks ran and their result; do not report planned CI as passed.

## API and database compatibility

- Public HTTP APIs are `/api/v1`; additive optional fields are preferred within a major version. Do not change meaning or remove fields in a deployed version. Breaking changes require `/api/v2`, a documented deprecation period, telemetry, and client migration plan.
- OpenAPI is the wire contract. CI should detect unintended breaking changes. Keep error envelope and pagination semantics stable.
- Alembic migration IDs are immutable, ordered, reviewed. Use expand/backfill/contract; support current and immediately previous application version during rolling deploy. Test fresh install and upgrade from previous release. Do not edit an applied migration; create a corrective migration.
- Content definitions and challenge hidden-test versions are immutable after publication; publish a new version to change them.

## Pull request checklist

- Scope and architecture docs updated when boundaries/decisions change.
- No credentials, learner data, hidden tests, or generated artifacts included.
- Dependency and lock files agree; migrations are reversible or have explicit recovery notes.
- Relevant checks were run and results stated; limitations and follow-up work are clear.
