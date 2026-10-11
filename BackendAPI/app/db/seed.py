"""Insert small, stable development content without overwriting existing rows."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from BackendAPI.app.db.models import (
    AchievementDefinition,
    ChallengeHiddenTestCase,
    ChallengeHint,
    CodingChallengeDefinition,
    CurriculumRegion,
    LearningObjective,
    QuestDefinition,
    QuestEventTarget,
    QuestObjectivePrerequisite,
    QuestObjectiveRule,
    QuestRewardRule,
)
from BackendAPI.app.db.session import SessionLocal


def _insert_if_missing(session: Session, model: type, key: tuple[Any, ...], **values: Any) -> bool:
    if session.get(model, key if len(key) > 1 else key[0]) is not None:
        return False
    session.add(model(**values))
    session.flush()
    return True


def seed_development(session: Session) -> dict[str, int]:
    counts = {
        "regions": 0,
        "objectives": 0,
        "quests": 0,
        "challenges": 0,
        "achievements": 0,
        "questRules": 0,
    }
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

    # The first playable region is an additive, versioned content pack. Existing
    # curriculum rows remain untouched so older quests and clients keep working.
    valley_region = {
        "slug": "variable-valley",
        "version": 1,
        "name": "Variable Valley",
        "summary": "Learn to store values, accept inputs, and return clear outputs.",
        "sort_order": 0,
        "unlock_region_slug": None,
        "unlock_region_version": None,
        "is_published": True,
    }
    counts["regions"] += _insert_if_missing(
        session,
        CurriculumRegion,
        (valley_region["slug"], valley_region["version"]),
        **valley_region,
    )
    valley_objective = {
        "slug": "valley-variables-and-io",
        "version": 1,
        "region_slug": "variable-valley",
        "region_version": 1,
        "title": "Variables and input/output",
        "summary": "Store function inputs in variables and return readable results.",
        "sort_order": 1,
        "prerequisites": [],
        "is_published": True,
    }
    counts["objectives"] += _insert_if_missing(
        session,
        LearningObjective,
        (valley_objective["slug"], valley_objective["version"]),
        **valley_objective,
    )
    valley_quest = {
        "slug": "variables-in-the-valley",
        "version": 1,
        "region_slug": "variable-valley",
        "region_version": 1,
        "objective_slug": "valley-variables-and-io",
        "objective_version": 1,
        "title": "A Message for the Valley",
        "summary": (
            "Help Mira restore the valley beacon by solving five variable and input/output "
            "challenges."
        ),
        "public_content": {"kind": "main", "estimatedMinutes": 20},
        "is_published": True,
    }
    counts["quests"] += _insert_if_missing(
        session, QuestDefinition, (valley_quest["slug"], 1), **valley_quest
    )

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
        hidden = {
            "signal-coordinate": [
                {"input": [17, 42], "expected": [17, 42]},
                {"input": [-8, 5], "expected": [-8, 5]},
            ],
            "foundry-output": [
                {"input": [7, 12], "expected": 19},
                {"input": [-4, 9], "expected": 5},
            ],
            "trail-decision": [
                {"input": [True], "expected": "tunnel"},
                {"input": [False], "expected": "ridge"},
            ],
        }[slug]
        hints = {
            "signal-coordinate": [
                "A function can return more than one value by returning a tuple.",
                "Return (x, y) in the same order as the parameters.",
            ],
            "foundry-output": [
                "Use the + operator to combine two numeric values.",
                "Return first + second; do not print it.",
            ],
            "trail-decision": [
                "Use an if/else branch to choose one of two strings.",
                "Return 'tunnel' for True and 'ridge' otherwise.",
            ],
        }[slug]
        visible_tests = {
            "signal-coordinate": [
                {"input": [2, 3], "expected": [2, 3]},
                {"input": [0, -1], "expected": [0, -1]},
            ],
            "foundry-output": [
                {"input": [2, 3], "expected": 5},
                {"input": [0, -1], "expected": -1},
            ],
            "trail-decision": [
                {"input": [False], "expected": "ridge"},
                {"input": [True], "expected": "tunnel"},
            ],
        }[slug]
        public_content = {
            "mode": "function",
            "functionName": {
                "signal-coordinate": "signal_coordinate",
                "foundry-output": "combined_energy",
                "trail-decision": "choose_trail",
            }[slug],
            "functionSignature": {
                "signal-coordinate": "signal_coordinate(x, y)",
                "foundry-output": "combined_energy(first, second)",
                "trail-decision": "choose_trail(is_raining)",
            }[slug],
            "starterCode": {
                "signal-coordinate": (
                    "def signal_coordinate(x, y):\n"
                    "    # Return both coordinates as a tuple.\n"
                    "    pass\n"
                ),
                "foundry-output": (
                    "def combined_energy(first, second):\n"
                    "    # Return the combined energy.\n"
                    "    pass\n"
                ),
                "trail-decision": (
                    "def choose_trail(is_raining):\n"
                    "    # Return 'ridge' when dry, otherwise 'tunnel'.\n"
                    "    pass\n"
                ),
            }[slug],
            "examples": {
                "signal-coordinate": ["signal_coordinate(2, 3) returns (2, 3)"],
                "foundry-output": ["combined_energy(2, 3) returns 5"],
                "trail-decision": ["choose_trail(False) returns 'ridge'"],
            }[slug],
            "visibleTests": visible_tests,
            "expectedOutputFormat": "Return the value described by the function signature.",
        }
        digest_input = json.dumps(
            {
                "slug": slug,
                "version": 1,
                "statement": statement,
                "public": public_content,
                "hidden": hidden,
                "hints": hints,
            },
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
            "max_source_bytes": 8192,
            "is_published": True,
        }
        counts["challenges"] += _insert_if_missing(
            session, CodingChallengeDefinition, (slug, 1), **values
        )
        for position, test_definition in enumerate(hidden):
            if (
                session.query(ChallengeHiddenTestCase)
                .filter_by(challenge_slug=slug, challenge_version=1, position=position)
                .first()
                is None
            ):
                session.add(
                    ChallengeHiddenTestCase(
                        challenge_slug=slug,
                        challenge_version=1,
                        position=position,
                        test_definition=test_definition,
                    )
                )
        for level, content in enumerate(hints, start=1):
            if (
                session.query(ChallengeHint)
                .filter_by(challenge_slug=slug, challenge_version=1, level=level)
                .first()
                is None
            ):
                session.add(
                    ChallengeHint(
                        challenge_slug=slug,
                        challenge_version=1,
                        level=level,
                        content=content,
                    )
                )

        versioned_digest = hashlib.sha256(
            json.dumps(
                {
                    "slug": slug,
                    "version": 2,
                    "statement": statement,
                    "public": public_content,
                    "hidden": hidden,
                    "hints": hints,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        version2 = {**values, "version": 2, "content_digest": versioned_digest}
        counts["challenges"] += _insert_if_missing(
            session, CodingChallengeDefinition, (slug, 2), **version2
        )
        for position, test_definition in enumerate(hidden):
            if (
                session.query(ChallengeHiddenTestCase)
                .filter_by(challenge_slug=slug, challenge_version=2, position=position)
                .first()
                is None
            ):
                session.add(
                    ChallengeHiddenTestCase(
                        challenge_slug=slug,
                        challenge_version=2,
                        position=position,
                        test_definition=test_definition,
                    )
                )
        for level, content in enumerate(hints, start=1):
            if (
                session.query(ChallengeHint)
                .filter_by(challenge_slug=slug, challenge_version=2, level=level)
                .first()
                is None
            ):
                session.add(
                    ChallengeHint(
                        challenge_slug=slug,
                        challenge_version=2,
                        level=level,
                        content=content,
                    )
                )

    valley_challenges = [
        {
            "slug": "valley-name-tag",
            "title": "A Name for the Beacon",
            "statement": "Store the supplied name in a variable and return a friendly greeting.",
            "function": "make_name_tag",
            "signature": "make_name_tag(name)",
            "starter": (
                "def make_name_tag(name):\n    # Store a greeting, then return it.\n    pass\n"
            ),
            "examples": ["make_name_tag('Ada') returns 'Hello, Ada!'"],
            "visible": [
                {"input": ["Ada"], "expected": "Hello, Ada!"},
                {"input": ["Kai"], "expected": "Hello, Kai!"},
            ],
            "hidden": [
                {"input": ["Mira"], "expected": "Hello, Mira!"},
                {"input": ["River"], "expected": "Hello, River!"},
            ],
            "hints": [
                "Give the input a descriptive variable name before building the result.",
                "Join the greeting text, the name variable, and the exclamation mark.",
                "Assign the joined string to a variable, then return that variable.",
            ],
        },
        {
            "slug": "valley-sunplot-area",
            "title": "The Sunplot",
            "statement": (
                "Use the width and height inputs to calculate and return the rectangular garden "
                "area."
            ),
            "function": "calculate_plot_area",
            "signature": "calculate_plot_area(width, height)",
            "starter": (
                "def calculate_plot_area(width, height):\n"
                "    # Store the calculated area in a variable.\n"
                "    pass\n"
            ),
            "examples": ["calculate_plot_area(4, 3) returns 12"],
            "visible": [
                {"input": [4, 3], "expected": 12},
                {"input": [5, 2], "expected": 10},
            ],
            "hidden": [
                {"input": [7, 6], "expected": 42},
                {"input": [0, 9], "expected": 0},
            ],
            "hints": [
                "The function receives two values that describe the rectangle.",
                "Area is found by multiplying width by height.",
                "Save width * height in an area variable and return it.",
            ],
        },
        {
            "slug": "valley-signal-label",
            "title": "Label the Signal",
            "statement": "Turn the numeric signal level into the exact text shown by the example.",
            "function": "format_signal",
            "signature": "format_signal(level)",
            "starter": (
                "def format_signal(level):\n"
                "    # Return a label such as 'Signal level: 3'.\n"
                "    pass\n"
            ),
            "examples": ["format_signal(3) returns 'Signal level: 3'"],
            "visible": [
                {"input": [3], "expected": "Signal level: 3"},
                {"input": [0], "expected": "Signal level: 0"},
            ],
            "hidden": [
                {"input": [12], "expected": "Signal level: 12"},
                {"input": [-1], "expected": "Signal level: -1"},
            ],
            "hints": [
                "The input is a number, while the result must be text.",
                "Convert the level to text with str(level) before joining it.",
                "Store 'Signal level: ' + str(level) in a variable and return it.",
            ],
        },
        {
            "slug": "valley-seed-count",
            "title": "Count the Seeds",
            "statement": (
                "Calculate how many seeds are planted when every row receives the same number."
            ),
            "function": "seed_total",
            "signature": "seed_total(rows, seeds_per_row)",
            "starter": (
                "def seed_total(rows, seeds_per_row):\n"
                "    # Store the total seed count in a variable.\n"
                "    pass\n"
            ),
            "examples": ["seed_total(3, 8) returns 24"],
            "visible": [
                {"input": [3, 8], "expected": 24},
                {"input": [2, 5], "expected": 10},
            ],
            "hidden": [
                {"input": [6, 7], "expected": 42},
                {"input": [1, 0], "expected": 0},
            ],
            "hints": [
                "Each row has an equal number of seeds.",
                "Repeated equal groups are counted with multiplication.",
                "Assign rows * seeds_per_row to a total variable and return it.",
            ],
        },
        {
            "slug": "valley-beacon-message",
            "title": "Restore the Beacon Message",
            "statement": "Combine the learner and region inputs into the exact beacon message.",
            "function": "compose_beacon_message",
            "signature": "compose_beacon_message(name, region)",
            "starter": (
                "def compose_beacon_message(name, region):\n"
                "    # Build and return the beacon message.\n"
                "    pass\n"
            ),
            "examples": ["compose_beacon_message('Ada', 'Valley') returns 'Ada reached Valley!'"],
            "visible": [
                {"input": ["Ada", "Valley"], "expected": "Ada reached Valley!"},
                {"input": ["Kai", "Orchard"], "expected": "Kai reached Orchard!"},
            ],
            "hidden": [
                {"input": ["Mira", "Valley"], "expected": "Mira reached Valley!"},
                {"input": ["Fox", "Grove"], "expected": "Fox reached Grove!"},
            ],
            "hints": [
                "Both inputs are strings that belong in one output sentence.",
                "Keep the spaces around the word reached and at the end of the sentence.",
                "Join name, ' reached ', region, and '!' in that order.",
            ],
        },
    ]
    previous_challenge_slug = ""
    for sequence, challenge in enumerate(valley_challenges, start=1):
        slug = challenge["slug"]
        public_content = {
            "mode": "function",
            "functionName": challenge["function"],
            "functionSignature": challenge["signature"],
            "starterCode": challenge["starter"],
            "examples": challenge["examples"],
            "visibleTests": challenge["visible"],
            "visibleHints": challenge["hints"],
            "questSlug": "variables-in-the-valley",
            "prerequisiteChallengeSlug": previous_challenge_slug,
            "sequence": sequence,
            "expectedOutputFormat": "Return the exact value described by the function signature.",
        }
        digest_input = json.dumps(
            {
                "slug": slug,
                "version": 1,
                "statement": challenge["statement"],
                "public": public_content,
                "hidden": challenge["hidden"],
                "hints": challenge["hints"],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        counts["challenges"] += _insert_if_missing(
            session,
            CodingChallengeDefinition,
            (slug, 1),
            slug=slug,
            version=1,
            objective_slug="valley-variables-and-io",
            objective_version=1,
            title=challenge["title"],
            statement=challenge["statement"],
            public_content=public_content,
            content_digest=hashlib.sha256(digest_input).hexdigest(),
            max_source_bytes=8192,
            is_published=True,
        )
        for position, test_definition in enumerate(challenge["hidden"]):
            if (
                session.query(ChallengeHiddenTestCase)
                .filter_by(challenge_slug=slug, challenge_version=1, position=position)
                .first()
                is None
            ):
                session.add(
                    ChallengeHiddenTestCase(
                        challenge_slug=slug,
                        challenge_version=1,
                        position=position,
                        test_definition=test_definition,
                    )
                )
        for level, content in enumerate(challenge["hints"], start=1):
            if (
                session.query(ChallengeHint)
                .filter_by(challenge_slug=slug, challenge_version=1, level=level)
                .first()
                is None
            ):
                session.add(
                    ChallengeHint(
                        challenge_slug=slug,
                        challenge_version=1,
                        level=level,
                        content=content,
                    )
                )
        previous_challenge_slug = slug

    valley_targets = [("interact", "valley-mentor", 1)] + [
        ("challenge_passed", challenge["slug"], 1) for challenge in valley_challenges
    ]
    for event_type, target_id, target_version in valley_targets:
        counts["questRules"] += _insert_if_missing(
            session,
            QuestEventTarget,
            (event_type, target_id, target_version),
            event_type=event_type,
            target_id=target_id,
            target_version=target_version,
            is_enabled=True,
        )
    valley_objectives = [
        ("accept-valley-quest", "interact", "valley-mentor"),
        *[
            (f"complete-{challenge['slug']}", "challenge_passed", challenge["slug"])
            for challenge in valley_challenges
        ],
    ]
    for objective_id, event_type, target_id in valley_objectives:
        counts["questRules"] += _insert_if_missing(
            session,
            QuestObjectiveRule,
            ("variables-in-the-valley", 1, objective_id),
            quest_slug="variables-in-the-valley",
            quest_version=1,
            objective_id=objective_id,
            event_type=event_type,
            target_id=target_id,
            target_version=1,
            required_count=1,
        )
    previous_objective = "accept-valley-quest"
    for challenge in valley_challenges:
        objective_id = f"complete-{challenge['slug']}"
        counts["questRules"] += _insert_if_missing(
            session,
            QuestObjectivePrerequisite,
            ("variables-in-the-valley", 1, objective_id, previous_objective),
            quest_slug="variables-in-the-valley",
            quest_version=1,
            objective_id=objective_id,
            prerequisite_objective_id=previous_objective,
        )
        previous_objective = objective_id
    counts["questRules"] += _insert_if_missing(
        session,
        QuestRewardRule,
        ("variables-in-the-valley", 1, "valley-beacon-xp"),
        quest_slug="variables-in-the-valley",
        quest_version=1,
        reward_id="valley-beacon-xp",
        reward_type="experience",
        experience_points=50,
    )

    targets = [
        ("interact", "relay-switch", 1),
        ("checkpoint", "signal-platform", 1),
        ("challenge_passed", "signal-coordinate", 1),
        ("prerequisite_completed", "light-the-signal", 1),
        ("challenge_passed", "foundry-output", 1),
        ("interact", "crossing-console", 1),
        ("checkpoint", "trail-crossing", 1),
    ]
    for event_type, target_id, target_version in targets:
        counts["questRules"] += _insert_if_missing(
            session,
            QuestEventTarget,
            (event_type, target_id, target_version),
            event_type=event_type,
            target_id=target_id,
            target_version=target_version,
            is_enabled=True,
        )

    rules = [
        ("light-the-signal", "activate-relay", "interact", "relay-switch"),
        ("light-the-signal", "reach-platform", "checkpoint", "signal-platform"),
        ("light-the-signal", "pass-signal-challenge", "challenge_passed", "signal-coordinate"),
        (
            "balance-the-foundry",
            "complete-signal-prerequisite",
            "prerequisite_completed",
            "light-the-signal",
        ),
        ("balance-the-foundry", "pass-foundry-challenge", "challenge_passed", "foundry-output"),
        ("choose-the-crossing", "inspect-crossing", "interact", "crossing-console"),
        ("choose-the-crossing", "reach-crossing", "checkpoint", "trail-crossing"),
    ]
    for quest_slug, objective_id, event_type, target_id in rules:
        counts["questRules"] += _insert_if_missing(
            session,
            QuestObjectiveRule,
            (quest_slug, 1, objective_id),
            quest_slug=quest_slug,
            quest_version=1,
            objective_id=objective_id,
            event_type=event_type,
            target_id=target_id,
            target_version=1,
            required_count=1,
        )
    prerequisites = [
        ("light-the-signal", "reach-platform", "activate-relay"),
        ("light-the-signal", "pass-signal-challenge", "reach-platform"),
        ("balance-the-foundry", "pass-foundry-challenge", "complete-signal-prerequisite"),
        ("choose-the-crossing", "reach-crossing", "inspect-crossing"),
    ]
    for quest_slug, objective_id, required_id in prerequisites:
        counts["questRules"] += _insert_if_missing(
            session,
            QuestObjectivePrerequisite,
            (quest_slug, 1, objective_id, required_id),
            quest_slug=quest_slug,
            quest_version=1,
            objective_id=objective_id,
            prerequisite_objective_id=required_id,
        )
    counts["questRules"] += _insert_if_missing(
        session,
        QuestRewardRule,
        ("light-the-signal", 1, "signal-experience"),
        quest_slug="light-the-signal",
        quest_version=1,
        reward_id="signal-experience",
        reward_type="experience",
        experience_points=25,
    )

    version_one_quests = session.query(QuestDefinition).filter_by(version=1).all()
    for quest in version_one_quests:
        values = {
            "slug": quest.slug,
            "version": 2,
            "region_slug": quest.region_slug,
            "region_version": quest.region_version,
            "objective_slug": quest.objective_slug,
            "objective_version": quest.objective_version,
            "title": quest.title,
            "summary": quest.summary,
            "public_content": quest.public_content,
            "is_published": quest.is_published,
        }
        counts["quests"] += _insert_if_missing(session, QuestDefinition, (quest.slug, 2), **values)
    for quest in version_one_quests:
        old_rules = (
            session.query(QuestObjectiveRule)
            .filter_by(quest_slug=quest.slug, quest_version=1)
            .all()
        )
        for old_rule in old_rules:
            target_version = (
                2
                if old_rule.event_type in {"challenge_passed", "prerequisite_completed"}
                else old_rule.target_version
            )
            target_key = (old_rule.event_type, old_rule.target_id, target_version)
            counts["questRules"] += _insert_if_missing(
                session,
                QuestEventTarget,
                target_key,
                event_type=old_rule.event_type,
                target_id=old_rule.target_id,
                target_version=target_version,
                is_enabled=True,
            )
            counts["questRules"] += _insert_if_missing(
                session,
                QuestObjectiveRule,
                (quest.slug, 2, old_rule.objective_id),
                quest_slug=quest.slug,
                quest_version=2,
                objective_id=old_rule.objective_id,
                event_type=old_rule.event_type,
                target_id=old_rule.target_id,
                target_version=target_version,
                required_count=old_rule.required_count,
            )
        old_edges = (
            session.query(QuestObjectivePrerequisite)
            .filter_by(quest_slug=quest.slug, quest_version=1)
            .all()
        )
        for edge in old_edges:
            counts["questRules"] += _insert_if_missing(
                session,
                QuestObjectivePrerequisite,
                (quest.slug, 2, edge.objective_id, edge.prerequisite_objective_id),
                quest_slug=quest.slug,
                quest_version=2,
                objective_id=edge.objective_id,
                prerequisite_objective_id=edge.prerequisite_objective_id,
            )
        old_rewards = (
            session.query(QuestRewardRule).filter_by(quest_slug=quest.slug, quest_version=1).all()
        )
        for reward in old_rewards:
            counts["questRules"] += _insert_if_missing(
                session,
                QuestRewardRule,
                (quest.slug, 2, reward.reward_id),
                quest_slug=quest.slug,
                quest_version=2,
                reward_id=reward.reward_id,
                reward_type=reward.reward_type,
                experience_points=reward.experience_points,
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
