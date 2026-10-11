import json
import tomllib
from pathlib import Path

import pytest
from BackendAPI.app.schemas import Page, PlayerProfileUpsert
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]


def test_backend_dependencies_are_exactly_pinned() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = project["project"]["dependencies"] + project["dependency-groups"]["dev"]
    assert dependencies
    assert all("==" in dependency for dependency in dependencies)


def test_example_configuration_has_no_live_credentials() -> None:
    lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    assignments = [line for line in lines if line.strip() and not line.lstrip().startswith("#")]
    assert assignments
    assert all(line.startswith("CODEQUEST_") and "=" in line for line in assignments)
    assert not any("sk-" in line or "ghp_" in line for line in assignments)


def test_checked_in_openapi_matches_the_running_contract() -> None:
    from Tools.export_openapi import SPEC_PATHS, render_openapi

    for version, spec_path in SPEC_PATHS.items():
        checked_in = json.loads(spec_path.read_text(encoding="utf-8"))
        generated = json.loads(render_openapi(version))
        assert checked_in == generated
        if version == "v1":
            assert "/api/v1/curriculum/regions" in generated["paths"]
            assert "/api/v1/me" in generated["paths"]
        else:
            assert "/api/v2/me/quests/{quest_slug}/events" in generated["paths"]


def test_profile_and_pagination_schemas_reject_invalid_values() -> None:
    with pytest.raises(ValidationError):
        PlayerProfileUpsert(displayName="   ")
    with pytest.raises(ValidationError):
        PlayerProfileUpsert.model_validate({"displayName": "Ada", "isAdmin": True})
    with pytest.raises(ValidationError):
        Page[int](items=[], limit=101, offset=0, total=0)
