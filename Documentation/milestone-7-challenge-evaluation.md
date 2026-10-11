# Milestone 7: Trusted Python challenge evaluation

## Scope and outcome

This milestone adds an authenticated, versioned submission contract, durable submission and attempt records, progressive hints, a separate evaluator service boundary, and Unity code-entry/polling integration. It does not add multiplayer, arbitrary host-side execution, a tutor provider, or general-purpose Python environments.

The learner may submit source and a UUID idempotency key for an exact published challenge version. The backend accepts only definitions with a supported function mode, a function name, visible cases, and at least one hidden case. Older published challenge versions without evaluator rules remain readable but cannot be submitted. Challenge source and rules are immutable per `(slug, version)`; curriculum changes create another version.

## API and persistence

See [the v1 API contract](api/README.md#challenge-submission-and-evaluation-v1) and generated [OpenAPI v1](api/openapi-v1.json). The routes are:

- `GET /api/v1/challenges/{slug}/versions/{version}` returns public content only.
- `GET /api/v1/challenges/{slug}/hints?version=...&level=...` unlocks authenticated hints sequentially.
- `POST /api/v1/challenges/{slug}/submissions` queues source under the caller's identity.
- `GET /api/v1/me/submissions/{submission_id}` returns caller-owned status and sanitized results.

The new reversible migration adds evaluator limits, hidden test and hint tables, player hint unlocks, submission source/hash/idempotency fields and statuses, evaluation attempts, and supporting constraints/indexes. The server computes score from stored test counts and thresholds. A confirmed pass can submit a trusted quest event in the same transaction; client payloads cannot supply scores, XP, hidden tests, or pass claims. Same-key/equivalent requests replay the existing row, while a changed payload conflicts. Queue admission uses per-profile locking/rate limits, a global queue cap, and uniqueness constraints. PostgreSQL advisory locking and row locking are production concurrency controls; SQLite tests do not verify those guarantees.

## Runtime boundary and threat model

FastAPI never evaluates submitted source. It calls a separately configured internal worker and fails closed if the worker URL/token are not configured. The worker validates bounded JSON, limits concurrent jobs, invokes a digest-pinned Linux evaluator image through Docker, and returns bounded structured outcomes. The job container is configured without network access, host mounts, secrets, or an attached Docker socket; it uses a read-only root, non-root UID, dropped capabilities, resource limits, and a wall-clock kill path.

The worker launcher itself requires access to the Docker daemon to start and stop containers. This host/daemon control plane is a privileged boundary and has not received operational or adversarial verification. Container settings alone do not prove sandbox security. The Docker Linux engine was unavailable during implementation, so image execution, isolation, cleanup, and hostile-code resistance are unverified. Do not expose the worker or configure production submissions until the host/runtime boundary receives security review and adversarial tests. See [ADR-0011](adr/0011-python-execution-isolation.md).

Limits are enforced at the HTTP/job schema and container/process layers. The current implementation uses a bounded submission source size, worker request/response limits, two worker slots, per-player rate caps, per-test deadlines, output caps, container memory/CPU/PID/disk constraints, and an overall worker timeout. These are initial controls, not a certified capacity or isolation claim. Function-style JSON cases are supported; stdin-based challenges and optional package profiles are not.

## Privacy, retries, and UI state

Submission source is stored to support delivery/retry and currently has no automatic expiry. Access is restricted to the owning profile at API reads; hidden test definitions and raw worker output are not returned to learners. Source-retention duration, operational logging policy, worker host choice, quotas, allowed packages, and security review ownership remain open decisions.

Unity reuses a client submission UUID when retrying the same source and creates a new key when the source changes. It polls the caller-owned submission record. Only a backend `passed` result is treated as confirmed progress; queued/running states remain pending, and terminal failure/timeout/internal errors do not award client-side rewards. A retry after a request timeout may replay the original record. Protected calls require a real configured OIDC token; no fake credentials or local auth bypass is provided.

## Setup and validation

Install the repository's pinned Python environment from `pyproject.toml`/`uv.lock`. Run the API using the documented backend setup and configure `CODEQUEST_EVALUATION_WORKER_URL` plus a locally generated `CODEQUEST_EVALUATION_WORKER_TOKEN` in an untracked `.env`. Build a reviewed evaluator image and provide its immutable `CODEQUEST_EVALUATOR_IMAGE` digest to the worker. Never commit tokens or use a mutable image tag for deployment. A local worker without Docker/Linux runtime is intentionally unavailable; there is no host-Python fallback.

SQLite service and migration tests cover schema behavior, ownership, idempotency, limits, score calculation, and duplicate reward avoidance. PostgreSQL-specific locking/concurrency remains unverified unless a configured PostgreSQL integration test is actually run. Unity compilation and live HTTP integration must likewise be reported only when executed in the corresponding environment.

## Next milestone

Review the execution host and sandbox boundary, define source retention and evaluator runtime policy, validate with adversarial tests on the supported Linux runtime, and run PostgreSQL concurrency tests. Then complete Unity Editor verification and end-to-end authenticated API integration before expanding challenge content or adding gameplay features.
