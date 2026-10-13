# AN AGENTIC AI-POWERED 3D OPEN-WORLD RPG FOR ADAPTIVE PYTHON PROGRAMMING EDUCATION

CodeQuest AI is an adaptive, gamified educational platform combining an interactive 3D role-playing game (RPG) built in Unity with an agentic, multi-tiered backend architecture for real-time Python programming instruction. The system pairs in-world exploratory quests with code-evaluation sandboxes, contextual pedagogy, and standards-compliant authentication.

---

## 1. Project Overview & Current Implemented Features

### Implemented Capabilities
- **Interactive 3D Client (Unity 6 / URP):**
  - Third-person character locomotion, orientation-based camera rig, jump physics, and collision handling.
  - Integration of Kenney 3D character meshes and animation controller with active locomotion states (Idle, Run, Jump).
  - Modular NPC interaction framework with proximity detection, dialogue trees (Mira, Signal Keeper), and quest portal activation.
  - In-game monospace Python challenge editor modal HUD with function-contract validation, starter code injection, execution status polling, and sanitized feedback display.
  - Native Windows desktop OIDC client supporting Authorization Code + PKCE (S256) via loopback listener for Keycloak integration.
- **FastAPI Modular Monolith Backend:**
  - RESTful APIs for game health (`/healthz`, `/readyz`), curriculum catalog (`/api/v1/regions`, `/api/v1/challenges`), player profile, and authoritative quest event handling (`/api/v2`).
  - Strict OIDC RS256 JWT validation against configured issuer, audience, and JWKS endpoints; fails closed when authentication is unconfigured.
  - Reversible Alembic migrations with PostgreSQL schema support covering player profiles, quest progressions, and challenge submission records.
- **Python Execution Sandbox (Evaluator Service):**
  - Isolated runner enforcing CPU, wall-clock time, file-size (`RLIMIT_FSIZE`), process tree cleanup, and memory constraints.
  - Worker dispatch architecture designed for disposable, unprivileged Linux container execution without host networking or root privileges.
- **Comprehensive Documentation & Academic Report:**
  - Full LaTeX source code, figure assets, and compiled PDF deliverables for the 58-page major project report.

---

## 2. Technology Stack & Architecture

| Layer | Technologies & Frameworks | Description |
| :--- | :--- | :--- |
| **Game Client** | Unity 6000.3.19f1, URP, C# (.NET Standard 2.1) | 3D client, URP graphics pipeline, PhysX, custom UI runtime. |
| **Backend API** | FastAPI, Pydantic v2, SQLAlchemy 2.0, Uvicorn | High-performance asynchronous REST API, OpenAPI contract generation. |
| **Database** | PostgreSQL 17.5 / SQLite (for offline test harnesses), Alembic | Relational storage for player progress, curriculum, and submissions. |
| **Execution Sandbox** | Python 3.11, Docker (isolated Linux container) | Resource-limited, sandboxed evaluation of learner code submissions. |
| **Identity / Auth** | Keycloak 26.8.0, OIDC (RS256 JWT, PKCE S256) | Standards-compliant identity management and token issuance. |
| **Report / Docs** | LaTeX (TeX Live), BibTeX | Academic project report and architectural documentation. |

```
                              [ Unity 3D Client ]
                                /              \
        (OIDC Auth Code + PKCE) /                \ (RESTful JSON / Bearer JWT)
                               v                  v
                     [ Keycloak 26.8.0 ]    [ FastAPI Backend API ]
                                                   |         |
                               (SQLAlchemy/Alembic)|         | (Shared Token Dispatch)
                                                   v         v
                                          [ PostgreSQL DB ] [ Python Evaluator Worker ]
                                                                     |
                                                                     v
                                                            [ Docker Sandbox Job ]
```

---

## 3. Repository Directory Structure

```
CodeQuestAI/
├── .github/workflows/       # GitHub Actions CI definitions (baseline.yml)
├── BackendAPI/              # FastAPI application, database models, schemas, and tests
├── College Report/          # LaTeX report source, chapters, figures, bibliography, and build scripts
├── Database/                # Alembic migration environment and version scripts
├── Documentation/           # System design ADRs, API specs, and setup guides
│   ├── adr/                 # Architecture Decision Records
│   ├── api/                 # OpenAPI v1/v2 specifications
│   └── local-keycloak.md    # Local Keycloak realm and OIDC setup guide
├── GameClient/              # Unity 6 project source, assets, and project settings
│   ├── Assets/              # CodeQuest runtime scripts, URP settings, and Kenney assets
│   ├── Packages/            # Unity package manifests and locks
│   └── ProjectSettings/     # Physics, tags, graphics, and quality settings
├── Infrastructure/          # Docker Compose configurations (compose.yaml)
├── PythonExecutionService/  # Sandboxed code execution runner, worker, and container tests
├── Tools/                   # Verification tools (docs, config, OpenAPI export)
├── pyproject.toml           # Locked Python project dependencies and tool configs
└── uv.lock                  # Pinned uv dependency lockfile
```

---

## 4. Prerequisites & Setup Instructions

### Prerequisites
- **Operating System:** Windows 10/11 x64.
- **Python:** Python 3.11.9 managed via [uv](https://docs.astral.sh/uv/) (v0.13.0 recommended).
- **Unity:** Unity Editor **6000.3.19f1** via Unity Hub.
- **Container Engine:** Docker Desktop (with Linux container support enabled).
- **Git:** Git for Windows.

### Initializing Python Dependencies
From the repository root in PowerShell:
```powershell
uv sync --locked --all-groups
Copy-Item .env.example .env
```

---

## 5. Starting the Services

### 1. Database (PostgreSQL)
Run the bundled container or start a local PostgreSQL 17 instance:
```powershell
docker compose -f Infrastructure/compose.yaml up -d postgres
```
Apply migrations and seed initial curriculum data:
```powershell
$env:PYTHONPATH="."
uv run alembic -c Database/alembic.ini upgrade head
uv run python -m BackendAPI.app.db.seed
```

### 2. Backend API
Launch the FastAPI development server:
```powershell
$env:PYTHONPATH="."
uv run python -m uvicorn BackendAPI.app.main:app --reload --host 127.0.0.1 --port 8000
```
API health and OpenAPI docs will be available at:
- Health check: `http://127.0.0.1:8000/healthz`
- Interactive OpenAPI docs: `http://127.0.0.1:8000/docs`

### 3. Identity Provider (Keycloak - Optional for Local Auth)
Follow the detailed guide in [Documentation/local-keycloak.md](Documentation/local-keycloak.md) to initialize Keycloak 26.8.0 on port 8080 with the `codequest-dev` realm and `codequest-unity` client.

### 4. Code Evaluator Worker
In a Linux-capable container environment:
```powershell
$env:PYTHONPATH="."
$env:CODEQUEST_EVALUATION_WORKER_TOKEN="<configure-secure-local-token-32-chars>"
uv run python -m PythonExecutionService.worker
```

### 5. Unity Game Client
1. Open Unity Hub and add `D:\CodeQuestAI\GameClient`.
2. Ensure editor version is set to **6000.3.19f1**.
3. Open `Assets/Scenes/Bootstrap.unity`.
4. Press **Play** in the editor, or build standalone executable via **File → Build Settings**.

---

## 6. Running Tests & Validations

Run the automated suites from repository root:

```powershell
# Set Python path
$env:PYTHONPATH="."

# Linting and formatting checks
uv run ruff check .
uv run ruff format --check .

# Documentation and configuration checks
uv run python Tools/validate_docs.py
uv run python Tools/validate_config.py
uv run python Tools/export_openapi.py --check

# Backend API tests (47 unit/contract tests)
uv run pytest BackendAPI/tests

# Evaluator tests (10 contract tests)
uv run pytest PythonExecutionService/test_contract.py
```

In Unity Editor, run the test suites via **Window → General → Test Runner**:
- **EditMode Tests:** Movement rules, quest definitions, contract serialization, OIDC PKCE, and asset validation.
- **PlayMode Tests:** Runtime HUD bootstrapping, interactor trigger responses, and portal triggers.

---

## 7. Environment Variable Configuration

Copy `.env.example` to `.env`. Example safe local values:
```dotenv
CODEQUEST_ENV=local
CODEQUEST_APP_NAME=CodeQuestAI
CODEQUEST_HOST=127.0.0.1
CODEQUEST_PORT=8000
CODEQUEST_DATABASE_URL=postgresql+psycopg://codequest:local-dev-password@127.0.0.1:5432/codequest_dev

# Optional local Keycloak OIDC (uncomment when Keycloak is running):
# CODEQUEST_AUTH_ISSUER=http://localhost:8080/realms/codequest-dev
# CODEQUEST_AUTH_AUDIENCE=codequest-api
# CODEQUEST_AUTH_JWKS_URL=http://localhost:8080/realms/codequest-dev/protocol/openid-connect/certs
```
*Note: Real secrets, API keys, or production passwords must never be committed to Git.*

---

## 8. Current Limitations & Planned Roadmap

To ensure academic and technical transparency, the following scope boundaries are established:
- **Implemented Scope:** A single vertical-slice hub region ("Variable Valley"), initial NPC interaction dialogues, function-contract validation, loopback PKCE authentication, and containerized Python sandboxing.
- **Not Yet Implemented / Future Scope:**
  - Additional open-world biomes (e.g., *Function Forest*, *Loop Lagoon*) exist as curriculum data only, not 3D scenes.
  - Multiplayer / cooperative networking (zero Netcode/Mirror implementation in current demonstrator).
  - Advanced curriculum expansion beyond the foundational introductory sequence (40 total challenges planned).
  - Combat mechanisms, boss encounters, and physical obstacle damage systems.
