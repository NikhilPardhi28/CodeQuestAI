# Milestone 12: FastAPI TestClient hang diagnosis

Date: 2026-10-11. Starting checkpoint: `6f5a510f2b6e23ac98ee950355162683cf759f14`.

## Root cause

There is no application or dependency compatibility hang. The test process runs in a restricted Windows workspace sandbox that blocks the local socket operation required by asyncio's Windows event loop. Starlette's `TestClient` asks AnyIO to start a background event loop; Windows' default Proactor loop creates its wake-up channel with `socket.socketpair()`. Under the restricted execution boundary, `socket.socketpair()` itself stalled in `socket.accept()`. The thread dump showed the worker blocked in `asyncio.windows_events._make_self_pipe` while the pytest thread waited in `anyio.from_thread.start_blocking_portal`, called by Starlette's `TestClient` while sending the first health request. The request had not reached FastAPI middleware, the lifespan handler, or database access.

Evidence distinguishing an environment restriction from an application defect:

- In the restricted sandbox, a standalone `socket.socketpair()` and construction of both Windows asyncio loop policies each timed out after three seconds.
- Outside that boundary, the same interpreter's `socket.socketpair()` succeeded and the original health/readiness HTTP test passed in 0.14 seconds.
- No application behavior, test assertions, authentication checks, or dependency versions needed changing.

The installed runtime matched the repository's pinned direct dependencies and resolved lock entries: Python 3.11.9, FastAPI 0.115.12, Starlette 0.46.2, HTTPX 0.28.1, pytest 8.3.5, SQLAlchemy 2.0.39, and psycopg 3.2.6. `uv` is unavailable locally, so no `uv lock --check` or sync was performed; no dependency was changed.

## Safeguards

Pytest now uses its built-in `faulthandler_timeout = 30` setting to print thread stacks if a test stalls. The `python-and-docs` and `postgres-integration` GitHub Actions jobs now have 15-minute job limits; the existing evaluator job already has a 10-minute limit. These safeguards do not suppress or skip tests. In this restricted Windows sandbox, HTTP tests must run outside the network-restricted process boundary so local event-loop sockets can be created.

## Verification results

All Python commands used the repository `.venv` with the versions above. The tests below were executed outside the restricted boundary, where local sockets work.

| Group | Result |
|---|---|
| Original hanging test: `pytest -vv BackendAPI/tests/test_api.py::test_health_and_readiness` | **PASSED** — 1 passed in 0.14s. |
| Health/readiness HTTP tests: `pytest -vv BackendAPI/tests/test_api.py -k "health or readiness"` | **PASSED** — 2 passed, 10 deselected. |
| Protected profile/quest ownership HTTP test: `pytest -vv BackendAPI/tests/test_api.py -k quest_progress_is_scoped_to_authenticated_profile` | **PASSED** — 1 passed, 11 deselected. |
| Submission and ownership HTTP tests: `pytest -vv BackendAPI/tests/test_api.py -k "challenge_submission_and_polling_are_authenticated_and_owner_scoped or submission_routes_reject_unauthenticated_and_expired_tokens"` | **PASSED** — 2 passed, 10 deselected. |
| Full repository pytest suite after enabling the faulthandler safeguard: `pytest -q --tb=short` | **PASSED** — 56 passed, 5 skipped, 1 Starlette deprecation warning, 5.09s. Skipped: three PostgreSQL integration cases because `CODEQUEST_TEST_DATABASE_URL` is unset, and two real-container checks because Docker is unavailable and those tests are restricted to the Linux sandbox CI job. |
| Ruff lint and formatting | **PASSED** — `ruff check .` and `ruff format --check .`. |
| SQLite migration round-trip | **PASSED** — `pytest -q BackendAPI/tests/test_migrations.py`: 1 passed, 1 PostgreSQL case skipped. |
| Configuration and docs | **PASSED** — `Tools/validate_config.py` and `Tools/validate_docs.py`. |
| OpenAPI | **PASSED** — `Tools/export_openapi.py --check`. |
| PostgreSQL concurrency | **BLOCKED** — PostgreSQL URL/server unavailable; SQLite is not used as evidence for PostgreSQL locking. |
| Live OIDC, Docker isolation, authenticated Unity flow, hosted CI | **BLOCKED** — unchanged from [Milestone 11](milestone-11-live-integration-verification.md). |

One Starlette deprecation warning remains: `anyio.abc.BlockingPortal` is deprecated at the installed Starlette test-client call site. No dependency upgrade was attempted because the current locked versions run successfully outside the restricted socket boundary.

## Result

The original test hang is resolved operationally by running the HTTP suite with local socket support. No application code or security/ownership tests were changed. The test suite is reproducible with the locked environment when the runner permits Windows loopback socket creation; the unresolved PostgreSQL, live identity, evaluator, Unity, and hosted CI gates remain as stated above.
