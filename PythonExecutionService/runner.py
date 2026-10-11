"""Container entry point: evaluates only after the Docker boundary is applied."""

from __future__ import annotations

import json
import subprocess
import sys
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
                completed = subprocess.run(
                    [sys.executable, "-I", "-S", "-c", CHILD],
                    input=json.dumps(payload, separators=(",", ":")).encode(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    timeout=remaining,
                    check=False,
                    env={"PATH": "/usr/local/bin:/usr/bin:/bin", "PYTHONIOENCODING": "utf-8"},
                )
                if len(completed.stdout) > limit:
                    outcome = {"passed": False, "diagnosticCode": "output_limit", "message": ""}
                elif completed.returncode != 0:
                    outcome = {"passed": False, "diagnosticCode": "runtime_error", "message": ""}
                else:
                    returned = json.loads(completed.stdout)
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
            except subprocess.TimeoutExpired:
                result["timedOut"] = True
                outcome = {"passed": False, "diagnosticCode": "timeout", "message": ""}
            except (ValueError, TypeError):
                outcome = {"passed": False, "diagnosticCode": "runtime_error", "message": ""}
            if is_hidden:
                result["hiddenPassed"] += int(outcome["passed"])
            else:
                result["visibleResults"].append(outcome)
    sys.stdout.write(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
