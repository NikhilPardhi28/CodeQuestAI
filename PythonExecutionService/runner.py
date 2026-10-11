"""Container entry point: evaluates only after the Docker boundary is applied."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time

CHILD = r"""import json, sys
request = json.loads(sys.stdin.buffer.read())
try:
    namespace = {}
    exec(compile(request["source"], "<submission>", "exec"), namespace, namespace)
    value = namespace[request["functionName"]](*request["input"])
    print(json.dumps({"value": value}, separators=(",", ":")))
except SyntaxError:
    print(json.dumps({"diagnostic": "syntax_error"}))
except Exception:
    print(json.dumps({"diagnostic": "runtime_error"}))
"""


def _set_child_file_size_limit(max_bytes: int) -> None:
    import resource

    resource.setrlimit(resource.RLIMIT_FSIZE, (max_bytes, max_bytes))


def _kill_process_tree(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (AttributeError, OSError):
        process.kill()


def main() -> int:
    job = json.loads(sys.stdin.buffer.read(96 * 1024 + 1))
    definition = job["definition"]
    limit = int(definition["outputLimitBytes"])
    result = {
        "submissionId": job["submissionId"],
        "challengeSlug": job["challengeSlug"],
        "challengeVersion": job["challengeVersion"],
        "evaluatorVersion": job["evaluatorVersion"],
        "visibleResults": [],
        "hiddenPassed": 0,
        "hiddenTotal": len(definition["hiddenTests"]),
    }
    deadline = time.monotonic() + int(definition["timeLimitMs"]) / 1000
    for is_hidden, tests in (
        (False, definition["visibleTests"]),
        (True, definition["hiddenTests"]),
    ):
        for test in tests:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                result["timedOut"] = True
                outcome = {"passed": False, "diagnosticCode": "timeout", "message": ""}
                if not is_hidden:
                    result["visibleResults"].append(outcome)
                continue
            payload = {
                "source": job["source"],
                "functionName": definition["functionName"],
                "input": test["input"],
            }
            try:
                with tempfile.TemporaryFile() as output:
                    process = subprocess.Popen(
                        [sys.executable, "-I", "-S", "-c", CHILD],
                        stdin=subprocess.PIPE,
                        stdout=output,
                        stderr=output,
                        start_new_session=True,
                        preexec_fn=lambda: _set_child_file_size_limit(limit + 1),
                        env={"PATH": "/usr/local/bin:/usr/bin:/bin", "PYTHONIOENCODING": "utf-8"},
                    )
                    try:
                        process.communicate(
                            input=json.dumps(payload, separators=(",", ":")).encode(),
                            timeout=remaining,
                        )
                    except subprocess.TimeoutExpired:
                        _kill_process_tree(process)
                        process.communicate()
                        result["timedOut"] = True
                        outcome = {
                            "passed": False,
                            "diagnosticCode": "timeout",
                            "message": "",
                        }
                        if is_hidden:
                            result["hiddenPassed"] += 0
                        else:
                            result["visibleResults"].append(outcome)
                        continue
                    output.seek(0, os.SEEK_END)
                    output_size = output.tell()
                    if output_size > limit:
                        outcome = {"passed": False, "diagnosticCode": "output_limit", "message": ""}
                    elif process.returncode != 0:
                        outcome = {
                            "passed": False,
                            "diagnosticCode": "runtime_error",
                            "message": "",
                        }
                    else:
                        output.seek(0)
                        raw_output = output.read(limit + 1)
                        returned = json.loads(raw_output)
                        if returned.get("diagnostic"):
                            outcome = {
                                "passed": False,
                                "diagnosticCode": returned["diagnostic"],
                                "message": "",
                            }
                        else:
                            passed = returned.get("value") == test["expected"]
                            outcome = {
                                "passed": passed,
                                "diagnosticCode": None if passed else "wrong_answer",
                                "message": "",
                            }
                if is_hidden:
                    result["hiddenPassed"] += int(outcome["passed"])
                else:
                    result["visibleResults"].append(outcome)
            except (ValueError, TypeError):
                outcome = {"passed": False, "diagnosticCode": "runtime_error", "message": ""}
                if is_hidden:
                    result["hiddenPassed"] += 0
                else:
                    result["visibleResults"].append(outcome)
    sys.stdout.write(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
