# Report Revision Log — CodeQuest AI Major Project Report

**Project Root:** `D:\CodeQuestAI\College Report`  
**Compiled Deliverable:** `D:\CodeQuestAI\College Report\CodeQuestAI_Major_Project_Report.pdf` (56 pages, 1,805,482 bytes)  
**Date of Revision:** 13 October 2026

---

## 1. Summary of Modifications

### 1.1 Project Title Correction
- **Approved Exact Title:**  
  `AN AGENTIC AI-POWERED 3D OPEN-WORLD RPG FOR ADAPTIVE PYTHON PROGRAMMING EDUCATION`
- **Updated Locations:**
  - `frontmatter/details.tex` (`\ProjectTitle`)
  - `frontmatter/coverpage.tex` (Outer cover page)
  - `frontmatter/titlepage.tex` (Formal institutional title page)
  - `frontmatter/approval.tex` (Institutional approval certificate)
  - `REPORT_METADATA.md` (Metadata audit document)
  - `chapters/chapter1.tex` (Introduction text)

### 1.2 Student Enrollment Number
- **Enrollment Number:** `C2023FE00027`
- **Updated Locations:**
  - `frontmatter/details.tex` (`\EnrollmentNo`)
  - `frontmatter/titlepage.tex`
  - `frontmatter/declaration.tex`
  - `REPORT_METADATA.md`

### 1.3 Concise Academic Abstract
- **Word Count:** Exactly 199 words (body text excluding keywords).
- **Content:** Succinctly articulates the computer science education retention problem, proposed 3D RPG architecture, implemented technology stack (Unity 6 URP, FastAPI, PostgreSQL, Docker cgroup sandbox, Keycloak OIDC/PKCE), challenge evaluation loop, and empirical validation outcomes (sub-second evaluation latency, host isolation, cross-session persistence in Variable Valley).
- **Location:** `frontmatter/abstract.tex` (Roman numeral page `i`).

### 1.4 Reformatting of Ten-Paper Literature Review Table
- **Format:** Converted to an optimized `longtable` spanning pages 24 to 27 (3 pages) with compact font (`\footnotesize`), cell padding (`\tabcolsep=4pt`), column wrapping, and repeated table headers on page breaks.
- **Content Integrity:** Retained all 10 surveyed papers with full citation metadata, sample sizes, empirical findings, and identified research gaps.
- **Table 2.1 (Gap Analysis):** Migrated to `tabularx` with `X` columns to prevent margin overflow.

### 1.5 Integration of Demo Screenshots & Architecture Diagrams
The 5 uploaded screenshots were copied to `figures/` with academic filenames and referenced in the narrative:
1. `figures/variable_valley_gameplay.png`: Inserted into Chapter 5 (`\ref{fig:variable_valley_gameplay}`) showing the 3D game world with player avatar, environmental beacons, and guide NPCs (Signal Keeper and Mira).
2. `figures/learning_region_catalog.png`: Inserted into Chapter 3 (`\ref{fig:learning_region_catalog}`) showing the Variable Valley curriculum catalog, learning goals, and ordered challenge list.
3. `figures/python_challenge_editor.png`: Inserted into Chapter 5 (`\ref{fig:ui_editor_annotated}`) showing the in-game modal Python editor, monospace typography, Run/Submit button, and output terminal.
4. `figures/main_menu_and_npcs.png`: Inserted into Chapter 6 (`\ref{fig:standalone_menu}`) illustrating the standalone main menu overlay with high-contrast text buttons.
5. `figures/dialogue_interaction.png`: Preserved in Chapter 6 (`\ref{fig:dialogue_interaction}`) illustrating NPC dialogue branching choices.
6. `figures/prisma.png`: PRISMA selection flowchart in Chapter 2.
7. `figures/learning_outcomes_graph.png`: Formative quiz and challenge pass rate analytics plot in Chapter 6.

### 1.6 Table Alignment and Overflow Audits
All tables throughout the report were audited and converted to responsive width formats:
- `Table 2.1` (Gap Analysis, Ch. 2): Converted from rigid `tabular` to `tabularx{\textwidth}`.
- `Table 2.2` (Top 10 Literature Survey, Ch. 2): Formatted with `longtable` across pages 24–27.
- `Figure 4.3` (Relational ERD, Ch. 4): Converted to `tabularx` with explicit column widths.
- `Table 5.1` (Tech Stack, Ch. 5): Converted from overflow-prone `tabular` to `tabularx{\textwidth}`.
- `Table 6.1` (Test Summary, Ch. 6): Converted to `tabularx{\textwidth}`.
- `Table 6.2` (Latency Benchmarks, Ch. 6): Converted to `tabularx{\textwidth}`.
- `Table 7.1` (Objective Evaluation, Ch. 7): Styled with `tabularx{\textwidth}`.
- `Table B.1` (REST Endpoints, Appendix B): Styled with `tabularx{\textwidth}`.
- `Abbreviations Table`: Converted to `tabularx{\textwidth}`.

### 1.7 Table of Contents Alignment Fix
- **Root Cause Diagnosed:** `\cfttoctitlefont` in `main.tex` contained unbalanced `\hfill` calls (`\renewcommand{\cfttoctitlefont}{\hfill\huge\bfseries}` and `\renewcommand{\cftaftertoctitle}{\hfill}`) which shifted the title and affected default ToC margins.
- **Correction Applied:** Removed asymmetric `\hfill` padding, ensuring natural alignment matching the standard chapter titles across the document.

### 1.8 Reduced Abbreviations List
- **Pruned:** Removed 25 redundant, rarely used, or generic entries (e.g., CI/CD, CRUD, CS, DTO, GDI, GUI, LNCS, PaaS, PEP, SRL, SSL, TLS, UUID, VM, VR, XP).
- **Retained (24 Essential Terms):** AI, API, AST, DBMS, HUD, HTTP, IDE, JSON, JWT, KT, LLM, LMS, NPC, OIDC, ORM, PKCE, PRISMA, RAG, REST, RPG, SQL, UI, UML, URP.
- **Location:** `frontmatter/abbreviations.tex`.

---

## 2. Compilation and Build Status
- **LaTeX Compiler:** TeX Live 2026 containerized engine (`codequest-latex:local`).
- **Passes Executed:** `pdflatex` $\rightarrow$ `bibtex` $\rightarrow$ `pdflatex` $\rightarrow$ `pdflatex`.
- **Exit Code:** Clean exit code `0`.
- **Undefined References:** Zero (`main.log` verified with 0 undefined citations or references).
- **Final PDF Deliverable:** `CodeQuestAI_Major_Project_Report.pdf` (56 pages, 1.80 MB).
