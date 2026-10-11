# BackendAPI foundation

This directory contains the first FastAPI modular monolith implementation. See the generated [v1 API contract](../Documentation/api/README.md) for routes and limitations.

## Local setup

Install Python 3.11 and uv (see root [CONTRIBUTING.md](../CONTRIBUTING.md)). From repository root:

```powershell
uv sync --all-groups
Copy-Item .env.example .env
docker compose -f Infrastructure/compose.yaml up -d postgres
uv run python -m alembic upgrade head
uv run python -m BackendAPI.app.db.seed
uv run python -m uvicorn BackendAPI.app.main:app --reload
```

`.env.example` contains local placeholders only. Replace them for shared environments; never commit `.env`. Local PostgreSQL is started separately. OIDC is still unselected; protected routes fail closed until all three issuer/audience/JWKS settings are configured.

## Configuration

Use typed settings sourced from environment variables. `CODEQUEST_` is the reserved environment prefix. Partial OIDC configuration fails fast; missing OIDC configuration leaves protected endpoints unavailable rather than enabling a bypass. Keep secrets out of logs, exception messages, telemetry, and client bundles.

## API and persistence rules

- Public routes are under `/api/v1`; version schemas and generated OpenAPI deliberately.
- Error bodies use the stable envelope defined in `Documentation/04-services-data-security.md`.
- Database schema changes use reviewed Alembic revisions under `Database/migrations/versions/`.
- Use additive expand/contract migration steps for deployed compatibility; never mutate published challenge versions in place.
- Services own repository interfaces; route handlers translate transport data and do not embed domain or SQL rules.
- Health, catalog, profile, and caller-owned progress/award/submission-metadata routes are implemented under `/api/v1`. No execution, grading, progression-write, teacher/admin, or provider integration endpoints exist yet.

## Migration and development content

Apply schema with `uv run python -m alembic upgrade head`; roll back one migration with `uv run python -m alembic downgrade -1`. Seed missing development catalog rows with `uv run python -m BackendAPI.app.db.seed`. See [Database setup](../Database/README.md).

Run unit and SQLite migration tests with `uv run python -m pytest`. PostgreSQL integration tests require the isolated `CODEQUEST_TEST_DATABASE_URL` described in `Database/README.md`.
