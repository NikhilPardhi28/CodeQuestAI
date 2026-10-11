# Milestone 8: Runtime verification and security hardening

Date: 2026-10-11. Repository checkpoint inspected before work: `b3b667be43319c905aab0a5475eccf224d1e1a0c`.

## Environment and exact versions

- Windows 11, Python 3.11.9; project `.venv` dependencies: FastAPI 0.115.12, Starlette 0.46.2, HTTPX 0.28.1, AnyIO 4.15.1, pytest 8.3.5, SQLAlchemy 2.0.39, Alembic 1.15.2, psycopg 3.2.6, Ruff 0.11.2.
- Unity Editor `6000.3.19f1 (7689f4515d75)`. The checked-in package lock resolved URP 17.3.0, Test Framework 1.6.0, and uGUI 2.0.0. No package manifest or lock versions were changed.
- Docker CLI 29.6.1 is installed. Its `desktop-linux` server is unavailable: `docker info` reports the `dockerDesktopLinuxEngine` named pipe does not exist.
- PostgreSQL is not available locally; `CODEQUEST_TEST_DATABASE_URL` is unset. The repository's Compose and new CI integration job use PostgreSQL 17.5 Alpine.

## Reproduction and resolution of the Windows HTTP hang

Command used for diagnostics:

```powershell
& .\.venv\Scripts\python.exe -c "import faulthandler, pytest; faulthandler.dump_traceback_later(6); raise SystemExit(pytest.main(['BackendAPI/tests/test_api.py::test_health_and_readiness', '-vv', '-s']))"
```

The captured stack stopped in `socket.socketpair()` → `socket.accept()` while AnyIO created the Windows Proactor event loop for Starlette `TestClient`. The request had not entered FastAPI. A standalone `socket.socketpair()` succeeded when run with local-socket access, and the same focused HTTP test passed in that environment. This is the workspace sandbox's loopback restriction, not an application lifespan, SQLite, or fixture deadlock; application/test code was not changed to mask it. Run Windows `TestClient` checks in a normal local environment or a runner that permits loopback sockets.

The HTTP integration test also exposed a real configuration injection defect: the submission route called `get_settings()` directly, bypassing FastAPI dependency overrides. It now receives `Settings = Depends(get_settings)`, keeping production behavior unchanged and making the route testable with explicit settings.

## Security changes

- Terminal submission source is deleted from active database rows after `CODEQUEST_SUBMISSION_SOURCE_RETENTION_DAYS` (default 30 days); a backend lifespan task performs cleanup hourly. Queued/running submissions are retained. Idempotency hashes and result metadata remain for retries/audit. Database backups and transaction logs need separately configured expiry.
- Evaluator output is written to a private temporary file with a Linux `RLIMIT_FSIZE` ceiling; evaluator subprocesses start in a fresh process group and the timeout kills the group. The outer launcher retains its container kill path.
- Worker requests now validate the source SHA-256 against the body, submission UUID and challenge identity, function identifier, test lists, and numeric bounds. Evaluator image configuration must match a full `@sha256:<64 hex>` digest.
- The worker HTTP adapter caps request threads at 8, evaluation jobs at 2, and per-request socket time at 10 seconds. It does not log request bodies or source.
- Deterministic tests mock the Docker CLI to verify restrictive launch flags, timeout kill requests, and digest rejection. They never execute hostile source on the developer host. No claim of complete container isolation is made.

## Reproducible commands and results

Run from `D:\CodeQuestAI`:

```powershell
& .\.venv\Scripts\python.exe -m ruff check BackendAPI PythonExecutionService Tools
& .\.venv\Scripts\python.exe -m ruff format --check BackendAPI PythonExecutionService Tools
& .\.venv\Scripts\python.exe Tools\validate_docs.py
& .\.venv\Scripts\python.exe Tools\validate_config.py
& .\.venv\Scripts\python.exe Tools\export_openapi.py --check
& .\.venv\Scripts\python.exe -m pytest -q --tb=short
```

Final full suite: **49 passed, 3 skipped**, with one Starlette deprecation warning. The three skips are PostgreSQL migration round-trip, quest concurrency, and submission concurrency because `CODEQUEST_TEST_DATABASE_URL` is unset. The suite includes FastAPI HTTP/auth checks and deterministic worker-contract/launcher tests.

Unity Editor commands (omit `-quit` when running Test Runner):

```powershell
& 'C:\Program Files\Unity\Hub\Editor\6000.3.19f1\Editor\Unity.exe' -batchmode -nographics -quit -projectPath 'D:\CodeQuestAI\GameClient' -logFile 'D:\CodeQuestAI\GameClient\Logs\m8-compile.log'
& 'C:\Program Files\Unity\Hub\Editor\6000.3.19f1\Editor\Unity.exe' -batchmode -nographics -projectPath 'D:\CodeQuestAI\GameClient' -runTests -testPlatform EditMode -testResults 'D:\CodeQuestAI\GameClient\TestResults\m8-editmode.xml' -logFile 'D:\CodeQuestAI\GameClient\Logs\m8-editmode-real.log'
& 'C:\Program Files\Unity\Hub\Editor\6000.3.19f1\Editor\Unity.exe' -batchmode -nographics -projectPath 'D:\CodeQuestAI\GameClient' -runTests -testPlatform PlayMode -testResults 'D:\CodeQuestAI\GameClient\TestResults\m8-playmode.xml' -logFile 'D:\CodeQuestAI\GameClient\Logs\m8-playmode.log'
```

Compilation completed under 6000.3.19f1 with no C# compiler errors in the log. Final EditMode reported 8 passed, 0 failed, 0 skipped. Offline PlayMode reported 4 passed, 0 failed, 1 skipped (`Ignored` for the live API test when its opt-in environment was absent). A separate live PlayMode run against the locally started FastAPI service and SQLite database reported 5 passed, 0 failed, 0 skipped. The live run exercised health, readiness, public catalog retrieval, and fail-closed unauthenticated protected-profile behavior; it did not use a real OIDC provider. Test XML/logs are in Unity-ignored output directories. Unity online-services configuration timed out, but Editor compilation and Test Runner completed.

PostgreSQL integration command for a fresh, disposable database named exactly `codequest_test`:

```powershell
$env:CODEQUEST_TEST_DATABASE_URL = 'postgresql+psycopg://codequest:replace-local-password@127.0.0.1:5432/codequest_test'
& .\.venv\Scripts\python.exe -m pytest -q BackendAPI/tests/test_migrations.py::test_postgres_migration_round_trip_when_configured BackendAPI/tests/test_quest_postgres_concurrency.py BackendAPI/tests/test_submission_postgres_concurrency.py
```

The command was not run because the PostgreSQL/Docker server was unavailable. CI now provisions the pinned PostgreSQL 17.5 service and runs migration round-trip, concurrent quest revision, same-key submission idempotency, and duplicate-pass reward checks.

## Verification matrix

| Area | Status | Evidence / limitation |
|---|---|---|
| Python lint and formatting | PASSED | Final `ruff check` and `ruff format --check` passed; 43 files are formatted. |
| Backend, HTTP, auth, migration SQLite, and deterministic worker tests | PASSED | `49 passed, 3 skipped`; all three skips require PostgreSQL. |
| Docs, config, generated OpenAPI | PASSED | Validators and `export_openapi.py --check`. |
| Unity compilation | PASSED | Editor 6000.3.19f1, exit code 0, log showed script compile and no C# compiler errors. |
| Unity EditMode | PASSED | 8 passed, 0 failed, 0 skipped. |
| Unity PlayMode | PASSED | Offline: 4 passed, 0 failed, 1 skipped. Live API: 5 passed, 0 failed, 0 skipped against local FastAPI/SQLite. |
| Windows HTTP-test root cause | PASSED | Reproduced stack and verified with loopback-enabled execution. |
| PostgreSQL migrations and concurrency | BLOCKED | Docker Linux daemon and local PostgreSQL unavailable; CI job added but not run here. |
| Real Python execution/adversarial sandbox behavior | BLOCKED | Docker Linux daemon unavailable; mocked launcher tests are not isolation evidence. |
| Authenticated live API ↔ worker integration | BLOCKED | Live Unity tested public endpoints and fail-closed unauthenticated profile behavior. Authenticated requests still use controlled test-key/JWKS route tests and mocked dispatcher; no live worker/IdP. |
| Production sandbox approval | BLOCKED | Requires supported Linux runtime, adversarial execution tests, and host/daemon security review. |

## Remaining risks and next milestone

The API/worker trust boundary still depends on protecting the worker token and the launcher's Docker-daemon access. Host kernel configuration, seccomp/AppArmor policy, hostile-code escape resistance, live process cleanup, network denial, and real output-flood behavior have not been observed on Linux. Source deletion from active rows does not erase existing backups or transaction logs. Production sandbox readiness remains explicitly unapproved.

Next, run the PostgreSQL CI integration job and evaluator adversarial suite on the intended Linux runner, establish backup retention, inspect Docker host privileges and MAC/seccomp policy, and run authenticated end-to-end Unity/API/worker integration before beginning another feature milestone.
