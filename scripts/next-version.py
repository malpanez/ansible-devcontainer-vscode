#!/usr/bin/env python3
"""Compute the next semver tag from conventional commits since the last tag.

Prints the next version (e.g. "v1.2.0") to stdout, or nothing when the
commits since the last tag warrant no release (docs/chore/ci only).
First release (no v* tags yet) is v1.0.0.

Bump rules over commit subjects and bodies since the last tag:
  - "type!:" subject or "BREAKING CHANGE" in body  -> major
  - feat                                           -> minor
  - fix / perf / security / revert                 -> patch
"""

from __future__ import annotations

import re
import subprocess

PATCH_TYPES = ("fix", "perf", "security", "revert")
SUBJECT_RE = re.compile(r"^(?P<type>[a-z]+)(?:\([^)]*\))?(?P<bang>!)?:")


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def main() -> None:
    try:
        last_tag = git("describe", "--tags", "--abbrev=0", "--match", "v*")
    except subprocess.CalledProcessError:
        print("v1.0.0")
        return

    log_range = f"{last_tag}..HEAD"
    subjects = git("log", log_range, "--pretty=%s").splitlines()
    bodies = git("log", log_range, "--pretty=%b")

    if not subjects:
        return

    # Promotion squash merges land as "chore: promote develop to main"
    # with the real feat/fix subjects as body bullets — scan those too.
    subjects += [
        line.removeprefix("* ").strip()
        for line in bodies.splitlines()
        if line.startswith("* ")
    ]

    major = minor = patch = False
    if "BREAKING CHANGE" in bodies:
        major = True
    for subject in subjects:
        match = SUBJECT_RE.match(subject)
        if not match:
            continue
        if match["bang"]:
            major = True
        elif match["type"] == "feat":
            minor = True
        elif match["type"] in PATCH_TYPES:
            patch = True

    if not (major or minor or patch):
        return

    version = last_tag.lstrip("v").split("-")[0]
    major_n, minor_n, patch_n = (int(part) for part in version.split("."))
    if major:
        major_n, minor_n, patch_n = major_n + 1, 0, 0
    elif minor:
        minor_n, patch_n = minor_n + 1, 0
    else:
        patch_n += 1
    print(f"v{major_n}.{minor_n}.{patch_n}")


if __name__ == "__main__":
    main()
