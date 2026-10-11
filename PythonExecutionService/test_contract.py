"""Safe protocol checks only; these tests never execute learner source."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docker_runner import validate_job  # noqa: E402


@pytest.fixture
def job() -> dict[str, object]:
    return {
        "submissionId": "0fedb4c5-58e0-49b7-8c91-3de94099db6b",
        "challengeSlug": "signal-coordinate",
        "challengeVersion": 1,
        "evaluatorVersion": "python-v1",
        "source": "def signal_coordinate(x, y): return (x, y)",
        "sourceDigest": "a" * 64,
        "definition": {
            "mode": "function",
            "functionName": "signal_coordinate",
            "visibleTests": [{"input": [1, 2], "expected": [1, 2]}],
            "hiddenTests": [{"input": [3, 4], "expected": [3, 4]}],
            "timeLimitMs": 1000,
            "outputLimitBytes": 65536,
        },
    }


def test_bounded_job_shape_is_accepted_without_execution(job):
    assert validate_job(job)["challengeVersion"] == 1


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(extra="must fail"),
        lambda value: value.update(source="x" * (32 * 1024 + 1)),
        lambda value: value["definition"].update(mode="unknown"),
        lambda value: value["definition"].update(timeLimitMs=5001),
    ],
)
def test_invalid_worker_requests_are_rejected_before_container_launch(job, mutate):
    invalid = copy.deepcopy(job)
    mutate(invalid)
    with pytest.raises(ValueError):
        validate_job(invalid)
