# Milestone 9: Playable coding quest vertical slice

Date: 2026-10-11. Starting checkpoint: `f54e54c9e1f7ca5382e56a29ddabb1495af7593f`.

## Implemented slice

The Bootstrap runtime now composes the original Signal Keeper greybox alongside a small Variable Valley route. Mira is an interactable mentor; her dialogue has an explicit quest acceptance choice. Acceptance submits the registered `interact/valley-mentor` event to the existing v2 quest service. A visible path, gate, beacon, and the existing third-person movement/camera provide the route from the player start to the region. Press **E** at the gate to open the Variable Valley catalog; press **J** for the objective journal.

The backend seed adds immutable v1 content for region `variable-valley`, objective `valley-variables-and-io`, and quest `variables-in-the-valley`. It is additive and idempotent: no existing region, quest, challenge version, migration, or roadmap region is removed or rewritten. Five deterministic function challenges are served by the existing public v1 catalog and exact-version read routes:

| Sequence | Versioned challenge | Learning focus |
|---:|---|---|
| 1 | `valley-name-tag` v1 | Store a string input and return a greeting |
| 2 | `valley-sunplot-area` v1 | Calculate and store a value from two inputs |
| 3 | `valley-signal-label` v1 | Convert a number and return formatted text |
| 4 | `valley-seed-count` v1 | Store and return a repeated-group total |
| 5 | `valley-beacon-message` v1 | Combine two inputs into the final beacon output |

Each has a public statement, function signature, starter code, examples, two visible cases, two separately stored hidden cases, deterministic evaluator limits, and three progressive authored hints. Public content includes only public cases and hints. Catalog sequence/prerequisite metadata drives the client list. The evaluator's current contract is function arguments and return values; stdin/`input()`/stdout modes remain unsupported.

The quest rules require the mentor acceptance interaction, then each of the five matching passed submission records in order. The existing trusted submission result path advances those objectives from backend state. The quest grants 50 XP through the existing server reward ledger only on completion. The Unity client refreshes quest progress after a confirmed pass and displays XP only after the authoritative progression request succeeds. The player client cannot declare a pass, advance a quest objective, or grant XP.

## Unity coding panel and tutor

The in-game panel retrieves the exact published challenge version. It provides a multiline monospace editor, challenge instructions/examples, a local function-header format check, a separate authenticated **Submit to evaluator** action, queue/running/terminal state display, sanitized visible-case feedback, retry with the same key for unchanged source, polling cancellation, and a next-step action. The local check verifies only that the expected `def` header appears; it never parses or executes submitted code. Hidden cases are never fetched by the game client.

The editor is not syntax-highlighted because the current legacy uGUI/InputField architecture has no supported highlighting widget/package installed. `RuleBasedTutorHintProvider` consumes public catalog hints in order and adds contextual prompts based on prior progress and sanitized error category. It receives no source code and makes no external request; the interface can later host another provider without changing submission authority.

Quest service startup now caches progress returned before quest assets are registered and applies matching versions when they register. It can refresh authoritative progress after a challenge pass. Pending/failed event state remains distinct and the bounded event queue remains in memory only.

## Run locally

From the repository root, after installing the pinned project dependencies and applying migrations:

```powershell
uv run python -m alembic upgrade head
uv run python -m BackendAPI.app.db.seed
uv run python -m uvicorn BackendAPI.app.main:app --reload
```

Open `GameClient/Assets/Scenes/Bootstrap.unity` in Unity `6000.3.19f1`, press Play, choose **Start exploring**, talk to Mira, accept the quest, walk to the gate, and open the catalog. With the current checked-in bootstrap token provider, protected submission and quest writes fail closed with an explicit sign-in message. Public catalog content, navigation, local header feedback, and rule-based hints remain usable.

Do not enable arbitrary execution without a real OIDC provider, the isolated worker, a supported Linux container runtime, and the M8 security review gates. No submitted code is executed in Unity, FastAPI, or the developer host.

## Validation results

Results from the final M9 verification pass:

| Check | Result |
|---|---|
| Backend full suite | 52 passed, 3 PostgreSQL tests skipped (no `CODEQUEST_TEST_DATABASE_URL`), one Starlette deprecation warning |
| Ruff lint/format | `ruff check BackendAPI PythonExecutionService Tools` passed; `ruff format --check BackendAPI PythonExecutionService Tools` passed (44 files). The repository-wide `ruff check .` still reports 20 pre-existing long-line findings in the already-applied immutable migration `Database/migrations/versions/20261011_0003_challenge_evaluation.py`; the migration was not rewritten. |
| Documentation/config/OpenAPI validators | Passed after the milestone report was added |
| Unity compilation | Passed in Editor `6000.3.19f1 (7689f4515d75)`; no C# compiler errors |
| Unity EditMode | 12 passed, 0 failed, 0 skipped |
| Unity PlayMode without live API | 6 passed, 0 failed, 1 skipped (opt-in live API test) |
| Live API catalog check | FastAPI health and readiness returned HTTP 200 on the local SQLite database. Unity PlayMode live API suite: 7 passed, 0 failed, 0 skipped; public regions/catalog, five Valley challenges, exact `valley-name-tag` v1 retrieval, and the unauthenticated profile request's fail-closed response were exercised. No authenticated protected operation is claimed. |
| PostgreSQL migration/concurrency | Blocked locally; only CI job is configured, not run here |
| Real Python container execution/adversarial isolation | Blocked: Docker Linux engine unavailable |
| Real OIDC authenticated Unity/API/worker path | Blocked: no identity provider/token adapter or configured evaluator worker |

Backend tests use SQLite for fast catalog, rule, and transactional checks. They use a test-only worker result to exercise the established server result handler; this does not execute learner Python and is not evidence of a live evaluator. The live Unity HTTP check also used SQLite. PostgreSQL locking is not claimed based on SQLite. One earlier live PlayMode attempt failed because its backend process exited before Unity made its requests; that run was discarded and the full test was rerun successfully with the backend kept alive.

## Remaining limitations and readiness

The playable UI and server-integration boundaries exist, but the complete acceptance path through a real Python pass and persisted reward is not operational on this workstation. Unity is currently composed with `UnauthenticatedTokenProvider`; protected routes reject requests. The separate worker and Docker Linux engine are not running, so a submission cannot be safely evaluated here. Restart restoration is implemented against the existing authenticated quest progress API but remains unverified against a real OIDC identity. The database contract, ordered progression, reward uniqueness, and client-side pass protection have backend SQLite tests; PostgreSQL concurrency remains open.

The hub is intentionally primitive greybox art. No paid assets, new Unity packages, backend services, AI keys, or migration were added. Later roadmap content—other regions, traversal challenges, bosses, items, inventory, achievements, adaptive/AI tutoring, multiplayer, and teacher/admin dashboards—remains planned.

**Readiness:** ready for a controlled UI/content review and authenticated local integration setup; not ready to claim a fully playable trusted-evaluation/reward loop or production sandbox approval. The next gate is selecting/configuring the real OIDC client and running the trusted evaluator on a reviewed Linux host, then exercising a live submission through quest completion and a restored session.
