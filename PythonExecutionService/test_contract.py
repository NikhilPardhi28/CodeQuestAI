"""Safe protocol checks only; these tests never execute learner source."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docker_runner import (  # noqa: E402
    EvaluationUnavailable,
    run_isolated_job,
    validate_job,
)


@pytest.fixture
def job() -> dict[str, object]:
    return {
        "submissionId": "0fedb4c5-58e0-49b7-8c91-3de94099db6b",
        "challengeSlug": "signal-coordinate",
        "challengeVersion": 1,
        "evaluatorVersion": "python-v1",
        "source": "def signal_coordinate(x, y): return (x, y)",
        "sourceDigest": hashlib.sha256(b"def signal_coordinate(x, y): return (x, y)").hexdigest(),
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


def _fake_result(job: dict[str, object]) -> bytes:
    return json.dumps(
        {
            "submissionId": job["submissionId"],
            "challengeSlug": job["challengeSlug"],
            "challengeVersion": job["challengeVersion"],
            "evaluatorVersion": job["evaluatorVersion"],
            "visibleResults": [{"passed": True, "diagnosticCode": None, "message": ""}],
            "hiddenPassed": 1,
            "hiddenTotal": 1,
        }
    ).encode()


def test_launcher_uses_restricted_container_and_never_evaluates_on_host(job, monkeypatch):
    import docker_runner

    captured: dict[str, object] = {}

    class FakeProcess:
        returncode = 0

        def __init__(self, command, **_kwargs):
            captured["command"] = command

        def communicate(self, input=None, timeout=None):
            captured["payload"] = json.loads(input)
            captured["timeout"] = timeout
            return _fake_result(job), None

    monkeypatch.setenv("CODEQUEST_EVALUATOR_IMAGE", "example/evaluator@sha256:" + "a" * 64)
    monkeypatch.setattr(docker_runner.subprocess, "Popen", FakeProcess)
    job["source"] = "while True: pass"
    job["sourceDigest"] = hashlib.sha256(job["source"].encode()).hexdigest()

    result = run_isolated_job(job)
    command = captured["command"]
    assert result["submissionId"] == job["submissionId"]
    assert captured["payload"]["source"] == "while True: pass"
    assert "--network=none" in command
    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert "--user=65534:65534" in command
    assert "--pids-limit=16" in command
    assert "--memory=128m" in command
    assert "--cpus=1" in command
    assert "--privileged" not in command
    assert "--mount" not in command
    assert "-v" not in command


def test_launcher_timeout_kills_the_named_container_without_host_fallback(job, monkeypatch):
    import subprocess

    import docker_runner

    killed: list[str] = []

    class TimedOutProcess:
        returncode = None
        command = ["docker", "run"]

        def __init__(self, _command, **_kwargs):
            pass

        def communicate(self, input=None, timeout=None):
            if input is not None:
                raise subprocess.TimeoutExpired(self.command, timeout)
            return b"", None

        def kill(self):
            self.returncode = -9

    monkeypatch.setenv("CODEQUEST_EVALUATOR_IMAGE", "example/evaluator@sha256:" + "b" * 64)
    monkeypatch.setattr(docker_runner.subprocess, "Popen", TimedOutProcess)
    monkeypatch.setattr(docker_runner, "_kill_container", killed.append)

    result = run_isolated_job(job)
    assert result["timedOut"] is True
    assert len(killed) == 1
    assert killed[0].startswith("cq-eval-")


def test_launcher_rejects_mutable_or_malformed_image_digest(job, monkeypatch):
    monkeypatch.setenv("CODEQUEST_EVALUATOR_IMAGE", "example/evaluator:latest")
    with pytest.raises(EvaluationUnavailable, match="immutable evaluator image digest"):
        run_isolated_job(job)


def test_worker_job_requires_digest_matching_source(job):
    job["sourceDigest"] = "0" * 64
    with pytest.raises(ValueError, match="source digest mismatch"):
        validate_job(job)
