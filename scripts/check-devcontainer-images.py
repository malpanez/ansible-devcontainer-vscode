#!/usr/bin/env python3
"""Check the images that the dev container templates and examples start from.

The templates under devcontainers/<stack>/, the active copy in .devcontainer/
and the examples open from a published image pinned to a release version tag
plus that tag's index digest (<image>:v1.4.0@sha256:...), so opening a dev
container is a pull instead of a local build. Version tags are the only tags
nothing moves or deletes: the nightly rebuild moves latest, main, the Python
stream tag and the sha- tag of the commit it rebuilds, and cleanup-ghcr.yml
deletes the digest they leave untagged two weeks later. Renovate moves tag and
digest together after each release.
local-build/devcontainer.json is the one variant per stack that builds the stack's
Dockerfile, for working on the image itself. It sits in a folder of its own
because the Dev Containers CLI only accepts a config file named
devcontainer.json, and VS Code only offers .devcontainer/<folder>/ ones.

Fails (exit 1) when:
  - a file is not valid JSON with comments;
  - a template or example has no "image", or one that is not
    <registry>/<repository>:<tag>@sha256:<digest>;
  - that tag is not a release version tag, v<major>.<minor>.<patch>;
  - a template other than local-build/devcontainer.json still has "build";
  - a template directory has no local-build/devcontainer.json, or that file differs
    from its devcontainer.json in anything but name/image/build (CI runs the
    build variant's lifecycle commands on behalf of the image variant), or its
    build.context is not ${localWorkspaceFolder} (the only value that reaches
    the repository root from devcontainers/<stack>/ and from .devcontainer/
    alike), or its Dockerfile is missing.
Unless --offline, it also asks the registry, and fails when a pinned digest
does not resolve, does not hash to itself, is not a multi-arch index, or has a
platform manifest that does not resolve, or when its version tag does not
resolve to exactly the pinned digest (the sha256 of the bytes the tag serves).
Version tags are never moved, so a mismatch means the pin is wrong or the tag
was moved. Usage errors exit 2.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TEMPLATE_GLOBS = (
    "devcontainers/*/devcontainer*.json",
    "devcontainers/*/local-build/devcontainer.json",
    ".devcontainer/devcontainer*.json",
    ".devcontainer/local-build/devcontainer.json",
)
EXAMPLE_GLOBS = ("examples/*/.devcontainer/*.json",)
IMAGE_VARIANT = "devcontainer.json"
BUILD_DIR = "local-build"
BUILD_CONTEXT = "${localWorkspaceFolder}"
VARIANT_KEYS = frozenset({"name", "image", "build"})
IMAGE_RE = re.compile(
    r"^(?P<repository>[a-z0-9.-]+(?::[0-9]+)?(?:/[a-z0-9._-]+)+)"
    r":(?P<tag>[A-Za-z0-9_][A-Za-z0-9_.-]{0,127})"
    r"@(?P<digest>sha256:[0-9a-f]{64})$"
)
VERSION_TAG_RE = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+")
REGISTRY_WORKERS = 6
REGISTRY_ATTEMPTS = 3
REGISTRY_RETRY_DELAY_SECONDS = 3.0
NOT_FOUND_MARKERS = (": not found", "manifest unknown")
INDEX_MEDIA_TYPES = frozenset(
    {
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
    }
)


class RegistryError(Exception):
    """The registry could not answer for a reference."""


@dataclass(frozen=True)
class PinnedImage:
    repository: str
    tag: str
    digest: str

    @property
    def ref(self) -> str:
        return f"{self.repository}:{self.tag}@{self.digest}"


def _strip_comments(text: str) -> str:
    out: list[str] = []
    i = 0
    in_string = False
    while i < len(text):
        char = text[i]
        if in_string:
            out.append(char)
            if char == "\\" and i + 1 < len(text):
                out.append(text[i + 1])
                i += 2
                continue
            if char == '"':
                in_string = False
            i += 1
            continue
        if char == '"':
            in_string = True
            out.append(char)
            i += 1
        elif text.startswith("//", i):
            end = text.find("\n", i)
            i = len(text) if end == -1 else end
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end == -1:
                raise ValueError("unterminated block comment")
            i = end + 2
        else:
            out.append(char)
            i += 1
    return "".join(out)


def _strip_trailing_commas(text: str) -> str:
    out: list[str] = []
    in_string = False
    escaped = False
    for i, char in enumerate(text):
        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == ",":
            rest = text[i + 1 :].lstrip()
            if rest[:1] in ("}", "]"):
                continue
        out.append(char)
    return "".join(out)


def load_jsonc(text: str) -> Any:
    """Parse JSON with comments and trailing commas, as devcontainer.json allows."""
    return json.loads(_strip_trailing_commas(_strip_comments(text)))


def parse_image(value: object) -> PinnedImage | None:
    """Split <registry>/<repository>:<tag>@sha256:<digest>; None for any other value.

    Only the shape: whether the tag is a release version tag is check_files' call,
    so that a rolling-tag pin gets a finding that says why it breaks.
    """
    if not isinstance(value, str):
        return None
    match = IMAGE_RE.match(value)
    if match is None:
        return None
    return PinnedImage(match["repository"], match["tag"], match["digest"])


def _discover(root: Path, patterns: Iterable[str]) -> list[Path]:
    found: set[Path] = set()
    for pattern in patterns:
        found.update(path for path in root.glob(pattern) if path.is_file())
    return sorted(found)


def _without_variant_keys(config: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in config.items() if key not in VARIANT_KEYS}


def _check_build_variant(
    path: Path, config: dict[str, Any], configs: dict[Path, Any]
) -> list[str]:
    findings: list[str] = []
    if "image" in config:
        findings.append('the build variant must not set "image"')
    build = config.get("build")
    if not isinstance(build, dict):
        findings.append('the build variant has no "build" object')
        return findings
    if build.get("context") != BUILD_CONTEXT:
        findings.append(
            f'build.context is {json.dumps(build.get("context"))}, not "{BUILD_CONTEXT}":'
            " a path relative to this file reaches the repository root from only one of"
            " devcontainers/<stack>/ and .devcontainer/"
        )
    dockerfile = build.get("dockerfile")
    if not isinstance(dockerfile, str) or not (path.parent / dockerfile).is_file():
        findings.append(
            f"build.dockerfile {json.dumps(dockerfile)} is not a file relative to it"
        )
    sibling = path.parent.parent / IMAGE_VARIANT
    sibling_config = configs.get(sibling)
    if isinstance(sibling_config, dict):
        if _without_variant_keys(config) != _without_variant_keys(sibling_config):
            findings.append(
                f"differs from ../{IMAGE_VARIANT} in more than name/image/build;"
                " CI proves the lifecycle of the image variant through this file"
            )
    elif not sibling.is_file():
        findings.append(f"has no ../{IMAGE_VARIANT} to build the same container as")
    return findings


def _is_build_variant(path: Path) -> bool:
    return path.name == IMAGE_VARIANT and path.parent.name == BUILD_DIR


def check_files(root: Path) -> tuple[list[str], list[PinnedImage]]:
    """Check every template and example; return findings and the pinned images."""
    findings: list[str] = []
    images: list[PinnedImage] = []
    templates = _discover(root, TEMPLATE_GLOBS)
    examples = _discover(root, EXAMPLE_GLOBS)

    configs: dict[Path, Any] = {}
    for path in templates + examples:
        try:
            configs[path] = load_jsonc(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            findings.append(f"{path.relative_to(root)}: cannot be parsed: {exc}")

    for path, config in configs.items():
        rel = path.relative_to(root)
        if not isinstance(config, dict):
            findings.append(f"{rel}: is not a JSON object")
            continue
        if path in templates and _is_build_variant(path):
            findings.extend(
                f"{rel}: {message}"
                for message in _check_build_variant(path, config, configs)
            )
            continue
        if "build" in config:
            findings.append(
                f'{rel}: still builds locally ("build"); templates start from the'
                f" published image, and only {BUILD_DIR}/{IMAGE_VARIANT} builds the"
                " Dockerfile"
            )
        image = parse_image(config.get("image"))
        if image is None:
            findings.append(
                f'{rel}: "image" is {json.dumps(config.get("image"))}, not'
                " <registry>/<repository>:<tag>@sha256:<digest>"
            )
            continue
        if VERSION_TAG_RE.fullmatch(image.tag) is None:
            # Not sent to the registry: the pin is wrong whatever it answers today.
            findings.append(
                f'{rel}: pins the tag "{image.tag}", not a release version tag'
                " v<major>.<minor>.<patch>: the nightly rebuild moves the other tags"
                " (latest, main, py3xx, the sha- tag of the commit it rebuilds) and"
                " cleanup-ghcr.yml deletes the digest they leave untagged two weeks"
                " later, so the pin stops pulling"
            )
            continue
        images.append(image)

    stack_dirs = {path.parent for path in templates if not _is_build_variant(path)}
    for directory in sorted(stack_dirs):
        if (directory / IMAGE_VARIANT) in configs and not (
            directory / BUILD_DIR / IMAGE_VARIANT
        ).is_file():
            findings.append(
                f"{directory.relative_to(root)}: has no {BUILD_DIR}/{IMAGE_VARIANT},"
                " so its Dockerfile cannot be opened as a dev container nor tested by CI"
            )
    return findings, images


def inspect_raw(ref: str) -> bytes:
    """Return the manifest bytes the registry serves for ref.

    A reference the registry does not have fails at once. Any other failure (a
    timeout, a reset, a 5xx) is tried again: GHCR once answered an i/o timeout
    that a rerun did not repeat, and would otherwise fail the check for an image
    that is there.
    """
    detail = ""
    for attempt in range(1, REGISTRY_ATTEMPTS + 1):
        try:
            proc = subprocess.run(
                ["docker", "buildx", "imagetools", "inspect", "--raw", ref],
                capture_output=True,
                check=False,
            )
        except OSError as exc:
            raise RegistryError(f"cannot run docker: {exc}") from exc
        if proc.returncode == 0:
            return proc.stdout
        detail = proc.stderr.decode("utf-8", errors="replace").strip()
        detail = detail or f"docker exited {proc.returncode}"
        if any(marker in detail for marker in NOT_FOUND_MARKERS):
            break
        if attempt < REGISTRY_ATTEMPTS:
            time.sleep(REGISTRY_RETRY_DELAY_SECONDS * attempt)
    raise RegistryError(detail)


def _platforms(document: dict[str, Any]) -> dict[str, str]:
    platforms: dict[str, str] = {}
    for entry in document.get("manifests") or []:
        platform = entry.get("platform") or {}
        os_name = platform.get("os", "unknown")
        arch = platform.get("architecture", "unknown")
        if os_name == "unknown" or arch == "unknown":
            continue
        name = f"{os_name}/{arch}"
        if platform.get("variant"):
            name = f"{name}/{platform['variant']}"
        platforms[name] = entry.get("digest", "")
    return platforms


def _load_manifest(raw: bytes) -> dict[str, Any]:
    try:
        document = json.loads(raw)
    except ValueError as exc:
        raise RegistryError(f"the registry answer is not JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise RegistryError("the registry answer is not a JSON object")
    return document


def _sha256(raw: bytes) -> str:
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _check_tag(image: PinnedImage) -> list[str]:
    try:
        raw = inspect_raw(f"{image.repository}:{image.tag}")
    except RegistryError as exc:
        return [f"{image.ref}: the tag {image.tag} does not resolve: {exc}"]
    tagged = _sha256(raw)
    if tagged == image.digest:
        return []
    message = (
        f"{image.ref}: {image.repository}:{image.tag} resolves to {tagged}, not"
        " the pinned digest; version tags are never moved, so the pin is wrong"
        " or the tag was moved"
    )
    return [message]


def check_registry(image: PinnedImage) -> tuple[list[str], list[str]]:
    """Ask the registry about one pinned image; return findings and its platforms.

    The pinned digest must resolve, hash to itself, be a multi-arch index whose
    platform manifests all resolve, and be exactly what the version tag serves.
    The tag is asked even when the digest does not resolve: its answer is the
    digest the pin should have.
    """
    findings: list[str] = []
    pinned = f"{image.repository}@{image.digest}"
    try:
        raw = inspect_raw(pinned)
        document = _load_manifest(raw)
    except RegistryError as exc:
        findings.append(f"{image.ref}: the pinned digest does not resolve: {exc}")
        return findings + _check_tag(image), []

    served = _sha256(raw)
    if served != image.digest:
        findings.append(f"{image.ref}: the registry served {served} for this digest")
    findings.extend(_check_tag(image))
    if document.get("mediaType") not in INDEX_MEDIA_TYPES:
        findings.append(
            f"{image.ref}: is a single-platform manifest"
            f" ({document.get('mediaType')}), not a multi-arch index; pin the index"
            f" digest of {image.repository}:{image.tag}"
        )
        return findings, []

    platforms = _platforms(document)
    if not platforms:
        findings.append(f"{image.ref}: the index lists no platform image")
    for platform, child in sorted(platforms.items()):
        try:
            _load_manifest(inspect_raw(f"{image.repository}@{child}"))
        except RegistryError as exc:
            findings.append(
                f"{image.ref}: the {platform} manifest {child} does not resolve: {exc}"
            )
    return findings, sorted(platforms)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root (default: the current directory).",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Check the files only; do not ask the registry.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not (root / "devcontainers").is_dir():
        print(f"::error::{root} has no devcontainers/ directory", file=sys.stderr)
        return 2

    findings, images = check_files(root)
    if not args.offline:
        unique = sorted(set(images), key=lambda item: item.ref)
        with ThreadPoolExecutor(max_workers=REGISTRY_WORKERS) as pool:
            results = list(pool.map(check_registry, unique))
        for image, (image_findings, platforms) in zip(unique, results, strict=True):
            findings.extend(image_findings)
            if not image_findings:
                print(f"ok {image.ref} [{', '.join(platforms)}]")

    for finding in findings:
        print(f"::error::{finding}", file=sys.stderr)
    if findings:
        return 1
    scope = "files" if args.offline else "files and registry"
    print(f"All dev container images check out ({scope}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
