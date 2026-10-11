# Database schema and migrations

PostgreSQL is the persistence target. Schema changes are authored as immutable Alembic revisions under `migrations/versions/`; model metadata supports development tests but the application never creates tables automatically.

## Local setup

1. Install Docker Desktop with its Linux container engine and start it.
2. Copy the root `.env.example` to `.env`. `CODEQUEST_POSTGRES_PASSWORD` is a local placeholder; replace it for shared environments. Keep `.env` untracked.
3. Start only PostgreSQL (the Compose file does not start an API or worker):

   ```powershell
   docker compose -f Infrastructure/compose.yaml up -d postgres
   ```

4. Apply the schema and seed the small development catalog:

   ```powershell
   uv run python -m alembic upgrade head
   uv run python -m BackendAPI.app.db.seed
   ```

5. Inspect or stop the local database:

   ```powershell
   docker compose -f Infrastructure/compose.yaml ps
   docker compose -f Infrastructure/compose.yaml down
   ```

The named volume persists data after `down`. Removing that volume deletes local database data; do so only when you intend to reset the disposable development database.

## Migration policy

- The initial schema migration is `20261011_0001`. It creates all current application tables and constraints.
- Use `uv run python -m alembic revision --autogenerate -m "short-description"` only to draft; review the generated migration against both model metadata and PostgreSQL behavior before committing.
- Test new revisions on a fresh database and from the previous revision. Never edit an applied migration; add a corrective revision.
- Deployment changes use expand/backfill/contract. Content rows are versioned and published revisions are immutable.
- `uv run python -m alembic downgrade -1` reverts one revision. `downgrade base` removes all application tables and data and is for disposable development/test databases only.

## Seed data

`python -m BackendAPI.app.db.seed` inserts only missing `(slug, version)` rows. It never overwrites a row that already exists. Current development content covers the first three documented curriculum regions, six learning objectives, three quests, three public challenge definitions, and two achievement definitions. It includes no player accounts, hidden tests, solutions, or learner submission source.

## PostgreSQL integration tests

The routine test suite uses isolated in-memory SQLite for fast constraints and a temporary SQLite file for Alembic upgrade/downgrade checks. PostgreSQL-specific migration coverage is skipped unless `CODEQUEST_TEST_DATABASE_URL` is set to a dedicated, empty database named exactly `codequest_test`. Never point it at a shared or production database.
