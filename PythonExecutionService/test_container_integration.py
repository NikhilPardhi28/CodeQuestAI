"""Real disposable-container checks; opt in only on a trusted Linux Docker runner."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docker_runner import run_isolated_job  # noqa: E402

pytestmark = pytest.mark.sandbox


def _job(
    source: str,
    function_name: str,
    argument: object,
    expected: object,
    *,
    time_limit_ms: int = 2500,
    output_limit_bytes: int = 4096,
) -> dict[str, object]:
    return {
        "submissionId": str(uuid.uuid4()),
        "challengeSlug": "sandbox-verification",
        "challengeVersion": 1,
        "evaluatorVersion": "python-v1",
        "source": source,
        "sourceDigest": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "definition": {
            "mode": "function",
            "functionName": function_name,
            "visibleTests": [{"input": [argument], "expected": expected}],
            "hiddenTests": [{"input": [argument], "expected": expected}],
            "timeLimitMs": time_limit_ms,
            "outputLimitBytes": output_limit_bytes,
        },
    }


def _require_real_sandbox() -> None:
    if os.environ.get("CODEQUEST_RUN_EVALUATOR_CONTAINER_TESTS") != "1":
        pytest.skip("real evaluator checks run only in the isolated Linux Docker CI job")
    image = os.environ.get("CODEQUEST_EVALUATOR_IMAGE", "")
    if not image.startswith("sha256:") or len(image) != len("sha256:") + 64:
        pytest.fail("CI must configure CODEQUEST_EVALUATOR_IMAGE from the built image content ID")


def test_disposable_linux_job_enforces_runtime_boundary_and_hides_host_files() -> None:
    _require_real_sandbox()
    marker_path = Path(tempfile.gettempdir()) / f"cq-host-marker-{uuid.uuid4().hex}"
    marker_path.write_text("host-only-marker", encoding="utf-8")
    expected = {
        "uid": 65534,
        "networkBlocked": True,
        "rootFilesystemReadOnly": True,
        "hostMarkerHidden": True,
        "dockerSocketAbsent": True,
    }
    source = """
def inspect_boundary(marker_path):
    import os
    import socket

    network_blocked = True
    try:
        connection = socket.socket()
        connection.settimeout(0.2)
        connection.connect(("1.1.1.1", 80))
        network_blocked = False
        connection.close()
    except OSError:
        pass

    root_read_only = False
    try:
        with open("/opt/codequest/write-probe", "w") as probe:
            probe.write("not allowed")
    except OSError:
        root_read_only = True

    return {
        "uid": os.geteuid(),
        "networkBlocked": network_blocked,
        "rootFilesystemReadOnly": root_read_only,
        "hostMarkerHidden": not os.path.exists(marker_path),
        "dockerSocketAbsent": not os.path.exists("/var/run/docker.sock"),
    }
"""
    try:
        result = run_isolated_job(_job(source, "inspect_boundary", str(marker_path), expected))
    finally:
        marker_path.unlink(missing_ok=True)

    assert result["visibleResults"] == [{"passed": True, "diagnosticCode": None, "message": ""}]
    assert result["hiddenPassed"] == 1
    assert result["hiddenTotal"] == 1
    assert "hiddenResults" not in result
    assert "host-only-marker" not in json.dumps(result)


def test_disposable_linux_job_enforces_time_and_output_limits() -> None:
    _require_real_sandbox()
    infinite_loop = "def stall(value):\n    while True:\n        pass\n"
    timed_out = run_isolated_job(_job(infinite_loop, "stall", None, None, time_limit_ms=300))
    assert timed_out.get("timedOut") is True
    assert timed_out["visibleResults"][0]["diagnosticCode"] == "timeout"

    output_flood = "def flood(value):\n    print('x' * 8192)\n    return value\n"
    bounded = run_isolated_job(_job(output_flood, "flood", "ok", "ok", output_limit_bytes=1024))
    assert bounded["visibleResults"][0]["diagnosticCode"] == "output_limit"
