# Milestone 10: Authenticated evaluation and progression

Date: 2026-10-11. Starting checkpoint: `5f75731b0943caa878778c25b2bc2d47fa6b238c`.

## Work completed

- Backend OIDC configuration now validates issuer, audience, and JWKS URL as a complete set. HTTPS is required except for loopback endpoints in local, development, and test environments. Audience values must be non-empty and trimmed. Existing verification pins accepted tokens to RS256 and requires a valid signature, configured issuer and audience, and `exp`, `iat`, and `sub` claims. Identity is mapped from the validated subject to the unique server-side player profile.
- Deterministic auth tests generate an RSA key per test and use the synthetic issuer `https://issuer.test/`; the JWKS client is replaced in process. These checks exercise signature and claims validation, fail-closed behavior, and config errors. They are not a live identity provider integration.
- The existing Unity `IAccessTokenProvider` boundary remains in place. No provider issuer, public client ID, API audience, or redirect registration is available in this environment, so Unity login/token acquisition remains blocked. No secret was added to the client and no token-validation bypass was added.
- The evaluator launcher continues to require a repository-qualified `@sha256:` image reference for deployment. In the `ci`, `test`, and `local` environments only, it also accepts the immutable image content ID of a locally built image. The GitHub Actions `evaluator-sandbox` job builds with the pinned official Python base image `python:3.11-slim-bookworm@sha256:2333bd330d12de02514770b3585cad313644316047cdee24a7acfdece6de6efb`, then passes the resulting content ID to the launcher. The base digest is from the [Docker Official Image metadata](https://hub.docker.com/layers/library/python/3.11-slim-bookworm/).
- New opt-in Linux container integration tests check non-root UID, disabled network access, read-only root filesystem, no host temporary file or Docker socket mount, bounded execution time, output limits, and absence of hidden result details. Student-like source runs only inside the disposable worker container. Mocked launcher tests remain separate from these real-container checks.
- The Ruff findings in migration `20261011_0003_challenge_evaluation.py` were corrected with formatting-only line wrapping. SQL statements, migration operations, names, values, and ordering are unchanged. Repository-wide Ruff lint and format checks now pass locally.

## Exact local environment checks

- `docker --version` → Docker CLI 29.6.1.
- `docker info --format '{{.ServerVersion}}'` → failed: `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine; check if the path is correct and if the daemon is running: open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.`
- `psql` is not installed, `CODEQUEST_TEST_DATABASE_URL` is unset, and `CODEQUEST_DATABASE_URL` is unset in the process environment.
- `CODEQUEST_AUTH_ISSUER`, `CODEQUEST_AUTH_AUDIENCE`, `CODEQUEST_AUTH_JWKS_URL`, `CODEQUEST_EVALUATION_WORKER_URL`, `CODEQUEST_EVALUATION_WORKER_TOKEN`, and `CODEQUEST_EVALUATOR_IMAGE` are unset. Values from local secret files were not read or reported.
- The CI workflow's `uv` command was not available on this host (`uv` is not recognized). The equivalent pinned tools in `.venv` were used for the full pytest, Ruff, formatting, and documentation/config/OpenAPI checks; `uv lock --check` and `uv sync --locked` were not run locally.
- The GitHub Actions workflow defines hosted Ubuntu PostgreSQL and evaluator sandbox jobs. They were not dispatched or observed from this local run.

## Validation results

All checks are classified by whether they were executed here. The sandbox integration test file was collected by pytest but skipped because the real Linux Docker job is the only enabled execution environment for hostile source.

| Area | Status | Command/evidence |
|---|---|---|
| Full Python backend and worker-contract suite | PASSED | `& .\.venv\Scripts\python.exe -m pytest -q --tb=short` → 56 passed, 5 skipped, 1 Starlette deprecation warning. Skips: three PostgreSQL tests and two real-container tests. |
| Deterministic authentication and worker contract tests | PASSED | Included in the full suite; focused auth/worker run was 15 passed. |
| Repository-wide lint | PASSED | `& .\.venv\Scripts\ruff.exe check .` → all checks passed. |
| Repository-wide formatting | PASSED | `& .\.venv\Scripts\ruff.exe format --check .` → 49 files already formatted. |
| Exact CI `uv run ruff ...` commands and lock check | BLOCKED LOCALLY | `uv run ruff check .`, `uv run ruff format --check .`, and `uv lock --check` could not start because `uv` is not installed/on `PATH`; equivalent installed project Ruff commands passed above. |
| Alembic SQLite migration round-trip | PASSED | `& .\.venv\Scripts\python.exe -m pytest -q BackendAPI/tests/test_migrations.py` → 1 passed, 1 PostgreSQL case skipped. |
| Documentation/config/OpenAPI validators | PASSED | `Tools/validate_docs.py`, `Tools/validate_config.py`, and `Tools/export_openapi.py --check` passed after the report update. |
| Unity 6000.3.19f1 compilation | PASSED | Batch compilation exited successfully; no C# compiler errors. |
| Unity EditMode | PASSED | 12 passed, 0 failed, 0 skipped. |
| Unity offline PlayMode | PASSED | 6 passed, 0 failed, 1 ignored opt-in live API/auth test. |
| PostgreSQL migrations and concurrency | BLOCKED | No PostgreSQL client/server or configured test URL; Docker Linux daemon is unavailable. SQLite does not verify PostgreSQL locking. |
| Live OIDC integration | BLOCKED | No identity provider or native/public client registration is configured. Deterministic generated-key tests do not prove provider discovery or live token issuance. |
| Unity authenticated login and API calls | BLOCKED | Bootstrap still uses `UnauthenticatedTokenProvider`; no client ID, authorization endpoint, token endpoint, redirect URI, or API-audience token is available. |
| Real evaluator image and hostile-code tests | BLOCKED LOCALLY | Docker Linux daemon is unavailable, and no deployed evaluator image digest or worker endpoint/token is configured. The GitHub Actions job is configured but has not run here. |
| Authenticated Unity → API → worker → quest reward → restart | BLOCKED | Requires the real OIDC client, worker, and authenticated database environment. No pass, XP, or restored real-player state is simulated or claimed. |
| Hosted GitHub Actions jobs | NOT RUN | Workflow YAML parsed locally, but no remote workflow run was dispatched or observed. |

The full Python test suite uses SQLite for local API and service tests. Three PostgreSQL-only cases were skipped. The two real-container tests were skipped because `CODEQUEST_RUN_EVALUATOR_CONTAINER_TESTS` is intentionally unset locally. The new Ubuntu Actions job builds the image and sets that variable only after confirming the runner's Docker daemon; no local result is inferred from the workflow definition.

## Security and rollout limits

Production remains disabled until an operator configures an HTTPS OIDC issuer, the exact API audience, the issuer's HTTPS JWKS URL, and a native/public game client using Authorization Code with PKCE and no client secret. The provider must issue RS256-signed API access tokens with a `kid`, `iss`, `aud`, `exp`, `iat`, and `sub` accepted by the backend. The current Unity bootstrap has no browser login implementation, so selecting the provider and its supported native redirect flow is a prerequisite to a reviewable client implementation.

The production worker remains disabled until a reviewed evaluator image is published and configured by immutable repository digest, the worker URL uses HTTPS off-loopback, the shared worker token is provisioned through secret storage, PostgreSQL migrations/concurrency are verified, and the disposable Linux security checks have run on the intended host. The CI job's local image content ID is a reproducible test identity, not a production deployment reference or sandbox approval.

**Readiness:** backend auth rules and reproducible CI sandbox checks are strengthened, but Milestone 10's authenticated real-player evaluation path is incomplete. The next required step is provision/configure a test OIDC provider and native public-client registration, then exercise PKCE login against the backend. In parallel, run the PostgreSQL and evaluator CI jobs and review their actual output before enabling any worker integration.
