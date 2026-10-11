# Versioned API v1

`openapi-v1.json` is generated from the running FastAPI route and Pydantic schema definitions. Check drift with `uv run python Tools/export_openapi.py --check`; regenerate after an intentional contract change with `uv run python Tools/export_openapi.py`.

## Conventions

- Base path: `/api/v1`. Health endpoints are `/healthz` (process liveness) and `/readyz` (database readiness).
- List responses use `{ "items": [], "limit": 20, "offset": 0, "total": 0 }`; `limit` is 1–100, default 20; `offset` is zero-based, default 0.
- API errors are flat objects with stable `code`, safe `message`, `retryable`, and `correlationId`. Each response also includes the matching `X-Request-ID` header. Client-provided request IDs must be UUIDs; otherwise the API generates one.
- JSON request and response properties use lower camel case. Unknown or invalid request fields produce a 422 error without echoing submitted values.
- Public GET routes expose only published definitions and public challenge content. There are no write endpoints for quest completion, progression, awards, submissions, or arbitrary code execution in this milestone.

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
- Only public definition reads and profile initialization/update are implemented. Quest progress, progression, awards, and submission metadata are read-only. No challenge submission create/run endpoint exists yet.
- Challenge execution, scoring, progression awards, authoring/publishing, teacher/admin routes, refresh-token handling, rate limiting, CORS, and production observability are not implemented.
- `source_digest` is metadata only; submitted source code is neither received nor persisted in this milestone.
- Readiness checks PostgreSQL only. Missing OIDC configuration disables protected routes but does not make public catalog service unready.
