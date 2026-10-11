# ADR-0012 — Authoritative quest event ledger

**Status:** Accepted · **Date:** 2026-10-11

## Context

Milestone 5 introduced reusable Unity quest definitions and local event handling, while the API exposed only read-only quest snapshots. Client-only completion cannot safely grant persistent progress or rewards, and retries or concurrent devices can otherwise duplicate or overwrite state.

## Decision

Quest mutations use an additive `/api/v2` event contract. OIDC identity selects the player profile. The client submits only an idempotency UUID, published quest version, expected revision, supported event type, and registered target version. Challenge completion also references a server-owned passed submission. Versioned server-authored rules determine objective progress, transitions, and XP. Event receipts, progress revision, reward ledger entries, and progression changes commit atomically.

Quest definitions and rules are immutable by version after publication. Event receipts are retained until account deletion or a future approved retention policy. Unity displays progress as pending or failed until the API confirms it; its offline event queue is bounded to 32 in-memory events and does not survive application restart.

## Consequences

- A modified client cannot submit XP, reward quantities, objective counts, or completion state.
- Idempotency and reward uniqueness constraints prevent duplicate application; PostgreSQL row locks serialize revision updates.
- Registered interaction/checkpoint events are authenticated client reports and do not prove physical presence or independently grant XP. Production anti-cheat evidence requires a later server-observed or signed gameplay design.
- Challenge evidence is verifiable only after a trusted evaluator has written a passed submission. Challenge submission/evaluation is not implemented by this decision.
- SQLite is suitable for fast functional tests; PostgreSQL concurrency claims require the dedicated PostgreSQL integration test.
- Offline play does not imply cloud persistence. Authenticated API requests continue to fail closed.

## References

- [API contract and retry rules](../api/README.md#quest-events-v2-contract-milestone-6)
- [Database migration policy](../../Database/README.md#migration-policy)
- [Security architecture](../04-services-data-security.md#7-identity-authorization-and-save-data)
- [Quest requirements](../01-product-requirements.md#2-software-requirements-specification)
