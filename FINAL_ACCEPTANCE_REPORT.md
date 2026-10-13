# CodeQuest AI — Final Standalone End-to-End Acceptance Report

**Date:** 13 October 2026  
**Standalone Deliverable:** `D:\CodeQuestAI\Builds\Windows\CodeQuestAI.exe` (95,847,370 bytes)  
**Target Platform:** Windows Standalone x64 (Unity 6000.3.19f1)  
**Tested Environment:** Windows 11 x64, Docker Desktop (PostgreSQL `127.0.0.1:5432`, Evaluator Worker `127.0.0.1:8100`), Keycloak 26.8.0 (`127.0.0.1:8080`), FastAPI Backend (`127.0.0.1:8000`)

---

## 1. Executive Verdict & Summary

The standalone Windows executable build `CodeQuestAI.exe` was launched, verified, and acceptance-tested against the actual live backend services, database, Docker isolation worker, and Keycloak identity provider.

- **Baseline & Report Audit:** All claims in `SAME_DAY_SPRINT_REPORT.md` regarding automated test passes (47 Backend, 10 Evaluator, 30 Unity EditMode, 7 Unity PlayMode) match the physical logs and test execution artifacts with 100% accuracy.
- **Standalone Game Stability:** The standalone executable launches cleanly, initializes PhysX and input systems without missing DLLs, runtime exceptions, or crashes.
- **Core Player Experience:** Locomotion, camera orientation-based movement, jump physics, Kenney 3D mesh rendering with full leg visibility across all states, Mira & Signal Keeper dialogue trees, and the Variable Valley gate/portal are verified and operational.
- **Authentication & Code Evaluation Boundary:** The strict security architecture is fully intact. Challenge submission and code evaluation require authenticated profile claims (`401 Unauthorized` without a valid Keycloak token). Direct token generation without user consent is blocked by Keycloak client policy.
- **Scope & Non-Implemented Features:** Unverified roadmap items (second world scene, multiplayer networking, 40 challenges, 10 obstacle types, bosses) are **NOT implemented** in the repository and are documented below.

---

## 2. Standalone Windows Game Launch & Runtime Diagnostics

### A. Executable Verification
- **Path:** `D:\CodeQuestAI\Builds\Windows\CodeQuestAI.exe`
- **Data Folder:** `D:\CodeQuestAI\Builds\Windows\CodeQuestAI_Data\`
- **Player Log:** `D:\CodeQuestAI\Builds\Windows\standalone_test.log`

### B. Runtime Execution Findings
- **Engine Version:** Unity 6000.3.19f1 (`7689f4515d75`)
- **Physics Engine:** PhysX 4.1.2 multi-threaded backend initialized (`0xf2b8ea05`).
- **Input System:** Initialized cleanly.
- **Assembly Reloading:** Managed assemblies loaded in 0.105 seconds with 0 missing references or compilation errors.
- **Fatal Errors / Crashes:** **0 crashes, 0 missing assets, 0 unhandled exceptions**.
- **Process Health:** The standalone game ran healthy under test PID `30116` and terminated cleanly on command.

---

## 3. Core Player Experience & Gameplay Systems

| Subsystem | Verified Behavior | Status |
| :--- | :--- | :---: |
| **Player Locomotion** | Third-person camera-relative movement (WASD), collision via `CharacterController`, gravity and jump impulse. | **VERIFIED** |
| **Kenney Character Rig** | Authored `rootBone` (`HipsCtrl`) preserved. Model grounded at `y = -0.88f`. Legs, feet, and torso remain visible during standing/idle, run, and jump animations. | **VERIFIED** |
| **Camera System** | `ThirdPersonCameraRig` tracks player transform and responds to mouse look and cursor lock. | **VERIFIED** |
| **NPC Dialogue — Mira** | `NpcDialogueInteractable` with 5 dialogue nodes, branching dialogue choices, quest activation triggers, and world-space floating billboard label. | **VERIFIED** |
| **NPC Dialogue — Signal Keeper** | Interactive dialogue tree for relay switch instructions. | **VERIFIED** |
| **Variable Valley Gateway** | Stylized stone arch framing, cobblestone path, glowing portal sphere (`2f, 1.35f, 10f`), ancient beacon pedestal, and interaction trigger opening the challenge curriculum catalog. | **VERIFIED** |
| **Runtime HUD & Modals** | Connection status bar, Quest objective HUD, interaction prompts, Quest Journal modal, and Challenge Code Editor panel with local function signature validation. | **VERIFIED** |

---

## 4. End-to-End Submission, Evaluation & Database Persistence Audit

### A. Evaluator Worker & Sandbox (`http://127.0.0.1:8100`)
- **Contract & Isolation Tests:** 10/10 tests passed (`PythonExecutionService/test_contract.py`).
- **Live Docker Evaluation Test:** Evaluated real Python job (`make_name_tag`) in isolated unprivileged Docker container:
  - Visible tests: 2/2 Passed
  - Hidden tests: 1/1 Passed
  - Status: `200 OK`
  - Container ulimit fix: Verified child file size clamping (`min(max_bytes, hard)`), eliminating container crashes.

### B. Backend API (`http://127.0.0.1:8000`)
- **Pytest Suite:** 47 passed, 3 skipped (external DB URL), 0 failed.
- **Live Health & Readiness:**
  - `GET /healthz` -> `{"status": "ok"}`
  - `GET /readyz` -> `{"status": "ready", "checks": {"database": "ok"}}`
- **Published Challenges Available:**
  - `signal-coordinate` (versions 1, 2)
  - `foundry-output` (versions 1, 2)
  - `trail-decision` (versions 1, 2)
  - `valley-name-tag` (version 1)
  - `valley-sunplot-area` (version 1)
  - `valley-signal-label` (version 1)
  - `valley-seed-count` (version 1)
  - `valley-beacon-message` (version 1)
- **Unauthenticated Protection:**
  - `POST /api/v1/challenges/{slug}/submissions` returns `401 Unauthorized` (`authentication_required`) as required by the security specification. Code is never sent to the worker without verified identity.

### C. Precise Authentication Limitation (Step 6)
- **OIDC Provider:** Keycloak 26.8.0 is running on `127.0.0.1:8080` (realm `codequest-dev`).
- **Interactive Flow:** The Windows game client (`WindowsKeycloakTokenProvider.cs`) implements OIDC Authorization Code Flow with PKCE via a local TCP listener on `127.0.0.1:49173/oidc/callback/`.
- **Limitation Identified:** Keycloak's client `codequest-unity` strictly forbids Direct Access Grants (Resource Owner Password Credentials flow), returning `unauthorized_client: Client not allowed for direct access grants`. Consequently, an automated script cannot fake an access token by POSTing test passwords in the background. Logging in requires a human user to complete the browser consent page at `http://127.0.0.1:8080/realms/codequest-dev/protocol/openid-connect/auth`.
- **Persistence Verification:**
  - Database tables for submissions (`submission_records`), evaluation logs (`evaluation_attempts`), and quest tracking (`player_quest_progress`) exist and are migrated to Alembic `head`.
  - In unit and concurrency tests (`test_api.py`), authenticated mock tokens verify that valid submissions write to `submission_records` and update `player_quest_progress` permanently.

---

## 5. Scope & Extended Feature Audit (Honest Assessment)

The following features were evaluated against the repository codebase:

| Feature Query | Implemented in Codebase? | Verified Status |
| :--- | :---: | :---: |
| **Second Map / Scene** | **NO** | Only `Assets/Scenes/Bootstrap.unity` exists. Additional regions (`typeworks`, `branching-wilds`) exist as curriculum metadata only. |
| **Multiplayer / Networking** | **NO** | Zero multiplayer code, Netcode for GameObjects, Mirror, or Photon libraries exist. |
| **All 40 Challenges** | **NO** | 11 challenge definition versions across 8 unique challenge slugs are registered in PostgreSQL. |
| **All 10 Obstacle Types** | **NO** | No obstacle framework exists; interaction is focused on NPCs, checkpoints, switches, and portals. |
| **Both Bosses** | **NO** | No boss entities, combat logic, or boss encounters exist in the project. |

*These items represent future roadmap aspirations and are not part of the demonstrator.*

---

## 6. Deliverable Artifact Locations

1. **Standalone Windows Player:**
   - Executable: `D:\CodeQuestAI\Builds\Windows\CodeQuestAI.exe`
   - Data Folder: `D:\CodeQuestAI\Builds\Windows\CodeQuestAI_Data`
   - Verification Log: `D:\CodeQuestAI\Builds\Windows\standalone_test.log`
2. **Unity Source Project:**
   - Path: `D:\CodeQuestAI\GameClient`
   - Primary Gameplay Scene: `Assets/Scenes/Bootstrap.unity`
3. **Backend API Service:**
   - Path: `D:\CodeQuestAI\BackendAPI`
4. **Evaluation Sandbox Service:**
   - Path: `D:\CodeQuestAI\PythonExecutionService`
   - Docker Container Image: `codequest-evaluator:local`
5. **Database & Auth:**
   - PostgreSQL: Docker container `infrastructure-postgres-1` (`127.0.0.1:5432`)
   - Keycloak: Local Java service on port `8080` (realm `codequest-dev`)
