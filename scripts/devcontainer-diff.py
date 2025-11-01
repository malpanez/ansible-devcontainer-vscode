#!/usr/bin/env python3
"""
Show differences between .devcontainer/ and the source template under devcontainers/<stack>.
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path


def load_metadata(metadata_path: Path) -> dict:
    with metadata_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def list_files(root: Path) -> set[Path]:
    return {p for p in root.rglob("*") if p.is_file()}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_bytes().hex()


def diff_files(source: Path, target: Path) -> str:
    source_text = read_text(source)
    target_text = read_text(target)
    source_lines = source_text.splitlines(keepends=True)
    target_lines = target_text.splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            source_lines,
            target_lines,
            fromfile=str(source),
            tofile=str(target),
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diff current .devcontainer contents against template."
    )
    parser.add_argument(
        "--target", default=".devcontainer", help="Path to the .devcontainer directory."
    )
    parser.add_argument(
        "--templates",
        default="devcontainers",
        help="Path to the devcontainers/ directory.",
    )
    parser.add_argument(
        "--stack", help="Template stack to compare. Defaults to metadata stack."
    )
    parser.add_argument(
        "--metadata",
        help="Explicit metadata path (defaults to <target>/.template-metadata.json).",
    )
    args = parser.parse_args()

    target = Path(args.target).resolve()
    if not target.exists():
        print(f"Target directory not found: {target}", file=sys.stderr)
        return 1

    metadata_path = (
        Path(args.metadata).resolve()
        if args.metadata
        else target / ".template-metadata.json"
    )
    if not metadata_path.exists():
        print(f"Metadata file not found: {metadata_path}", file=sys.stderr)
        return 1

    metadata = load_metadata(metadata_path)
    stack = args.stack or metadata.get("stack")
    if not stack:
        print("Stack not specified and metadata missing 'stack'.", file=sys.stderr)
        return 1

    templates_root = Path(args.templates).resolve()
    source = templates_root / stack
    if not source.exists():
        print(
            f"Template stack '{stack}' not found under {templates_root}",
            file=sys.stderr,
        )
        return 1

    target_files = list_files(target)
    source_files = list_files(source)

    target_rel = {p.relative_to(target) for p in target_files}
    source_rel = {p.relative_to(source) for p in source_files}

    additions = target_rel - source_rel
    deletions = source_rel - target_rel

    changed = False

    for addition in sorted(additions):
        print(f"+++ Added file: {addition}")
        changed = True

    for deletion in sorted(deletions):
        print(f"--- Missing file from template: {deletion}")
        changed = True

    for src_file in sorted(source_files):
        rel = src_file.relative_to(source)
        tgt_file = target / rel
        if not tgt_file.exists():
            continue
        if src_file.read_bytes() != tgt_file.read_bytes():
            diff = diff_files(src_file, tgt_file)
            if diff:
                print(diff)
                changed = True

    if not changed:
        print("No differences detected between .devcontainer/ and template.")
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
