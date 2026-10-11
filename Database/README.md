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
Challenge source is persisted for delivery to the separately configured worker and removed from terminal submission rows after `CODEQUEST_SUBMISSION_SOURCE_RETENTION_DAYS` (default 30 days). The API process runs an hourly cleanup task. The source digest and request hash remain for audit/idempotency; backup and transaction-log retention is controlled separately by the database operator.

## Migration policy

- `20261011_0001` creates the initial schema; `20261011_0002` adds quest rules, progress revisions, idempotency receipts, and the XP reward ledger; `20261011_0003` adds challenge evaluation limits, private hidden tests, progressive hints, submission source/idempotency, and durable evaluation attempts.
- Use `uv run python -m alembic revision --autogenerate -m "short-description"` only to draft; review the generated migration against both model metadata and PostgreSQL behavior before committing.
- Test new revisions on a fresh database and from the previous revision. Never edit an applied migration; add a corrective revision.
- Deployment changes use expand/backfill/contract. Content rows are versioned and published revisions are immutable.
- `uv run python -m alembic downgrade -1` reverts one revision. `downgrade base` removes all application tables and data and is for disposable development/test databases only.

## Seed data

`python -m BackendAPI.app.db.seed` inserts only missing rows. It never overwrites existing content. Current development content covers the original three curriculum regions plus Variable Valley, seven learning objectives, four quests and their event rules/targets, three existing logical challenges (with published v1/v2 definitions) plus five Variable Valley v1 challenges, separate hidden tests, progressive hint rows, and two achievements. It includes no player accounts, reference solutions, or learner submission source. The Variable Valley evaluator contract accepts function parameters and return values; stdin/`input()`/stdout challenge mode remains unsupported.

## PostgreSQL integration tests

The routine test suite uses isolated in-memory SQLite for fast constraints and a temporary SQLite file for Alembic upgrade/downgrade checks. PostgreSQL migration and concurrency coverage is skipped unless `CODEQUEST_TEST_DATABASE_URL` is set to a dedicated database named exactly `codequest_test`. Each PostgreSQL test verifies that no application tables remain, applies `uv run python -m alembic upgrade head`, verifies the Alembic revision and `curriculum_regions` table, then seeds the required development catalog before querying it. The tests downgrade to base during cleanup. The GitHub Actions job supplies `postgresql+psycopg://codequest:codequest-test-only@127.0.0.1:5432/codequest_test`; never point a test URL at a shared or production database. PostgreSQL test diagnostics log database/schema names, redacted URL targets, migration revisions, and table visibility without credentials. SQLite tests do not establish PostgreSQL locking behavior.
