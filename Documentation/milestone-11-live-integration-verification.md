# Milestone 11: Live integration verification

Date: 2026-10-11. Starting checkpoint: `d9f68f75eebfc40706c1f610ced8d6a7e0d29126`.

## Verification matrix

| Gate | Status | Evidence / limitation |
|---|---|---|
| Starting Git checkpoint and worktree | PASSED | HEAD matched the requested checkpoint and the worktree was clean before this report was added. |
| Repository lint and formatting | PASSED | `.venv\\Scripts\\ruff.exe check .` and `.venv\\Scripts\\ruff.exe format --check .` both exited 0; 49 files formatted. |
| Documentation, configuration, and OpenAPI checks | PASSED | `Tools/validate_docs.py`, `Tools/validate_config.py`, and `Tools/export_openapi.py --check` each exited 0. |
| Focused migration and evaluator contract tests | PASSED | `pytest -vv BackendAPI/tests/test_migrations.py BackendAPI/tests/test_quest_postgres_concurrency.py BackendAPI/tests/test_submission_postgres_concurrency.py PythonExecutionService/test_contract.py PythonExecutionService/test_container_integration.py` → 11 passed, 5 skipped, 1 warning. Skips are three PostgreSQL tests and two real-container tests because their external services/opt-in are unavailable. |
| Deterministic OIDC signature and claim tests | PASSED | The same focused API test invocation ran all five `BackendAPI/tests/test_security.py` tests before its first health route test stalled. They use generated local keys and a mocked JWKS client, not a live provider. |
| Full backend/API suite | BLOCKED | `pytest -q --tb=short` produced no output and did not complete. Focused pytest runs also stalled at the first `TestClient` request (`test_health_and_readiness`); they were interrupted. This is not a test failure diagnosis or a pass. A complete pytest summary is unavailable. |
| Exact CI `uv` lock/install commands | BLOCKED | `uv` is not installed/on PATH; `uv lock --check` and `uv sync --locked --all-groups` were not run. Local Ruff used the already installed `.venv` tool. |
| Live OIDC login and protected API | BLOCKED | No OIDC issuer, audience, JWKS URL, or provider registration is configured. The current Unity boundary has no PKCE browser login/token acquisition implementation. |
| PostgreSQL migrations and concurrency | BLOCKED | `CODEQUEST_TEST_DATABASE_URL` and `CODEQUEST_DATABASE_URL` are unset; no `psql` command is installed and no PostgreSQL service was available. SQLite migration success does not establish PostgreSQL locking/concurrency behavior. |
| Real evaluator isolation | BLOCKED | Docker CLI 29.6.1 is installed, but `docker info` failed because `//./pipe/dockerDesktopLinuxEngine` does not exist. The two disposable-container tests were skipped. No worker endpoint/token or evaluator image is configured. |
| Unity authenticated gameplay flow | BLOCKED | The required live identity, PostgreSQL, worker, and isolated evaluator are unavailable. No real Unity login, submission, quest reward, restart restoration, or duplicate/incorrect submission scenario was executed for this milestone. |
| Hosted GitHub Actions | BLOCKED | No `GITHUB_TOKEN`/`GH_TOKEN` or `gh` executable is available; jobs were not dispatched or observed. |

## Test identity provider setup

Keycloak is selected as a test-only OIDC provider candidate because it supports the standard OIDC Authorization Code flow with PKCE for a public native client and can issue locally verifiable RS256 tokens. No Keycloak instance, realm, client, credentials, or provider metadata were available during this verification. This selection does not change production identity configuration.

When provisioning the test realm, configure a native/public Unity client with Authorization Code enabled, PKCE using `S256` required, and no client secret. Register the exact redirect URI produced by the Unity browser-auth integration for each target platform. That URI remains TBD until the Unity auth package and callback handler are implemented; do not register a guessed callback. Configure the API audience to exactly match the backend `CODEQUEST_AUTH_AUDIENCE`. The backend also requires `CODEQUEST_AUTH_ISSUER` and `CODEQUEST_AUTH_JWKS_URL`, an RS256 signature with a matching `kid`, and `iss`, `aud`, `exp`, `iat`, and non-empty `sub` claims. Use the provider's realm discovery/JWKS endpoints and keep test values in local environment/secret storage. Never place a client secret in Unity or commit real tokens or credentials.

After client provisioning, verify valid login/token acquisition, expiry, wrong issuer, wrong audience, JWKS rotation/key selection, subject-to-profile mapping, and attempts to use another player's submission/progression identifiers. Preserve production issuer, audience, and signing keys separately. Until these checks pass, keep authenticated Unity login and production evaluation disabled; backend signature/issuer/audience validation remains fail-closed.

## PostgreSQL and evaluator execution instructions

The existing workflow `.github/workflows/baseline.yml` contains the supported reproducible checks. Its PostgreSQL job provisions PostgreSQL 17.5 Alpine and runs the configured migration round-trip, quest concurrency, and submission concurrency tests using `CODEQUEST_TEST_DATABASE_URL`. Capture the job's actual PostgreSQL version and pytest output when it runs; this local verification obtained neither.

The evaluator job targets a disposable Ubuntu runner, confirms Docker, builds from the digest-pinned Python base image, and runs `PythonExecutionService/test_container_integration.py` with the opt-in set only after the build. Run and inspect that job before enabling a worker. It is the available approved path for learner-like hostile code; Windows mocks are not evidence of Linux isolation.

## Exact local diagnostics

- HEAD before report: `d9f68f75eebfc40706c1f610ced8d6a7e0d29126`; `git status --short` was empty.
- Python: 3.11.9; installed Ruff: 0.11.2; Docker CLI: 29.6.1.
- Docker server probe failed: `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine; check if the path is correct and if the daemon is running: open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.`
- OIDC issuer/audience/JWKS, PostgreSQL test URL, worker URL/token, evaluator image, sandbox opt-in, and GitHub tokens were all absent from the process environment. Secret-file contents were not read.
- Unity Editor 6000.3.19f1 exists locally, but no live authenticated flow could be exercised without the identity and backend dependencies above. Earlier offline compile/test results are recorded in `Documentation/milestone-10-authenticated-evaluation.md`; they are not Milestone 11 live-flow evidence.

## Readiness and next actions

The real authenticated challenge-to-progression flow is **not complete**. Before declaring it ready, provision the test realm and native-client callback, implement PKCE in Unity, provide an isolated PostgreSQL test service and approved Linux Docker runner, then execute and retain the actual CI job outputs. Complete the full gameplay sequence in the milestone brief—including XP exactly-once, restart restoration, incorrect/failed submission, timeout/interruption, stale revision, expired token, and cross-player access checks—before enabling production evaluation.

No gameplay feature was added. This report records verification results and blockers only.
