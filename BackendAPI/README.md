# BackendAPI foundation

This directory contains the FastAPI modular monolith. See the [API contract](../Documentation/api/README.md), generated [OpenAPI v1](../Documentation/api/openapi-v1.json), and generated [OpenAPI v2](../Documentation/api/openapi-v2.json).

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

- Public catalog and legacy read routes remain under `/api/v1`; quest event writes and authoritative quest/progression reads are under `/api/v2`.
- Error bodies use the stable envelope defined in `Documentation/04-services-data-security.md`.
- Database schema changes use reviewed Alembic revisions under `Database/migrations/versions/`.
- Use additive expand/contract migration steps for deployed compatibility; never mutate published challenge versions in place.
- Services own repository interfaces; route handlers translate transport data and do not embed domain or SQL rules.
- Health, catalog, profile, and legacy snapshots are implemented under `/api/v1`. V2 quest events validate registered server-authored rules and trusted passed submissions; XP and objective counts are never accepted from the client. Challenge submission/evaluation, arbitrary code execution, teacher/admin, and provider integration endpoints do not exist.

## Migration and development content

Apply schema with `uv run python -m alembic upgrade head`; roll back one migration with `uv run python -m alembic downgrade -1`. Seed missing development catalog rows with `uv run python -m BackendAPI.app.db.seed`. See [Database setup](../Database/README.md).

Run backend tests with `uv run python -m pytest`. PostgreSQL migration and concurrency tests require the isolated, empty `CODEQUEST_TEST_DATABASE_URL` described in `Database/README.md`; SQLite alone does not verify PostgreSQL locking.
