# Milestone 6 — Server-authoritative quest events

## Scope

This milestone adds the versioned quest event contract, normalized server-authored rules, transactional player progress, replay protection, and a Unity event client. It does not add challenge submission/evaluation, arbitrary Python execution, multiplayer, or authored production content.

## API

- `POST /api/v2/me/quests/{quest_slug}/events` accepts one supported event for the authenticated profile and returns the authoritative snapshot.
- `GET /api/v2/me/quests` returns that profile's objective counts and quest revisions.
- `GET /api/v2/me/progression` returns that profile's progression state.
- `GET /api/v2/quests/{quest_slug}?version=N` returns the published server-owned rules for one quest version.

Supported events are registered interactions, checkpoints, trusted passed challenge submissions, and completed quest prerequisites. Clients cannot submit objective counts, completion status, XP, reward values, or player identifiers. XP is derived from versioned rules and granted only after all quest objectives are satisfied, including a trusted challenge objective for rewarded quests.

## Persistence and retry

Migration `20261011_0002` adds target/rule/prerequisite/reward tables, quest revision, per-profile idempotency receipts, and a unique reward ledger. The service atomically validates the event, locks the quest progress row on PostgreSQL, updates objective state, writes rewards/progression, and persists the replay response. Event receipts are retained until account deletion or a future approved retention policy. A stale revision returns the current server snapshot with `quest_revision_conflict`.

Unity loads v2 progress, submits the same event UUID on retry, and maps only backend results into server-confirmed objective counts/status. Pending and failed states stay distinct from confirmed state. Its offline queue is capped at 32 in-memory events and is lost when the application exits. Bootstrap still uses an unauthenticated token provider and therefore protected requests fail closed until an actual OIDC adapter is configured.

## Security limits

OIDC subject-to-profile mapping prevents clients from selecting another player. A passed submission must exist in trusted server storage, belong to the caller, and match the challenge slug/version. Interaction and checkpoint events are authenticated client reports; registration constrains where they can apply but does not prove the player physically reached or used the target. Anti-cheat proof needs a later server-observed or signed gameplay design. No submission-evaluation endpoint exists yet, so XP reward completion cannot be demonstrated end to end from the current client.

## Validation

SQLite unit/migration checks cover rule validation, ownership/evidence checks, idempotency, revision conflicts, reward uniqueness, and transaction rollback. PostgreSQL row-lock behavior is covered only by the opt-in integration test using the isolated `codequest_test` database; SQLite results are not evidence for PostgreSQL concurrency. See [database test instructions](../Database/README.md#postgresql-integration-tests) and [API contract](api/README.md#quest-events-v2-contract-milestone-6).

## Next milestone

Implement versioned challenge submission and trusted evaluation records, with PostgreSQL transaction/concurrency tests, then integrate a selected OIDC provider in Unity. That creates the first complete client-to-evaluator-to-quest-reward path without introducing arbitrary execution into the API process.
