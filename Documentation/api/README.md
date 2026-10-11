# Versioned API v1

`openapi-v1.json` and `openapi-v2.json` are generated from the FastAPI route and Pydantic schema definitions. Check drift with `uv run python Tools/export_openapi.py --check`; regenerate after an intentional contract change with `uv run python Tools/export_openapi.py`.

## Conventions

- Base path: `/api/v1`. Health endpoints are `/healthz` (process liveness) and `/readyz` (database readiness).
- List responses use `{ "items": [], "limit": 20, "offset": 0, "total": 0 }`; `limit` is 1–100, default 20; `offset` is zero-based, default 0.
- API errors are flat objects with stable `code`, safe `message`, `retryable`, and `correlationId`. Each response also includes the matching `X-Request-ID` header. Client-provided request IDs must be UUIDs; otherwise the API generates one.
- JSON request and response properties use lower camel case. Unknown or invalid request fields produce a 422 error without echoing submitted values.
- Public GET routes expose only published definitions and public challenge content. V2 quest events are the only quest mutation contract; there are no client-controlled progression, reward, submission, or arbitrary code execution endpoints.

## Route inventory

| Method | Path | Auth | Behavior |
|---|---|---|---|
| GET | `/healthz` | public | Liveness; no dependency check |
| GET | `/readyz` | public | Checks PostgreSQL connectivity; 503 if unavailable |
| GET | `/api/v1/curriculum/regions` | public | Published region page |
| GET | `/api/v1/curriculum/regions/{slug}` | public | Latest published version by stable slug |
| GET | `/api/v1/curriculum/objectives` | public | Published objectives, optional `region_slug` filter |
| GET | `/api/v1/curriculum/objectives/{slug}` | public | Latest published version by stable slug |
| GET | `/api/v1/quests` | public | Published quest definitions, optional `region_slug` filter |
| GET | `/api/v1/quests/{slug}` | public | Latest published version by stable slug |
| GET | `/api/v1/challenges` | public | Published public challenge definitions, optional `objective_slug` filter |
| GET | `/api/v1/challenges/{slug}` | public | Latest published public version; never includes hidden tests |
| GET | `/api/v1/me` | OIDC bearer | Caller-owned profile; 404 until initialized |
| PUT | `/api/v1/me` | OIDC bearer | Idempotent profile creation/update using only token issuer/subject identity |
| GET | `/api/v1/me/quests` | OIDC bearer | Caller-owned quest progress page |
| GET | `/api/v1/me/progression` | OIDC bearer | Caller-owned progression snapshot |
| GET | `/api/v1/me/achievements` | OIDC bearer | Caller-owned achievement awards page |
| GET | `/api/v1/me/submissions` | OIDC bearer | Caller-owned submission metadata page |
| POST | `/api/v2/me/quests/{quest_slug}/events` | OIDC bearer | Submit a registered, revision-checked quest event |
| GET | `/api/v2/me/quests` | OIDC bearer | Caller-owned quest progress with objective counts and revisions |
| GET | `/api/v2/me/progression` | OIDC bearer | Authoritative progression snapshot |
| GET | `/api/v2/quests/{quest_slug}?version=1` | public | Exact published quest version and server rules |

## Example requests and responses

PowerShell public catalog request:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/curriculum/regions?limit=1&offset=0'
```

Example page:

```json
{
  "items": [
    {
      "slug": "variable-vale",
      "version": 1,
      "name": "Variable Vale",
      "summary": "Learn to store values and communicate with the world.",
      "sortOrder": 1,
      "unlockRegionSlug": null
    }
  ],
  "limit": 1,
  "offset": 0,
  "total": 3
}
```

Protected profile initialization requires a real issuer token accepted by configured OIDC issuer, audience, JWKS URI, and RS256 signature:

```powershell
$headers = @{ Authorization = "Bearer $env:CODEQUEST_ACCESS_TOKEN" }
Invoke-RestMethod -Method Put -Uri 'http://127.0.0.1:8000/api/v1/me' -Headers $headers -ContentType 'application/json' -Body '{"displayName":"Ada","locale":"en"}'
```

Do not place tokens in command history or logs. No fake/development auth bypass exists. If the three OIDC settings are unset, protected endpoints return 503 `authentication_not_configured`; missing or invalid tokens after configuration return 401.

## Known limitations

- Identity provider and deployment are not selected. Bearer validation currently accepts RS256 OIDC JWTs only and checks signature, issuer, audience, expiration, issued-at, and subject. Role/scope policy and account lifecycle remain future work.
- Quest progress writes and authoritative quest/progression reads are implemented only in v2. Awards and submission metadata remain read-only. No challenge submission create/run endpoint exists yet.
- V1 quest progress remains read-only. Versioned quest event writes and authoritative quest/progression reads are implemented in additive v2 routes described below. V2 XP rewards require a trusted passed challenge record; client interaction/checkpoint claims cannot independently award XP.
- Challenge execution, scoring, progression awards, authoring/publishing, teacher/admin routes, refresh-token handling, rate limiting, CORS, and production observability are not implemented.
- `source_digest` is metadata only; submitted source code is neither received nor persisted in this milestone.
- Readiness checks PostgreSQL only. Missing OIDC configuration disables protected routes but does not make public catalog service unready.

## Quest Events v2 contract (Milestone 6)

`/api/v2` is additive; v1 remains unchanged. These request/response shapes are generated into `openapi-v2.json`.

### `POST /api/v2/me/quests/{quest_slug}/events` (OIDC bearer)

Request (unknown fields are rejected):

```json
{
  "eventId": "b3a35d10-cba4-498f-86c4-912a401c5132",
  "questVersion": 1,
  "expectedRevision": 0,
  "eventType": "interact",
  "targetId": "relay-switch",
  "targetVersion": 1
}
```

Allowed event types are `interact`, `checkpoint`, `challenge_passed`, and `prerequisite_completed`. The server matches the exact event type/target/version to a published objective rule, checks objective prerequisites, and computes all counts/status. `challenge_passed` additionally requires a `passed` submission record belonging to the authenticated profile for that exact challenge version. `prerequisite_completed` checks an already completed prerequisite quest version owned by the caller. Requests cannot supply player IDs, objective IDs, progress, status, XP, or reward fields. Interaction/checkpoint reports are authenticated client event claims matched to registered targets; they do not independently grant XP. A quest version with XP rewards must include an objective requiring a trusted `challenge_passed` event.

The response is a `QuestEventResult` with quest slug/version, server status, new revision, objective counts/completion flags, newly granted XP reward ledger entries, progression snapshot, and `replayed`. Progress transitions are server-owned: absent/available to `in_progress`, then to `completed` only when all required rules are satisfied. A repeated `eventId` with the same canonical payload returns the stored original result (200, `replayed: true`); reuse with a different payload returns 409 `idempotency_key_reused`. The idempotency key is scoped to the authenticated profile and retained with the event record; current policy retains records until account deletion/approved retention work.

The `expectedRevision` is checked after idempotency replay lookup. A stale revision returns 409 `quest_revision_conflict` with the authoritative current quest snapshot in the error's `currentState`. A missing/unsupported/unpublished quest version returns 404 `quest_version_not_found`; a registered but disallowed event/target or invalid objective transition returns 409 with a stable error code. Invalid shape is 422. Transactions reserve the idempotency key, lock the player quest row, validate, update objective state, write XP ledger/progression once, and store the response atomically. Any failure rolls the transaction back. Only accepted transactions retain an event receipt. A rejected event that rolls back its reservation has not consumed its UUID; after refreshing a stale revision, the client may submit the corrected payload with that same UUID. Once accepted, any different payload under that UUID returns `idempotency_key_reused`.

### `GET /api/v2/me/quests` and `GET /api/v2/me/progression` (OIDC bearer)

Both are caller-scoped using the OIDC subject-to-profile mapping. Quest pages include `revision` and objective progress; progression returns the existing authoritative experience/level/revision fields. No player identifier is accepted in the path or query.

### Definition read

`GET /api/v2/quests/{questSlug}?version=1` returns only a published immutable version, including its objective rules, explicit prerequisites, registered target versions, and server-owned XP reward rules. Rules are normalized in versioned database rows; publishing/admin mutation remains outside this milestone. Unregistered event targets and malformed prerequisite graphs are rejected during content validation and again before mutation.
