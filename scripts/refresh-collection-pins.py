#!/usr/bin/env python3
"""Recompute the sha256 of each Ansible collection pinned for the images.

devcontainers/ansible/collections*.txt pin every collection the ansible
images bake in as "<namespace.name> <version> <sha256>". Renovate bumps the
version with a galaxy-collection custom manager but cannot touch the hash,
so the renovate-postprocess workflow runs this after such a bump:

    scripts/refresh-collection-pins.py --sync-hashes

For every line it downloads the Galaxy artifact of the pinned version,
hashes it, and requires that hash to equal the sha256 Galaxy publishes for
the artifact before writing it. Idempotent; a no-op when nothing moved.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LISTS_GLOB = "devcontainers/ansible/collections*.txt"
GALAXY_API = (
    "https://galaxy.ansible.com/api/v3/plugin/ansible/content/published/collections"
)
# The version goes into a Galaxy URL path, so it is held to the shape
# install-collections.sh accepts instead of any non-blank run.
PIN_LINE = re.compile(
    r"^(?P<name>[a-z0-9_]+\.[a-z0-9_]+)"
    r" (?P<version>[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?)"
    r" (?P<sha256>[a-f0-9]{64})$",
    re.MULTILINE,
)
RETRIABLE = (403, 404, 408, 425, 429, 500, 502, 503, 504)


def http_get(url: str, attempts: int = 4) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "refresh-collection-pins"}
    )
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body: bytes = response.read()
                return body
        except urllib.error.URLError as error:  # HTTPError included
            status = getattr(error, "code", None)
            if attempt == attempts or (status is not None and status not in RETRIABLE):
                raise
            print(f"  retry {attempt}/{attempts} ({status or error}) {url}")
            time.sleep(2 * attempt)
    raise RuntimeError("unreachable")


def galaxy_sha256(name: str, version: str) -> str:
    namespace, collection = name.split(".", 1)
    detail_url = f"{GALAXY_API}/index/{namespace}/{collection}/versions/{version}/"
    detail = json.loads(http_get(detail_url))
    published = detail["artifact"]["sha256"]
    computed = hashlib.sha256(http_get(detail["download_url"])).hexdigest()
    if computed != published:
        raise RuntimeError(
            f"{name} {version}: artifact hashes to {computed}, Galaxy publishes {published}"
        )
    return computed


def sync_file(path: Path, fetch: Callable[[str, str], str]) -> bool:
    text = path.read_text()
    for number, line in enumerate(text.splitlines(), start=1):
        if line and not line.startswith("#") and PIN_LINE.fullmatch(line) is None:
            raise RuntimeError(
                f"{path}:{number}: not '<namespace.name> <version> <sha256>': {line}"
            )

    def refreshed(match: re.Match[str]) -> str:
        name, version = match.group("name", "version")
        print(f"{name} {version}: hashing the Galaxy artifact")
        return f"{name} {version} {fetch(name, version)}"

    updated = PIN_LINE.sub(refreshed, text)
    if updated == text:
        return False
    path.write_text(updated)
    return True


def sync_hashes(
    root: Path = REPO_ROOT, fetch: Callable[[str, str], str] = galaxy_sha256
) -> int:
    lists = sorted(root.glob(LISTS_GLOB))
    if not lists:
        raise RuntimeError(f"no collection lists match {LISTS_GLOB}")
    for path in lists:
        if sync_file(path, fetch):
            print(f"{path.relative_to(root)}: hashes updated")
    return 0


if __name__ == "__main__":
    if "--sync-hashes" not in sys.argv[1:]:
        print("usage: refresh-collection-pins.py --sync-hashes", file=sys.stderr)
        sys.exit(2)
    sys.exit(sync_hashes())
