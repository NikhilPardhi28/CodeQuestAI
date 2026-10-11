"""Validate repository dependency and local environment examples."""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate() -> list[str]:
    problems: list[str] = []
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    specifiers = [
        *project["project"].get("dependencies", []),
        *project["dependency-groups"].get("dev", []),
    ]
    for dependency in specifiers:
        if "==" not in dependency:
            problems.append(f"Dependency is not exactly pinned: {dependency}")

    env_path = ROOT / ".env.example"
    seen: set[str] = set()
    for line_number, raw_line in enumerate(env_path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            problems.append(f".env.example:{line_number}: expected KEY=value")
            continue
        key, value = line.split("=", 1)
        if not key.startswith("CODEQUEST_"):
            problems.append(f".env.example:{line_number}: key lacks CODEQUEST_ prefix")
        if key in seen:
            problems.append(f".env.example:{line_number}: duplicate key {key}")
        seen.add(key)
        if not value:
            problems.append(f".env.example:{line_number}: empty value for {key}")
        if re.search(r"(sk-[A-Za-z0-9]{12,}|gh[pousr]_[A-Za-z0-9]{20,})", value):
            problems.append(f".env.example:{line_number}: credential-like value is forbidden")
    return problems


def main() -> int:
    problems = validate()
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print("Dependency pins and local environment example are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
