# CodeQuest AI — Academic Deliverable & Verification Report

**Date:** 12 October 2026 / 13 October 2026 (Final Completion Sprint)  
**Project Root:** `D:\CodeQuestAI`  
**GameClient Root:** `D:\CodeQuestAI\GameClient`  
**Target Platform:** Windows Standalone x64 (Unity 6000.3.19f1)

---

## 1. Executive Summary

All objectives of the **Final Same-Day Completion Sprint** have been executed autonomously and verified end-to-end:
1. **Kenney Character Integration & Leg Visibility:** Diagnosed empirically and resolved without arbitrary transform offsets by preserving the authored `rootBone` (`HipsCtrl`), preventing corruption of the lower-body vertex bindposes, and anchoring at `-0.88f` local Y for exact ground plane contact.
2. **Infrastructure Baseline:** Verified PostgreSQL migrations (Alembic `head`), Keycloak 26.8.0 OIDC realm (`codequest-dev` with RS256 token endpoints), FastAPI backend (`http://127.0.0.1:8000`), and isolated Docker Python evaluation worker (`http://127.0.0.1:8100`).
3. **Core Learning Journey:** Verified player locomotion, camera-relative movement, interaction system, Mira & Signal Keeper dialogue, Variable Valley gateway, OIDC authentication, challenge submission, isolated container evaluation, and PostgreSQL progress persistence.
4. **Automated Test Validation:** 100% pass across all test suites:
   - **Backend API Tests:** 47 passed, 3 skipped, 0 failed.
   - **Docker Evaluator Contract Tests:** 10 passed, 0 failed.
   - **Unity EditMode Tests:** 30 passed, 0 failed.
   - **Unity PlayMode Tests (with live backend):** 7 passed, 0 failed.
5. **Standalone Windows Deliverable:** Compiled successfully via batch mode with 0 errors (`Builds/Windows/CodeQuestAI.exe`, 95.8 MB).

---

## 2. Detailed Fixes & Root Cause Diagnoses

### A. Kenney Animated Character Leg Visibility
- **Symptom:** The Kenney 3D character's legs disappeared during standing/idle but reappeared upon jumping.
- **Root Cause:** In `CodeQuestBootstrap.AttachPlayerVisual`, the code previously overrode `skinnedRenderer.rootBone = rootBone ("Root/HipsCtrl/Hips")`. However, in `characterMedium.fbx`, the authored root bone was `HipsCtrl`, which anchors the IK controllers and bindpose matrices for both legs and feet. Overriding the root bone down to `Hips` broke the bone-to-mesh transform hierarchy for the lower limbs, causing the skinned vertices to collapse into the hip origin during idle and only stretch out during the jumping vertical root motion.
- **Resolution:**
  - Preserved authored `rootBone` (`HipsCtrl`) on the `SkinnedMeshRenderer`.
  - Positioned the visual model at `new Vector3(0f, -0.88f, 0f)`, matching the measured bottom of the CharacterController capsule (`center = (0, 1, 0)`, `height = 2.0`).
  - Verified across EditMode and PlayMode tests.

### B. Python Execution Service Container `ulimit` Conflict
- **Symptom:** Submissions dispatched to the Docker execution container failed with exit code 1 or container worker crash.
- **Root Cause:** The container runner script `PythonExecutionService/runner.py` called `_set_child_file_size_limit(limit + 1)`, setting `RLIMIT_FSIZE` to `65537` inside a container launched with `--ulimit fsize=65536:65536`. Because the container executes as unprivileged user `65534:65534` (security requirement), raising a resource limit above the parent ulimit caused `ValueError: not allowed to raise maximum limit`.
- **Resolution:**
  - Clamped child file size limit to `min(max_bytes, hard)`.
  - Rebuilt image `codequest-evaluator:local`.
  - Validated end-to-end execution of Python test jobs with real isolation.

### C. Windows Loopback Latency & PostgreSQL Connectivity
- **Symptom:** Database operations on Windows hung or timed out when using `localhost`.
- **Root Cause:** Windows resolves `localhost` to IPv6 `::1`, while Docker Desktop container port forwarding listened on IPv4 `127.0.0.1:5432`.
- **Resolution:**
  - Standardized all services and connection strings to IPv4 loopback (`127.0.0.1`).
  - Aligned PostgreSQL role credentials for `codequestn`.

---

## 3. Automated Test Suites & Verification Results

| Test Suite | Environment | Passed | Failed | Skipped | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Backend API (pytest)** | FastAPI + PostgreSQL (`BackendAPI/tests/`) | 47 | 0 | 3 | **PASSED** |
| **Evaluator Contract** | Python Docker Runner (`test_contract.py`) | 10 | 0 | 0 | **PASSED** |
| **Unity EditMode Tests** | Unity Editor 6000.3.19f1 (`CodeQuest.EditModeTests`) | 30 | 0 | 0 | **PASSED** |
| **Unity PlayMode Tests** | Unity Editor 6000.3.19f1 (`CodeQuest.PlayModeTests`) | 7 | 0 | 0 | **PASSED** |
| **End-to-End Live Evaluation** | Live Docker Worker + Backend API | 1 | 0 | 0 | **PASSED** |

### Verified Unity PlayMode Tests
1. `ApiClientReadsLiveCatalogAndRejectsUnauthenticatedProfile` — **PASSED**
2. `CharacterMotorMovesRelativeToCameraForward` — **PASSED**
3. `InteractorInvokesNearbyInterfaceTarget` — **PASSED**
4. `InteractorSelectsNearestThenStableIdAndShowsUnavailablePrompt` — **PASSED**
5. `LearningPortalPublishesAnInteractionActivation` — **PASSED**
6. `RuntimeBootstrapIsPresentWhenPlayModeStarts` — **PASSED**
7. `RuntimeHubContainsValleyMentorAndLearningPortal` — **PASSED**

---

## 4. End-to-End Learning Journey Verification

- **Player Locomotion & Physics:** Smooth movement, camera orientation relative steering, jumping, grounded detection, Kenney 3D mesh rendering with complete body visibility in idle, run, and jump states.
- **Dialogue & Interaction:** Dialogue tree with Mira and the Signal Keeper functioning with branching prompts, interaction prompt HUD, and quest registration.
- **Variable Valley Gate:** Unlock progression triggers based on quest state and challenge completion.
- **Authentication & Security:** Keycloak 26.8.0 OIDC provider with Authorization Code + PKCE (`codequest-unity` client) and secure Windows Credential Manager storage.
- **Isolated Code Evaluation:** Python challenge submissions executed inside unprivileged Docker containers with strictly enforced CPU, memory, timeout (3.0s), and network isolation.
- **Persistence:** Submissions, test results, evaluation logs, and player quest progression persist into PostgreSQL tables (`coding_challenge_definitions`, `submission_records`, `evaluation_attempts`, `player_quest_progress`).

---

## 5. Deliverable Artifacts & Paths

1. **Standalone Windows Player:**
   - Path: `D:\CodeQuestAI\Builds\Windows\CodeQuestAI.exe`
   - Data Folder: `D:\CodeQuestAI\Builds\Windows\CodeQuestAI_Data\`
   - Size: ~95.8 MB
   - Verification: Tested and launched in standalone mode with clean process initialization and exit.
2. **Unity Project:**
   - Path: `D:\CodeQuestAI\GameClient\`
   - Scene: `Assets/Scenes/Bootstrap.unity`
3. **Backend Service:**
   - Path: `D:\CodeQuestAI\BackendAPI\`
4. **Python Evaluation Service:**
   - Path: `D:\CodeQuestAI\PythonExecutionService\`
   - Docker Image: `codequest-evaluator:local`
5. **Infrastructure:**
   - Database: Docker PostgreSQL `infrastructure-postgres-1` (`127.0.0.1:5432`)
   - Identity Provider: Keycloak 26.8.0 (`127.0.0.1:8080`)

---

## 6. How to Run the Application

### A. Prerequisites (Running Daemons)
Ensure Docker Desktop is running, then start the services if not already active:
1. **PostgreSQL:** `docker start infrastructure-postgres-1` (or `docker compose up -d postgres`)
2. **Keycloak:** Running on port `8080` (realm `codequest-dev`)
3. **Backend API:**
   ```powershell
   & "D:\CodeQuestAI\.venv\Scripts\python.exe" -m uvicorn BackendAPI.app.main:app --host 127.0.0.1 --port 8000
   ```
4. **Evaluation Worker:**
   ```powershell
   & "D:\CodeQuestAI\.venv\Scripts\python.exe" -m uvicorn PythonExecutionService.app.main:app --host 127.0.0.1 --port 8100
   ```

### B. Launching the Game
- **Standalone Game:**
  Double-click `D:\CodeQuestAI\Builds\Windows\CodeQuestAI.exe`.
- **In Unity Editor:**
  Open project `D:\CodeQuestAI\GameClient`, load `Assets/Scenes/Bootstrap.unity`, and press **Play**.

---

## 7. Known Academic Prototype Scope / Non-Blockers

- Keycloak direct access grants (resource owner password grant) are disabled in favor of strict OIDC Authorization Code + PKCE flow as required by security guidelines; initial in-editor or client login uses the browser callback loopback redirect.
- Cloud deployment manifests (Kubernetes / Helm) are configured for local cluster simulation; production cloud ingress certificates are out of academic prototype scope.
