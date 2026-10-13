# CodeQuest AI — College Major Project Report Metadata

This document records the official project, institutional, and student details used across the LaTeX report, as well as placeholders that require student/departmental confirmation.

---

## 1. Project Identity
- **Project Title:** AN AGENTIC AI-POWERED 3D OPEN-WORLD RPG FOR ADAPTIVE PYTHON PROGRAMMING EDUCATION
- **Short Name:** CodeQuest AI (previously referred to as *PYTHONIA* in earlier conceptual proposals)
- **Domain:** Computer Science and Engineering, Educational Technology, Game-Based Learning, Agentic AI, Automated Code Evaluation
- **Academic Degree:** Bachelor of Technology (B.Tech)
- **Semester:** Semester VII (Major Project-I) / VIII
- **Academic Year:** 2025–2026
- **Submission Date:** October, 2026

---

## 2. Institutional Details (from AIHER Approved Sample Template)
- **Institution:** Adani Institute of Higher Education and Research (DU)
- **Faculty:** Faculty of Engineering and Technology (FEAT)
- **Department:** Department of Artificial Intelligence and Data Science
- **Department (Uppercase):** DEPARTMENT OF ARTIFICIAL INTELLIGENCE AND DATA SCIENCE
- **Location:** Sawangi (Meghe), Wardha, Maharashtra – 442107

---

## 3. Student & Faculty Details
- **Student Name:** Nikhil Pardhi *(Confirmed from Git commit history / author identity)*
- **Student Enrollment Number:** C2023FE00027 *(Confirmed student enrollment number)*
- **Supervisor / Project Guide:** Dr. Shital Hajare *(Internal guide)*
- **Head of Department (HOD) / Dean Academics:** Dr. Utkarsha S Pacharaney *(from sample)*
- **Dean, Faculty of Engineering and Technology (FEAT):** Prof. (Dr.) K.T.V. Reddy *(from sample)*
- **Project Coordinator:** Dr. Subodh Daronde *(from sample)*

---

## 4. Implementation vs. Conceptual Scope Mapping

| Feature Area | Implemented & Verified in CodeQuest AI | Conceptual / Planned Scope (from PYTHONIA Proposal) |
| :--- | :--- | :--- |
| **Client Engine** | Unity 6 (`6000.3.19f1`) with URP 3D world, third-person controller, camera rig, interactive beacons & NPCs | 2D Godot/Pygame prototype |
| **Code Editor** | In-game multiline Python editor with syntax font, Run/Submit workflow, real-time output panel | In-browser Pyodide / monaco editor |
| **Backend API** | FastAPI asynchronous REST service (`http://127.0.0.1:8000`) with health checks, curriculum endpoints | FastAPI / Supabase cloud backend |
| **Database** | PostgreSQL 17.5 via Docker with Alembic migrations, player profiles, versioned quests & submissions | Supabase / PostgreSQL |
| **Authentication** | OIDC / Keycloak (`http://127.0.0.1:8080/realms/codequest-dev`) with PKCE desktop token provider | NextAuth / Keycloak |
| **Code Execution** | Isolated Docker Python execution service (`codequest-evaluator:local`) on `http://127.0.0.1:8100/internal/evaluate` | Cloud sandbox / Pyodide |
| **Curriculum** | Variable Valley Chapter 1 (`valley-name-tag`) with verified automated test cases | 7-zone multi-topic Python curriculum (variables to async/await) |
| **AI Tutoring** | Rule-based pedagogical hint provider (`ITutorHintProvider`) with error categorization | Multi-agent LangGraph orchestrator (Game Master, Hint, NPC, Code Review agents) |
