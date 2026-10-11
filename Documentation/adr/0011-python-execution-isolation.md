# ADR-0011: Per-job restricted Linux container for Python execution

**Status:** Accepted · **Date:** 2026-10-11

## Context

Learners must run real Python, and submissions are hostile by default. The API, database, secrets, host filesystem, and network must remain outside the code's trust boundary. Local development targets Windows with Docker Desktop and 16 GB RAM.

## Decision

Each submission runs in a fresh, disposable Linux container created by a dedicated execution service. The service accepts a bounded job schema, starts a non-root process with no network, no host mounts, no Docker socket, no secrets, read-only root filesystem, dropped capabilities, a private temporary workspace, and enforced CPU, memory, process-count, wall-clock, and output limits. The worker returns a bounded structured result; only BackendAPI validates attempt state, tests, scoring, and rewards.

Provisional starter limits (per the baseline, to be calibrated against curriculum libraries): CPU 2 seconds, wall clock 5 seconds, memory 128 MiB, one process, stdout+stderr 64 KiB, bounded source/input payload. These are initial local policy values, not a proof of adequate isolation or production capacity. Use image digests and pinned Python/runtime packages. Reject shell interpolation and kill the full process tree on timeout.

The initial worker implementation is a separate standard-library HTTP service and Docker job launcher under `PythonExecutionService/`. BackendAPI has no source execution code and calls only this internal boundary when both worker URL and token are configured. The launcher requires access to the Docker daemon to create and kill per-job containers; that privileged control plane is part of the threat boundary and must be isolated from the API and reviewed. Each job container is created with no network, host mounts, socket mount, passed secrets, or extra environment; it uses a read-only root, non-root UID, dropped capabilities, no-new-privileges, CPU/memory/process/disk limits, bounded queue slots, and an external timeout that kills the named container. Production runtime/host choice is not yet approved. The local Docker Linux daemon is unavailable; runtime operation and all isolation controls remain unverified. A container is defense-in-depth, not a complete sandbox guarantee; production use is blocked on documented host-kernel/runtime review and adversarial escape/resource tests.

## Consequences

This permits real Python only when the isolated worker runtime is configured and healthy. The initial worker supports function-style JSON input/output cases; standard-input challenges and additional package profiles remain unsupported. Source code is removed from terminal submission rows after `CODEQUEST_SUBMISSION_SOURCE_RETENTION_DAYS` (default 30 days) by an hourly cleanup task; queued/running work is retained until terminal. Digests, idempotency hashes, and result metadata remain, and backups need a separate retention policy. Worker responses are untrusted and checked against stored submission identity, challenge version, evaluator version, and test counts before backend scoring. No worker connection, isolated execution, or reward integration has been verified in this environment. The worker has no database credentials and cannot modify progression directly.

## Threat model and controls

| Threat | Required control |
|---|---|
| Filesystem read/write outside job | no host mounts; read-only root; private ephemeral workspace; non-root UID; destroy workspace |
| Network access/exfiltration | isolated network namespace/no route; outbound and DNS denial verified by adversarial tests |
| CPU/memory/process exhaustion | cgroup quotas, wall deadline, pids limit, bounded queue, kill process tree |
| Output flood or hidden-test disclosure | file-size-limited evaluator output, container memory/time limits, never return hidden tests/expected values |
| Kernel/container escape | patched pinned runtime/host, dropped capabilities, seccomp/MAC policy, no secrets, separate worker host boundary; residual risk remains |
| Cross-job contamination | one fresh container/workspace per job; destroy and verify cleanup |
| Malicious job protocol | schema and size validation, authenticated internal channel, attempt binding, signed/correlated results |
| Image/dependency compromise | pinned digests, reviewed package set, scanning/SBOM, rebuild and patch policy |
| Worker compromise reaches API/DB | separate network/identity, no database credentials, minimal result-only service capability |

### Outstanding security decisions

1. Production host OS and supported isolation runtime, including whether container-only isolation meets risk tolerance. The initial worker launcher has not received adversarial review.
2. Queue and concurrency quotas per account/class and total host capacity.
3. Exact permitted modules and separate standard-library/NumPy/Pandas image profiles.
4. Database backup/transaction-log retention and source erasure timing outside active submission rows.
5. Adversarial test ownership, security review cadence, patch SLA, and incident response.

## References

[Secure Python execution architecture](../04-services-data-security.md#6-secure-python-execution), [resource budgets and risk register](../06-quality-delivery-roadmap.md#1-test-strategy-and-release-acceptance), [software requirements](../01-product-requirements.md#2-software-requirements-specification).
