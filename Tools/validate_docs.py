"""Validate local Markdown links and heading fragments using only the stdlib."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)


def slugify(heading: str) -> str:
    heading = re.sub(r"`([^`]*)`", r"\1", heading)
    heading = re.sub(r"[^a-z0-9 -]", "", heading.lower())
    return re.sub(r"\s+", "-", heading.strip())


def check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    headings: set[str] = set()
    for heading in HEADING_RE.findall(text):
        base = slugify(heading)
        candidate = base
        suffix = 1
        while candidate in headings:
            suffix += 1
            candidate = f"{base}-{suffix}"
        headings.add(candidate)

    issues: list[str] = []
    for match in LINK_RE.finditer(text):
        target = match.group(1).strip().split()[0].strip("<>")
        parsed = urlsplit(target)
        if parsed.scheme or target.startswith("//"):
            continue
        relative = unquote(parsed.path)
        if not relative:
            linked_path = path
        else:
            linked_path = (path.parent / relative).resolve()
        try:
            linked_path.relative_to(ROOT)
        except ValueError:
            issues.append(f"{path.relative_to(ROOT)}: link escapes repository: {target}")
            continue
        if not linked_path.exists():
            issues.append(f"{path.relative_to(ROOT)}: missing link target: {target}")
            continue
        fragment = unquote(parsed.fragment)
        if fragment and linked_path.is_file() and linked_path.suffix.lower() == ".md":
            linked_text = linked_path.read_text(encoding="utf-8")
            linked_headings = {slugify(item) for item in HEADING_RE.findall(linked_text)}
            if fragment not in linked_headings:
                issues.append(f"{path.relative_to(ROOT)}: missing heading fragment: {target}")
    return issues


def main() -> int:
    markdown_files = sorted(ROOT.rglob("*.md"))
    ignored = {".git", ".venv", "node_modules", "Library"}
    markdown_files = [path for path in markdown_files if not ignored.intersection(path.parts)]
    problems = [issue for path in markdown_files for issue in check_file(path)]
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print(f"Validated local Markdown links in {len(markdown_files)} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
