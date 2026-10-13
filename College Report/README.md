# CodeQuest AI — College Major Project Report (LaTeX)

This directory contains the complete, academically rigorous, and professionally formatted LaTeX source code and compiled deliverables for the Major Project report:

> **Project Title:** CodeQuest AI: An Interactive 3D Role-Playing Game for Python Programming Education  
> **Institution:** Adani Institute of Higher Education and Research (AIHER), Department of Artificial Intelligence and Data Science  
> **Author:** Nikhil Pardhi  
> **Output Deliverable:** `CodeQuestAI_Major_Project_Report.pdf` (58 pages)

---

## 1. Directory Structure

```
College Report/
├── CodeQuestAI_Major_Project_Report.pdf  # Compiled final deliverables (58 pages)
├── main.tex                             # Root document orchestrating preliminary pages, chapters, and bibliography
├── references.bib                       # Verified BibTeX bibliography (20 entries with DOIs and preprints)
├── REPORT_METADATA.md                   # Audit of institutional placeholders, guides, and student details
├── REFERENCE_VERIFICATION.md            # Crossref and arXiv verification audit of literature citations
├── README.md                            # Project overview and compilation instructions
├── Dockerfile                           # Reproducible containerized TeX Live 2026 build environment
├── university.png                       # High-resolution institutional emblem for cover and title pages
├── frontmatter/
│   ├── details.tex                      # Global metadata definitions (title, author, department, supervisor)
│   ├── coverpage.tex                    # Outer hard-cover presentation page
│   ├── titlepage.tex                    # Inner formal title page
│   ├── approval.tex                     # Institutional project approval sheet
│   ├── declaration.tex                  # Candidate academic honesty declaration
│   ├── acknowledgment.tex              # Institutional acknowledgments
│   ├── abstract.tex                    # 350-word academic abstract and keywords
│   └── abbreviations.tex                # Formatted list of technical abbreviations
├── chapters/
│   ├── chapter1.tex                     # Chapter 1: Introduction (Background, Aim, Contributions, Organization)
│   ├── chapter2.tex                     # Chapter 2: Literature Survey (PRISMA methodology, Gap Analysis, 10-Study Table)
│   ├── chapter3.tex                     # Chapter 3: Methodology (Tiered Architecture, Curriculum, Sandbox Design)
│   ├── chapter4.tex                     # Chapter 4: System Analysis and Design (FRs, NFRs, UML Use Cases, ERD)
│   ├── chapter5.tex                     # Chapter 5: Implementation Details (Unity 3D, TrueType Font Fix, FastAPI, Docker)
│   ├── chapter6.tex                     # Chapter 6: Results and Testing (Automated Test Matrix, Standalone Benchmarks)
│   ├── chapter7.tex                     # Chapter 7: Conclusion and Future Scope (Summary, Objectives Evaluation, Roadmap)
│   └── appendices.tex                   # Appendices (Deployment Guide, API Specs, Test Logs)
└── figures/
    ├── prisma.png                       # PRISMA 2020 systematic literature selection flowchart
    ├── python_editor_ui.png             # In-game modal Python editor HUD screenshot
    ├── dialogue_interaction.png         # Proximity NPC dialogue interaction screenshot
    └── learning_outcomes_graph.png      # Formative quiz and challenge pass rate analytics plot
```

---

## 2. Compilation Instructions

### Option A: Local Docker (Recommended & Reproducible)

A containerized TeX Live 2026 build environment is pre-configured to guarantee zero host dependencies.

1. **Build the compiler container (if not already cached):**
   ```powershell
   docker build -t codequest-latex:local .
   ```

2. **Compile the document:**
   ```powershell
   docker run --rm -v "${PWD}:/work" -w /work codequest-latex:local sh -c "pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex"
   ```

3. **Copy to final deliverable:**
   ```powershell
   cp main.pdf CodeQuestAI_Major_Project_Report.pdf
   ```

### Option B: Overleaf (Cloud LaTeX)

1. Compress the contents of `D:\CodeQuestAI\College Report` into a `.zip` archive (excluding the generated `build/` files or `.log` files).
2. Log into [Overleaf](https://www.overleaf.com), create a new blank project, and upload the zip file.
3. In Overleaf project settings, ensure:
   - **Compiler:** `pdfLaTeX`
   - **TeX Live version:** `2024` or `2025`
   - **Main document:** `main.tex`
4. Click **Recompile**.

---

## 3. Customizing Placeholders Before Final Submission

Edit [frontmatter/details.tex](file:///d:/CodeQuestAI/College%20Report/frontmatter/details.tex) to fill in remaining administrative details:
- `\enrollmentno{...}`: Replace `[ENROLLMENT_NO_PLACEHOLDER]` with your university roll number.
- `\guide{...}`: Replace `[FACULTY_GUIDE_NAME_PLACEHOLDER]` with your internal faculty guide.
- `\hod{...}`: Replace `[HOD_NAME_PLACEHOLDER]` with the Head of Department.
- `\degreedate{...}`: Update the month and year of examination.
