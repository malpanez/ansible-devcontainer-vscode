#!/usr/bin/env python3
"""The images a release tags, and the job matrices that run on them.

IMAGES below is the one list of what a release tags and which platforms each
image must have. release.yml and scan-release-images.yml read it from here
instead of keeping a copy each, because a matrix cannot call a script and a tag
push is the only thing that runs release.yml: this file can be tested, a
workflow's inline list cannot.

  names
      Every image, one per line: what release.yml's resolve job loops over.

  gate-outputs
      Reads the records release.yml's resolve job built (a JSON list with name,
      image and digest at least) from stdin. Prints, for $GITHUB_OUTPUT:
        images=      the records, each with its platforms
        smoke_legs=  one row per image and platform, with the runner to use

  ci-matrix --mode <verification|candidate> --images <json> --base <true|false>
      Prints, for $GITHUB_OUTPUT, the matrices of ci.yml's image jobs, from the
      images the changes job resolved (a JSON list, base not in it) and whether
      base is built:
        legs=            one row per image and platform the image job tests,
                         with the runner to use. Verification mode tests its
                         amd64 build of each image, and base in a job of its
                         own. Candidate mode tests every platform of every
                         image it built, base among them, as release.yml's
                         smoke does.
        builds=          candidate mode: each image but base, with the
                         platforms build-containers.yml publishes it for.
                         Empty in verification mode.
        base_platforms=  the platforms of base, for its candidate build.

  scan-targets --newest <tag> [--requested <tag>] --pytag <py3NN> --owner <owner>
      Prints, for $GITHUB_OUTPUT, targets= the matrix of the nightly scan. Every
      image of the release asked for, or of the newest one; and when no release
      was asked for, every other image and tag pair the templates pin, because
      that is what users open and a pin can lag behind the newest release. The
      pins are read from devcontainers/*/devcontainer*.json under --root. Those
      files alone: local-build/devcontainer.json builds its Dockerfile and pins
      nothing.

      A pin that cannot be scanned (not valid JSON, malformed, a rolling tag, an
      image that is not in IMAGES) prints ::warning:: and adds no leg. Failing
      would leave the newest release unscanned that night for something
      check-devcontainer-images.py fails in CI anyway.

Bad input exits 1 with ::error::. Usage errors exit 2.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType
from typing import Any

AMD64 = "linux/amd64"
ARM64 = "linux/arm64"
MULTI_ARCH = f"{AMD64},{ARM64}"

# The images release.yml tags, in release-notes order, with the platforms
# build-containers.yml builds each of them for. Every listed platform is
# required: an index that lost its arm64 manifest fails the release gate and the
# nightly scan instead of passing on amd64 alone. An image added there must be
# added here, or it is never released nor rescanned;
# tests/test_release_images.py fails until the two agree.
IMAGES: dict[str, str] = {
    "base": MULTI_ARCH,
    "ansible": MULTI_ARCH,
    "ansible-podman": MULTI_ARCH,
    "ansible-aws": MULTI_ARCH,
    "terraform": MULTI_ARCH,
    "terraform-aws": MULTI_ARCH,
    "golang": MULTI_ARCH,
    "latex": AMD64,
}
RUNNERS: dict[str, str] = {AMD64: "ubuntu-24.04", ARM64: "ubuntu-24.04-arm"}
BASE = "base"
PIN_GLOB = "devcontainers/*/devcontainer*.json"


def _load_pin_parser() -> ModuleType:
    """Load check-devcontainer-images.py, whose name cannot be imported."""
    path = Path(__file__).with_name("check-devcontainer-images.py")
    spec = importlib.util.spec_from_file_location("check_devcontainer_images", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    # A dataclass looks its own module up here while it is being defined.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _output(key: str, value: object) -> str:
    return f"{key}={json.dumps(value, separators=(',', ':'))}"


def gate_outputs(records: Any) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Give each record its platforms and list one smoke leg per platform."""
    if not isinstance(records, list) or not records:
        raise ValueError("expected a non-empty JSON list of image records")
    images: list[dict[str, Any]] = []
    legs: list[dict[str, str]] = []
    for record in records:
        name = record.get("name") if isinstance(record, dict) else None
        if name not in IMAGES:
            raise ValueError(f"{json.dumps(record)} does not name an image in IMAGES")
        images.append({**record, "platforms": IMAGES[name]})
        for platform in IMAGES[name].split(","):
            legs.append(
                {
                    "name": name,
                    "image": record["image"],
                    "digest": record["digest"],
                    "platform": platform,
                    "arch": platform.split("/")[1],
                    "runner": RUNNERS[platform],
                }
            )
    return images, legs


MODES = ("verification", "candidate")


def _ci_leg(name: str, platform: str) -> dict[str, str]:
    return {
        "image": name,
        "platform": platform,
        "arch": platform.split("/")[1],
        "runner": RUNNERS[platform],
    }


def ci_matrix(
    mode: str, images: Any, base: bool
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """List the image job's legs and, in candidate mode, the candidate builds."""
    if mode not in MODES:
        raise ValueError(f"mode {json.dumps(mode)} is not one of {', '.join(MODES)}")
    if not isinstance(images, list) or not all(isinstance(i, str) for i in images):
        raise ValueError(
            f"expected a JSON list of image names, got {json.dumps(images)}"
        )
    for name in images:
        if name not in IMAGES or name == BASE:
            raise ValueError(f"{json.dumps(name)} is not an image in IMAGES but base")
    if len(set(images)) != len(images):
        raise ValueError(f"{json.dumps(images)} names an image twice")
    if mode == "verification":
        return [_ci_leg(name, AMD64) for name in images], []
    names = ([BASE] if base else []) + images
    legs = [
        _ci_leg(name, platform)
        for name in names
        for platform in IMAGES[name].split(",")
    ]
    builds = [{"image": name, "platforms": IMAGES[name]} for name in images]
    return legs, builds


def read_pins(root: Path, owner: str) -> tuple[set[tuple[str, str]], list[str]]:
    """Return the (image name, tag) pairs the templates pin, and a warning per other."""
    parser = _load_pin_parser()
    prefix = f"ghcr.io/{owner}/devcontainer-"
    pins: set[tuple[str, str]] = set()
    warnings: list[str] = []
    for path in sorted(root.glob(PIN_GLOB)):
        rel = path.relative_to(root)
        try:
            config = parser.load_jsonc(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            warnings.append(f"{rel}: cannot be parsed, so it is not scanned: {exc}")
            continue
        value = config.get("image") if isinstance(config, dict) else None
        pin = parser.parse_image(value)
        if pin is None:
            warnings.append(
                f'{rel}: "image" is {json.dumps(value)}, not'
                " <registry>/<repository>:<tag>@sha256:<digest>, so it is not scanned"
            )
        elif parser.VERSION_TAG_RE.fullmatch(pin.tag) is None:
            warnings.append(
                f'{rel}: pins the tag "{pin.tag}", not a release version tag,'
                " so it is not scanned"
            )
        elif pin.repository.removeprefix(prefix) not in IMAGES:
            warnings.append(
                f"{rel}: pins {pin.repository}, which is not one of {prefix}<name>"
                " with <name> in IMAGES of scripts/release-images.py, so it is not"
                " scanned"
            )
        else:
            pins.add((pin.repository.removeprefix(prefix), pin.tag))
    return pins, warnings


def _target(name: str, tag: str, newest: str, version_tag: str) -> dict[str, str]:
    return {
        "name": name,
        "tag": tag,
        "version_tag": version_tag,
        "platforms": IMAGES[name],
        # The job's name: a red leg must say which version it is, unless it is the
        # one everyone assumes.
        "label": name if tag == newest else f"{name} {tag}",
    }


def scan_targets(
    newest: str, requested: str, pytag: str, pins: Iterable[tuple[str, str]]
) -> list[dict[str, str]]:
    """List the release's images, then the pins that are not the newest release.

    Only a release has a stream-tagged base, py<NN>-<tag>. A pin is an image and
    tag as written, so a template pinning the base would get a leg that fails
    to resolve, not a guess at the tag it meant.
    """
    tag = requested or newest
    targets = [
        _target(name, tag, newest, f"{pytag}-{tag}" if name == BASE else tag)
        for name in IMAGES
    ]
    order = list(IMAGES)
    for name, pinned_tag in sorted(
        set(pins), key=lambda pin: (order.index(pin[0]), pin[1])
    ):
        if pinned_tag != newest:
            targets.append(_target(name, pinned_tag, newest, pinned_tag))
    return targets


def _print_gate_outputs() -> int:
    try:
        images, legs = gate_outputs(json.load(sys.stdin))
    except (KeyError, ValueError) as exc:
        print(f"::error::release-images: {exc}", file=sys.stderr)
        return 1
    print(_output("images", images))
    print(_output("smoke_legs", legs))
    return 0


def _print_ci_matrix(args: argparse.Namespace) -> int:
    if args.base not in ("true", "false"):
        print(
            f"::error::release-images: --base is '{args.base}', not true or false",
            file=sys.stderr,
        )
        return 1
    try:
        legs, builds = ci_matrix(
            args.mode, json.loads(args.images), args.base == "true"
        )
    except ValueError as exc:
        print(f"::error::release-images: {exc}", file=sys.stderr)
        return 1
    print(_output("legs", legs))
    print(_output("builds", builds))
    print(f"base_platforms={IMAGES[BASE]}")
    return 0


def _print_scan_targets(args: argparse.Namespace) -> int:
    if not args.newest or not args.pytag or not args.owner:
        print(
            "::error::release-images: --newest, --pytag and --owner must not be empty"
            f" (newest='{args.newest}', pytag='{args.pytag}', owner='{args.owner}')",
            file=sys.stderr,
        )
        return 1
    pins: set[tuple[str, str]] = set()
    if not args.requested:
        pins, warnings = read_pins(Path(args.root).resolve(), args.owner)
        for warning in warnings:
            print(f"::warning::{warning}", file=sys.stderr)
    targets = scan_targets(args.newest, args.requested, args.pytag, pins)
    print(_output("targets", targets))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("names", help="Every image, one per line.")
    commands.add_parser("gate-outputs", help="Matrices of release.yml, from stdin.")
    ci = commands.add_parser("ci-matrix", help="Matrices of ci.yml's image jobs.")
    ci.add_argument("--mode", required=True, help="verification or candidate.")
    ci.add_argument(
        "--images", required=True, help="JSON list of the images, base not in it."
    )
    ci.add_argument("--base", required=True, help="true when base is built.")
    scan = commands.add_parser("scan-targets", help="Matrix of the nightly scan.")
    scan.add_argument("--newest", required=True, help="The newest release.")
    scan.add_argument(
        "--requested",
        default="",
        help="A release to scan instead, with no pins (default: empty).",
    )
    scan.add_argument("--pytag", required=True, help="The base's Python stream tag.")
    scan.add_argument(
        "--owner", required=True, help="The GHCR namespace of the images."
    )
    scan.add_argument(
        "--root",
        default=".",
        help="Repository root (default: the current directory).",
    )
    args = parser.parse_args(argv)

    if args.command == "names":
        print("\n".join(IMAGES))
        return 0
    if args.command == "gate-outputs":
        return _print_gate_outputs()
    if args.command == "ci-matrix":
        return _print_ci_matrix(args)
    return _print_scan_targets(args)


if __name__ == "__main__":
    sys.exit(main())
