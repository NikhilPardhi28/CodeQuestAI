# CodeQuest AI

CodeQuest AI is a Python-learning 3D RPG project with an initial Unity runtime foundation and FastAPI catalog/profile APIs backed by an initial database migration. The current client is a greybox only; authored world content, dashboards, teacher/admin services, and isolated Python execution remain unimplemented.

## Start here

- Read the [architecture and product baseline](Documentation/README.md).
- Read [contributor setup and engineering conventions](CONTRIBUTING.md).
- Review accepted decisions in [the ADR index](Documentation/adr/README.md).

## Local Python tooling

Install Python 3.11.9 and uv 0.13.0, then from PowerShell at the repository root:

```powershell
py -m pip install --user uv==0.13.0
uv sync --locked --all-groups
Copy-Item .env.example .env
uv run python Tools/validate_docs.py
uv run python Tools/validate_config.py
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest
```

The environment file is an example only. Start the backend separately using [BackendAPI setup](BackendAPI/README.md); start the Unity client using [GameClient setup](GameClient/README.md).

## Unity

Use Unity Editor **6000.3.19f1** on Windows 10/11 x64. Install that exact version through Unity Hub; do not auto-upgrade. The [GameClient setup guide](GameClient/README.md) documents the pinned packages, first-open editor setup, controls, API configuration, and test instructions. Unity Editor package resolution, scene/settings generation, compilation, and Test Runner checks remain to be completed in the editor.

## Continuous integration

The GitHub Actions workflow in `.github/workflows/baseline.yml` checks the Python lock, documentation links, config examples, Ruff lint/formatting, and available backend tests. It requires no paid services. The workflow has been authored locally; it has not been run by GitHub Actions.
