#!/usr/bin/env python3
"""Refresh pinned tool versions (and their pinned hashes) from upstream.

Queries the latest release of every tool pinned as a Dockerfile ARG,
updates the ARG lines, and recomputes the per-release SHA-256 pins for
the tools whose upstream publishes no checksum manifest (age, tectonic,
AWS CLI). Tools verified against upstream manifests at build time
(terraform, terragrunt, tflint, sops, uv) only need the version bump.

Idempotent: exits cleanly with no changes when everything is current.
Run by the weekly dependency-refresh workflow; safe to run locally.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
API = "https://api.github.com"


def http_get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "refresh-tool-pins"})
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token and url.startswith(API):
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def latest_release_tag(repo: str) -> str:
    data = json.loads(http_get(f"{API}/repos/{repo}/releases/latest"))
    return str(data["tag_name"])


def latest_tag(repo: str) -> str:
    data = json.loads(http_get(f"{API}/repos/{repo}/tags?per_page=1"))
    return str(data[0]["name"])


def sha256_of(url: str) -> str:
    digest = hashlib.sha256()
    digest.update(http_get(url))
    return digest.hexdigest()


@dataclass
class Tool:
    name: str
    repo: str
    version_patterns: list[tuple[Path, str]]
    # (file, regex-with-two-groups, artifact-url-template) computed hashes
    hash_patterns: list[tuple[Path, str, str]] = field(default_factory=list)
    use_tags: bool = False
    strip_prefix: str = "v"

    def latest(self) -> str:
        tag = latest_tag(self.repo) if self.use_tags else latest_release_tag(self.repo)
        return tag.removeprefix(self.strip_prefix)


TF_DOCKERFILE = REPO_ROOT / "devcontainers/terraform/Dockerfile"
LATEX_DOCKERFILE = REPO_ROOT / "devcontainers/latex/Dockerfile"

TOOLS: list[Tool] = [
    Tool(
        name="uv",
        repo="astral-sh/uv",
        strip_prefix="",
        version_patterns=[
            (
                REPO_ROOT / "devcontainers/ansible/Dockerfile.podman",
                r'(ARG UV_VERSION=")([0-9.]+)(")',
            ),
            (
                REPO_ROOT / "devcontainers/base/Dockerfile",
                r"(ARG UV_VERSION=)([0-9.]+)()",
            ),
            (
                REPO_ROOT / "devcontainers/golang/Dockerfile",
                r'(ARG UV_VERSION=")([0-9.]+)(")',
            ),
            (LATEX_DOCKERFILE, r"(ARG UV_VERSION=)([0-9.]+)()"),
            (TF_DOCKERFILE, r"(ARG UV_VERSION=)([0-9.]+)()"),
            (
                REPO_ROOT / "roles/ansible_environment/defaults/main.yml",
                r"(uv_version \| default\(')([0-9.]+)('\, true\))",
            ),
        ],
    ),
    Tool(
        name="terraform",
        repo="hashicorp/terraform",
        version_patterns=[(TF_DOCKERFILE, r"(ARG TERRAFORM_VERSION=)([0-9.]+)()")],
    ),
    Tool(
        name="terragrunt",
        repo="gruntwork-io/terragrunt",
        version_patterns=[(TF_DOCKERFILE, r"(ARG TERRAGRUNT_VERSION=)([0-9.]+)()")],
    ),
    Tool(
        name="tflint",
        repo="terraform-linters/tflint",
        version_patterns=[(TF_DOCKERFILE, r"(ARG TFLINT_VERSION=)([0-9.]+)()")],
    ),
    Tool(
        name="sops",
        repo="getsops/sops",
        version_patterns=[(TF_DOCKERFILE, r"(ARG SOPS_VERSION=)([0-9.]+)()")],
    ),
    Tool(
        name="age",
        repo="FiloSottile/age",
        version_patterns=[(TF_DOCKERFILE, r"(ARG AGE_VERSION=)([0-9.]+)()")],
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
        repo="tectonic-typesetting/tectonic",
        strip_prefix="tectonic@",
        version_patterns=[(LATEX_DOCKERFILE, r"(ARG TECTONIC_VERSION=)([0-9.]+)()")],
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
        repo="aws/aws-cli",
        use_tags=True,
        strip_prefix="",
        version_patterns=[(TF_DOCKERFILE, r"(ARG AWS_CLI_VERSION=)([0-9.]+)()")],
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
    path, pattern = tool.version_patterns[0]
    match = re.search(pattern, path.read_text())
    if not match:
        raise RuntimeError(f"{tool.name}: version pattern not found in {path}")
    return match.group(2)


def bump(tool: Tool, new: str) -> None:
    for path, pattern in tool.version_patterns:
        text = path.read_text()
        updated, count = re.subn(pattern, rf"\g<1>{new}\g<3>", text)
        if count == 0:
            raise RuntimeError(f"{tool.name}: pattern missing in {path}")
        path.write_text(updated)
    for path, pattern, url_template in tool.hash_patterns:
        url = url_template.format(v=new)
        print(f"  hashing {url}")
        digest = sha256_of(url)
        text = path.read_text()
        updated, count = re.subn(pattern, rf"\g<1>{digest}", text)
        if count == 0:
            raise RuntimeError(f"{tool.name}: hash pattern missing in {path}")
        path.write_text(updated)


def main() -> int:
    changed = False
    for tool in TOOLS:
        try:
            latest = tool.latest()
            current = current_version(tool)
        except Exception as error:  # noqa: BLE001 - report and continue
            print(f"{tool.name}: SKIPPED ({error})")
            continue
        if latest == current:
            print(f"{tool.name}: {current} (current)")
            continue
        print(f"{tool.name}: {current} -> {latest}")
        bump(tool, latest)
        changed = True
    print("changes applied" if changed else "everything current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
