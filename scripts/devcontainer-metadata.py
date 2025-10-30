#!/usr/bin/env python3
"""
Inspect the .devcontainer/.template-metadata.json file and verify it matches
the current template contents.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_signature(template_root: Path) -> str:
    checksums = []
    for file_path in sorted(template_root.rglob("*")):
        if file_path.is_file():
            checksums.append(sha1_file(file_path))
    joined = "".join(checksums).encode()
    return hashlib.sha256(joined).hexdigest()


def load_metadata(metadata_path: Path) -> dict:
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
    with metadata_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify Dev Container template metadata."
    )
    parser.add_argument(
        "--target",
        default=".devcontainer",
        help="Path to the .devcontainer directory (default: .devcontainer)",
    )
    parser.add_argument(
        "--templates",
        default="devcontainers",
        help="Path to the devcontainers/ directory (default: devcontainers)",
    )
    args = parser.parse_args()

    target_dir = Path(args.target).resolve()
    templates_dir = Path(args.templates).resolve()
    metadata_path = target_dir / ".template-metadata.json"

    try:
        metadata = load_metadata(metadata_path)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    stack = metadata.get("stack")
    if not stack:
        print("Metadata missing 'stack' field.", file=sys.stderr)
        return 1

    source_path = metadata.get("source")
    if not source_path:
        print("Metadata missing 'source' field.", file=sys.stderr)
        return 1

    current_template = templates_dir / stack
    if not current_template.exists():
        print(
            f"Template directory for stack '{stack}' not found at {current_template}",
            file=sys.stderr,
        )
        return 1

    expected_signature = compute_signature(current_template)
    recorded_signature = metadata.get("signature")

    print(f"Stack:            {stack}")
    print(f"Template source:  {current_template}")
    print(f"Recorded source:  {source_path}")
    print(f"Recorded sig:     {recorded_signature}")
    print(f"Computed sig:     {expected_signature}")

    if expected_signature != recorded_signature:
        print(
            "Status: mismatch (template has changed since last provisioning).",
            file=sys.stderr,
        )
        return 2

    print("Status: OK (metadata matches current template).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
