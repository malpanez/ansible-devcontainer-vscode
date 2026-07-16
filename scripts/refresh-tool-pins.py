#!/usr/bin/env python3
"""Recompute the pinned SHA-256 for tools with no upstream checksum manifest.

Renovate bumps every pinned version natively (regex customManagers) but
cannot recompute a download hash. age, tectonic and AWS CLI publish no
checksum manifest, so their hardcoded SHA-256 is the only integrity check.
Renovate runs this as a postUpgradeTask after bumping one of their ARGs:

    scripts/refresh-tool-pins.py --sync-hashes

It reads the version already in each Dockerfile and rewrites the matching
hash. Idempotent; a no-op when the hashes already match.
"""

from __future__ import annotations

import hashlib
import re
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TF_DOCKERFILE = REPO_ROOT / "devcontainers/terraform/Dockerfile"
LATEX_DOCKERFILE = REPO_ROOT / "devcontainers/latex/Dockerfile"


def http_get(url: str, attempts: int = 4) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "refresh-tool-pins"})
    # CDNs (GitHub releases, AWS CloudFront) return sporadic 404/5xx at the
    # edge; retry with backoff so a blip doesn't fail a hash sync.
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            status = getattr(error, "code", None)
            retriable = (
                status in (403, 404, 408, 425, 429, 500, 502, 503, 504)
                or status is None
            )
            if attempt == attempts or not retriable:
                raise
            print(f"  retry {attempt}/{attempts} ({status or error}) {url}")
            time.sleep(2 * attempt)
    raise RuntimeError("unreachable")


def sha256_of(url: str) -> str:
    digest = hashlib.sha256()
    digest.update(http_get(url))
    return digest.hexdigest()


@dataclass
class Tool:
    name: str
    version_pattern: tuple[Path, str]
    # (file, regex whose group 1 is everything up to the hash, url template)
    hash_patterns: list[tuple[Path, str, str]]


TOOLS: list[Tool] = [
    Tool(
        name="age",
        version_pattern=(TF_DOCKERFILE, r"ARG AGE_VERSION=([0-9.]+)"),
        hash_patterns=[
            (
                TF_DOCKERFILE,
                r'(ARCH="amd64"; AGE_SHA256=")([a-f0-9]{64})',
                "https://github.com/FiloSottile/age/releases/download/v{v}/age-v{v}-linux-amd64.tar.gz",
            ),
            (
                TF_DOCKERFILE,
                r'(ARCH="arm64"; AGE_SHA256=")([a-f0-9]{64})',
                "https://github.com/FiloSottile/age/releases/download/v{v}/age-v{v}-linux-arm64.tar.gz",
            ),
        ],
    ),
    Tool(
        name="tectonic",
        version_pattern=(LATEX_DOCKERFILE, r"ARG TECTONIC_VERSION=([0-9.]+)"),
        hash_patterns=[
            (
                LATEX_DOCKERFILE,
                r'(TECTONIC_ARCH="x86_64-unknown-linux-musl"; \\\n\s*TECTONIC_SHA256=")([a-f0-9]{64})',
                "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%40{v}/tectonic-{v}-x86_64-unknown-linux-musl.tar.gz",
            ),
            (
                LATEX_DOCKERFILE,
                r'(TECTONIC_ARCH="aarch64-unknown-linux-musl"; \\\n\s*TECTONIC_SHA256=")([a-f0-9]{64})',
                "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%40{v}/tectonic-{v}-aarch64-unknown-linux-musl.tar.gz",
            ),
        ],
    ),
    Tool(
        name="aws-cli",
        version_pattern=(TF_DOCKERFILE, r"ARG AWS_CLI_VERSION=([0-9.]+)"),
        hash_patterns=[
            (
                TF_DOCKERFILE,
                r'(AWS_ARCH="x86_64"; AWS_SHA256=")([a-f0-9]{64})',
                "https://awscli.amazonaws.com/awscli-exe-linux-x86_64-{v}.zip",
            ),
            (
                TF_DOCKERFILE,
                r'(AWS_ARCH="aarch64"; AWS_SHA256=")([a-f0-9]{64})',
                "https://awscli.amazonaws.com/awscli-exe-linux-aarch64-{v}.zip",
            ),
        ],
    ),
]


def current_version(tool: Tool) -> str:
    path, pattern = tool.version_pattern
    match = re.search(pattern, path.read_text())
    if not match:
        raise RuntimeError(f"{tool.name}: version pattern not found in {path}")
    return match.group(1)


def sync_hashes() -> int:
    for tool in TOOLS:
        try:
            version = current_version(tool)
        except Exception as error:  # noqa: BLE001 - report and continue
            print(f"{tool.name}: SKIPPED ({error})")
            continue
        for path, pattern, url_template in tool.hash_patterns:
            url = url_template.format(v=version)
            print(f"{tool.name}: hashing {url}")
            digest = sha256_of(url)
            text = path.read_text()
            updated, count = re.subn(pattern, rf"\g<1>{digest}", text)
            if count == 0:
                raise RuntimeError(f"{tool.name}: hash pattern missing in {path}")
            path.write_text(updated)
    return 0


if __name__ == "__main__":
    if "--sync-hashes" not in sys.argv[1:]:
        print("usage: refresh-tool-pins.py --sync-hashes", file=sys.stderr)
        sys.exit(2)
    sys.exit(sync_hashes())
