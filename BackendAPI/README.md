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

Use typed settings sourced from environment variables. `CODEQUEST_` is the reserved environment prefix. Partial OIDC configuration fails fast; configured issuer and JWKS endpoints require HTTPS, except loopback HTTP for local/development/test environments. The audience must be non-empty. Missing OIDC configuration leaves protected endpoints unavailable rather than enabling a bypass. The backend verifies RS256 signatures and the configured issuer/audience plus `exp`, `iat`, and `sub`; deterministic synthetic-issuer tests are not a substitute for a live identity provider. Keep secrets out of logs, exception messages, telemetry, and client bundles.

## API and persistence rules

- Public catalog and legacy read routes remain under `/api/v1`; quest event writes and authoritative quest/progression reads are under `/api/v2`.
- Error bodies use the stable envelope defined in `Documentation/04-services-data-security.md`.
- Database schema changes use reviewed Alembic revisions under `Database/migrations/versions/`.
- Use additive expand/contract migration steps for deployed compatibility; never mutate published challenge versions in place.
- Services own repository interfaces; route handlers translate transport data and do not embed domain or SQL rules.
- Health, catalog, profile, challenge definitions/hints/submissions, and legacy snapshots are under `/api/v1`. V2 quest events validate server-authored rules and trusted passed submissions; accepted evaluations update matching objectives and rewards atomically. API source execution is prohibited; jobs go to PythonExecutionService only when configured.

## Migration and development content

Apply schema with `uv run python -m alembic upgrade head`; roll back one migration with `uv run python -m alembic downgrade -1`. Seed missing development catalog rows with `uv run python -m BackendAPI.app.db.seed`. See [Database setup](../Database/README.md).

Run backend tests with `uv run python -m pytest`. PostgreSQL migration and concurrency tests require the isolated, empty `CODEQUEST_TEST_DATABASE_URL` described in `Database/README.md`; SQLite alone does not verify PostgreSQL locking.

### Challenge worker

Submission endpoints stay unavailable unless `CODEQUEST_EVALUATION_WORKER_URL` and `CODEQUEST_EVALUATION_WORKER_TOKEN` are both configured. Run `python PythonExecutionService/worker.py` only after building a reviewed evaluator image and setting `CODEQUEST_EVALUATOR_IMAGE` to its immutable `@sha256:` reference. The worker service needs no database credentials and is distinct from each disposable job container. The Docker Linux engine is unavailable in this environment, so worker runtime and isolation are not verified. There is no host Python fallback.
