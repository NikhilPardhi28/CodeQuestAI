"""Per-job Docker launcher. Student source never runs in this process."""

from __future__ import annotations

import json
import os
import re
import subprocess
import uuid
from hashlib import sha256
from keyword import iskeyword

MAX_SOURCE_BYTES = 32 * 1024
MAX_JOB_BYTES = 96 * 1024
MAX_DIAGNOSTIC_BYTES = 64 * 1024
IMAGE_DIGEST = re.compile(r"^.+@sha256:[0-9a-f]{64}$")
LOCAL_IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")


class EvaluationUnavailable(RuntimeError):
    pass


def validate_job(job: object) -> dict[str, object]:
    if not isinstance(job, dict):
        raise ValueError("job must be an object")
    required = {
        "submissionId",
        "challengeSlug",
        "challengeVersion",
        "evaluatorVersion",
        "source",
        "sourceDigest",
        "definition",
    }
    if set(job) != required:
        raise ValueError("unexpected job fields")
    source = job["source"]
    if (
        not isinstance(source, str)
        or not source.strip()
        or len(source.encode("utf-8")) > MAX_SOURCE_BYTES
    ):
        raise ValueError("source outside limits")
    if (
        not isinstance(job["sourceDigest"], str)
        or job["sourceDigest"] != sha256(source.encode("utf-8")).hexdigest()
    ):
        raise ValueError("source digest mismatch")
    try:
        uuid.UUID(str(job["submissionId"]))
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid submission id") from exc
    if (
        not isinstance(job["challengeSlug"], str)
        or not job["challengeSlug"]
        or not isinstance(job["challengeVersion"], int)
        or isinstance(job["challengeVersion"], bool)
        or job["challengeVersion"] < 1
        or not isinstance(job["evaluatorVersion"], str)
        or not job["evaluatorVersion"]
    ):
        raise ValueError("invalid challenge identity")
    definition = job["definition"]
    if not isinstance(definition, dict) or set(definition) != {
        "mode",
        "functionName",
        "visibleTests",
        "hiddenTests",
        "timeLimitMs",
        "outputLimitBytes",
    }:
        raise ValueError("invalid challenge definition")
    function_name = definition["functionName"]
    if (
        definition["mode"] != "function"
        or not isinstance(function_name, str)
        or not function_name.isidentifier()
        or iskeyword(function_name)
    ):
        raise ValueError("unsupported challenge mode")
    visible_tests = definition["visibleTests"]
    hidden_tests = definition["hiddenTests"]
    if (
        not isinstance(visible_tests, list)
        or not isinstance(hidden_tests, list)
        or not visible_tests
        or not hidden_tests
    ):
        raise ValueError("visible and hidden tests are required")
    tests = visible_tests + hidden_tests
    if not 1 <= len(tests) <= 100:
        raise ValueError("test count outside limits")
    for test in tests:
        if (
            not isinstance(test, dict)
            or set(test) != {"input", "expected"}
            or not isinstance(test["input"], list)
        ):
            raise ValueError("invalid test definition")
    if (
        not isinstance(definition["timeLimitMs"], int)
        or isinstance(definition["timeLimitMs"], bool)
        or not 100 <= definition["timeLimitMs"] <= 5000
    ):
        raise ValueError("invalid time limit")
    if (
        not isinstance(definition["outputLimitBytes"], int)
        or isinstance(definition["outputLimitBytes"], bool)
        or not 1024 <= definition["outputLimitBytes"] <= MAX_DIAGNOSTIC_BYTES
    ):
        raise ValueError("invalid output limit")
    if len(json.dumps(job, separators=(",", ":")).encode()) > MAX_JOB_BYTES:
        raise ValueError("job exceeds byte limit")
    return job


def _kill_container(name: str) -> None:
    try:
        subprocess.run(
            ["docker", "kill", name],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def run_isolated_job(raw_job: object) -> dict[str, object]:
    job = validate_job(raw_job)
    image = os.environ.get("CODEQUEST_EVALUATOR_IMAGE", "")
    # CI can address the just-built disposable image by its immutable content ID;
    # deployed workers must use a repository-qualified registry digest.
    local_image_id_allowed = os.environ.get("CODEQUEST_ENV", "").lower() in {
        "local",
        "test",
        "ci",
    }
    if not (
        IMAGE_DIGEST.fullmatch(image)
        or (local_image_id_allowed and LOCAL_IMAGE_ID.fullmatch(image))
    ):
        raise EvaluationUnavailable("an immutable evaluator image digest is required")
    definition = job["definition"]
    name = "cq-eval-" + uuid.uuid4().hex[:20]
    command = [
        "docker",
        "run",
        "--rm",
        "--interactive",
        "--name",
        name,
        "--network=none",
        "--read-only",
        "--user=65534:65534",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=16",
        "--memory=128m",
        "--memory-swap=128m",
        "--cpus=1",
        "--ulimit",
        "core=0",
        "--ulimit",
        "fsize=65536:65536",
        "--ulimit",
        "nofile=64:64",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=16m",
        image,
    ]
    payload = json.dumps(job, separators=(",", ":")).encode("utf-8")
    process = None
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        stdout, _ = process.communicate(
            payload,
            timeout=(int(definition["timeLimitMs"]) / 1000) + 3,
        )
    except subprocess.TimeoutExpired:
        _kill_container(name)
        if process is not None:
            try:
                process.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
        return {
            "submissionId": job["submissionId"],
            "challengeSlug": job["challengeSlug"],
            "challengeVersion": job["challengeVersion"],
            "evaluatorVersion": job["evaluatorVersion"],
            "visibleResults": [],
            "hiddenPassed": 0,
            "hiddenTotal": len(definition["hiddenTests"]),
            "timedOut": True,
        }
    except OSError as exc:
        raise EvaluationUnavailable("container runtime is unavailable") from exc
    if process is None or process.returncode != 0 or len(stdout) > 32 * 1024:
        raise EvaluationUnavailable("isolated job did not return a valid result")
    try:
        result = json.loads(stdout)
    except (ValueError, UnicodeDecodeError) as exc:
        raise EvaluationUnavailable("isolated job returned invalid data") from exc
    return result
