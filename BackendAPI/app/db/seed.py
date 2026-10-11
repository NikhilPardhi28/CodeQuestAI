"""Insert small, stable development content without overwriting existing rows."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from BackendAPI.app.db.models import (
    AchievementDefinition,
    CodingChallengeDefinition,
    CurriculumRegion,
    LearningObjective,
    QuestDefinition,
)
from BackendAPI.app.db.session import SessionLocal


def _insert_if_missing(session: Session, model: type, key: tuple[Any, ...], **values: Any) -> bool:
    if session.get(model, key if len(key) > 1 else key[0]) is not None:
        return False
    session.add(model(**values))
    session.flush()
    return True


def seed_development(session: Session) -> dict[str, int]:
    counts = {"regions": 0, "objectives": 0, "quests": 0, "challenges": 0, "achievements": 0}
    regions = [
        {
            "slug": "variable-vale",
            "version": 1,
            "name": "Variable Vale",
            "summary": "Learn to store values and communicate with the world.",
            "sort_order": 1,
            "unlock_region_slug": None,
            "unlock_region_version": None,
            "is_published": True,
        },
        {
            "slug": "typeworks",
            "version": 1,
            "name": "Typeworks",
            "summary": "Explore Python types, conversion, and operators.",
            "sort_order": 2,
            "unlock_region_slug": "variable-vale",
            "unlock_region_version": 1,
            "is_published": True,
        },
        {
            "slug": "branching-wilds",
            "version": 1,
            "name": "Branching Wilds",
            "summary": "Use conditions to choose a safe route through changing terrain.",
            "sort_order": 3,
            "unlock_region_slug": "typeworks",
            "unlock_region_version": 1,
            "is_published": True,
        },
    ]
    for values in regions:
        counts["regions"] += _insert_if_missing(
            session, CurriculumRegion, (values["slug"], values["version"]), **values
        )

    objectives = [
        (
            "variables-and-assignment",
            "variable-vale",
            1,
            "Variables and assignment",
            "Store and update named values.",
        ),
        (
            "standard-output",
            "variable-vale",
            2,
            "Standard output",
            "Display a computed result with print().",
        ),
        (
            "python-data-types",
            "typeworks",
            1,
            "Python data types",
            "Distinguish strings, numbers, and booleans.",
        ),
        (
            "numeric-operators",
            "typeworks",
            2,
            "Numeric operators",
            "Use arithmetic operators to calculate a result.",
        ),
        (
            "conditional-branches",
            "branching-wilds",
            1,
            "Conditional branches",
            "Choose behavior with if, elif, and else.",
        ),
        (
            "comparison-operators",
            "branching-wilds",
            2,
            "Comparison operators",
            "Compare values to select a route.",
        ),
    ]
    objective_versions: dict[str, int] = {}
    for slug, region_slug, order, title, summary in objectives:
        region = next(item for item in regions if item["slug"] == region_slug)
        values = {
            "slug": slug,
            "version": 1,
            "region_slug": region_slug,
            "region_version": region["version"],
            "title": title,
            "summary": summary,
            "sort_order": order,
            "prerequisites": [],
            "is_published": True,
        }
        counts["objectives"] += _insert_if_missing(session, LearningObjective, (slug, 1), **values)
        objective_versions[slug] = 1

    quest_rows = [
        (
            "light-the-signal",
            "variable-vale",
            "variables-and-assignment",
            "Light the Signal",
            "Set the beacon values and report the route.",
        ),
        (
            "balance-the-foundry",
            "typeworks",
            "numeric-operators",
            "Balance the Foundry",
            "Calculate a stable energy output.",
        ),
        (
            "choose-the-crossing",
            "branching-wilds",
            "conditional-branches",
            "Choose the Crossing",
            "Select a path based on the trail conditions.",
        ),
    ]
    for slug, region_slug, objective_slug, title, summary in quest_rows:
        values = {
            "slug": slug,
            "version": 1,
            "region_slug": region_slug,
            "region_version": 1,
            "objective_slug": objective_slug,
            "objective_version": objective_versions[objective_slug],
            "title": title,
            "summary": summary,
            "public_content": {"kind": "main", "estimatedMinutes": 8},
            "is_published": True,
        }
        counts["quests"] += _insert_if_missing(session, QuestDefinition, (slug, 1), **values)

    challenge_rows = [
        (
            "signal-coordinate",
            "variables-and-assignment",
            "Signal Coordinate",
            "Assign the provided x and y values, then print them as a pair.",
        ),
        (
            "foundry-output",
            "numeric-operators",
            "Foundry Output",
            "Calculate the combined energy from the two supplied values.",
        ),
        (
            "trail-decision",
            "conditional-branches",
            "Trail Decision",
            "Choose the safe trail based on the supplied condition.",
        ),
    ]
    for slug, objective_slug, title, statement in challenge_rows:
        public_content = {
            "examples": [],
            "visibleHints": ["Name the values before combining them."],
        }
        digest_input = json.dumps(
            {"slug": slug, "version": 1, "statement": statement, "public": public_content},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        values = {
            "slug": slug,
            "version": 1,
            "objective_slug": objective_slug,
            "objective_version": objective_versions[objective_slug],
            "title": title,
            "statement": statement,
            "public_content": public_content,
            "content_digest": hashlib.sha256(digest_input).hexdigest(),
            "is_published": True,
        }
        counts["challenges"] += _insert_if_missing(
            session, CodingChallengeDefinition, (slug, 1), **values
        )

    achievements = [
        (
            "first-beacon",
            "First Beacon",
            "Complete the first learning quest.",
            {"event": "quest_completed", "count": 1},
        ),
        (
            "careful-coder",
            "Careful Coder",
            "Complete a challenge with a validated result.",
            {"event": "challenge_validated", "count": 1},
        ),
    ]
    for slug, title, description, criteria in achievements:
        values = {
            "slug": slug,
            "version": 1,
            "title": title,
            "description": description,
            "criteria": criteria,
            "is_published": True,
        }
        counts["achievements"] += _insert_if_missing(
            session, AchievementDefinition, (slug, 1), **values
        )

    session.commit()
    return counts


def main() -> None:
    with SessionLocal() as session:
        counts = seed_development(session)
    print(
        "Inserted development seed rows: "
        + ", ".join(f"{name}={count}" for name, count in counts.items())
    )


if __name__ == "__main__":
    main()
