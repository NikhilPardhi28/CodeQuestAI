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
Challenge source is persisted for delivery to the separately configured worker. Automatic source retention/deletion policy remains unresolved.

## Migration policy

- `20261011_0001` creates the initial schema; `20261011_0002` adds quest rules, progress revisions, idempotency receipts, and the XP reward ledger; `20261011_0003` adds challenge evaluation limits, private hidden tests, progressive hints, submission source/idempotency, and durable evaluation attempts.
- Use `uv run python -m alembic revision --autogenerate -m "short-description"` only to draft; review the generated migration against both model metadata and PostgreSQL behavior before committing.
- Test new revisions on a fresh database and from the previous revision. Never edit an applied migration; add a corrective revision.
- Deployment changes use expand/backfill/contract. Content rows are versioned and published revisions are immutable.
- `uv run python -m alembic downgrade -1` reverts one revision. `downgrade base` removes all application tables and data and is for disposable development/test databases only.

## Seed data

`python -m BackendAPI.app.db.seed` inserts only missing rows. It never overwrites existing content. Current development content covers three regions, six objectives, three quests and their event rules/targets, three public challenges with separate hidden tests and progressive hints, and two achievements. It includes no player accounts, reference solutions, or learner submission source.

## PostgreSQL integration tests

The routine test suite uses isolated in-memory SQLite for fast constraints and a temporary SQLite file for Alembic upgrade/downgrade checks. PostgreSQL migration and quest-concurrency coverage is skipped unless `CODEQUEST_TEST_DATABASE_URL` is set to a dedicated, empty database named exactly `codequest_test`. The concurrency test migrates and seeds that database, then downgrades it to base. Never point it at a shared or production database. SQLite tests do not establish PostgreSQL locking behavior.
