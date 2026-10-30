#!/usr/bin/env python3
"""Check a dev container image's size against its budget.

The budgets are in .github/image-size-budgets.json, one entry per published
image (devcontainer-<name>, keyed by <name>), in MiB (1024 * 1024 bytes).

  local --image <docker ref> --name <name>
      The pull request gate (ci.yml, devcontainer-build). Compares the size of
      an image in the local Docker engine, `docker image inspect` .Size, with
      max_uncompressed_mib. Over budget prints ::error:: and exits 1.

  registry --ref <repository>@<digest> --name <name> [--platform linux/amd64]
      The publish report (build-containers.yml). Sums config and layer sizes of
      the platform's manifest in the registry, the compressed bytes a pull
      downloads, and compares the sum with max_compressed_mib. Over budget
      prints ::warning:: and still exits 0: the pull request gate is the one
      that blocks, and a nightly rebuild that grew by OS updates alone must not
      hold back the security fixes it carries. A ref that is a single image
      manifest, not an index, is summed as it is.

Both modes append a table (image, metric, size, budget, headroom, verdict) to
$GITHUB_STEP_SUMMARY when it is set. Headroom is the share of the budget left,
negative when over.

Both fail closed, with exit 2, when the size cannot be judged: a name with no
budget (a new image must get one), a budgets file that cannot be read or is
ill-formed, a docker or registry error (registry calls are tried three times
first), or a Docker engine on the containerd image store. There .Size is the
compressed content plus the disk usage of the unpacked snapshots, 1.33 to
1.45 times the classic figure for the v2.0.0 images. The budgets are
calibrated on the classic overlay2 store of GitHub's ubuntu runners, where
.Size is the sum of the files in the image's layers, so a runner moved to the
containerd store fails here, with the reason, instead of as a 40% jump in
every image. Usage errors exit 2 too.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_BUDGETS = (
    Path(__file__).resolve().parents[1] / ".github/image-size-budgets.json"
)
MIB = 1024 * 1024
EXIT_OVER_BUDGET = 1
EXIT_UNJUDGED = 2
BUDGET_FIELDS = frozenset({"max_uncompressed_mib", "max_compressed_mib", "reason"})
REF_RE = re.compile(
    r"^(?P<repository>[a-z0-9.-]+(?::[0-9]+)?(?:/[a-z0-9._-]+)+)"
    r"@(?P<digest>sha256:[0-9a-f]{64})$"
)
DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}")
PLATFORM_RE = re.compile(r"(?P<os>[a-z0-9]+)/(?P<arch>[a-z0-9_]+)")
BYTE_COUNT_RE = re.compile(r"[0-9]+")
CONTAINERD_SNAPSHOTTER = "io.containerd.snapshotter"
REGISTRY_ATTEMPTS = 3
REGISTRY_RETRY_DELAY_SECONDS = 3.0
NOT_FOUND_MARKERS = (": not found", "manifest unknown")


class CheckError(Exception):
    """The size could not be judged."""


class RegistryError(CheckError):
    """The registry could not answer for a reference."""


@dataclass(frozen=True)
class Budget:
    max_uncompressed_mib: int
    max_compressed_mib: int
    reason: str


@dataclass(frozen=True)
class Measurement:
    image: str
    metric: str
    size: int
    budget_mib: int

    @property
    def budget(self) -> int:
        return self.budget_mib * MIB

    @property
    def over(self) -> bool:
        return self.size > self.budget

    @property
    def headroom_percent(self) -> float:
        return (self.budget - self.size) / self.budget * 100


def _mib(size: int) -> str:
    return f"{size / MIB:.1f} MiB"


def _is_positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def load_budgets(path: Path) -> dict[str, Budget]:
    """Read and validate the whole budgets file; any defect is a CheckError."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise CheckError(f"cannot read the budgets file {path}: {exc}") from exc
    images = document.get("images") if isinstance(document, dict) else None
    if not isinstance(images, dict) or not images:
        raise CheckError(f'{path}: has no non-empty "images" object')

    budgets: dict[str, Budget] = {}
    for name, entry in images.items():
        if not isinstance(entry, dict) or set(entry) != BUDGET_FIELDS:
            raise CheckError(
                f"{path}: images.{name} must have exactly the keys"
                f" {', '.join(sorted(BUDGET_FIELDS))}"
            )
        for field in ("max_uncompressed_mib", "max_compressed_mib"):
            if not _is_positive_int(entry[field]):
                raise CheckError(
                    f"{path}: images.{name}.{field} is {json.dumps(entry[field])},"
                    " not a positive integer"
                )
        reason = entry["reason"]
        if not isinstance(reason, str) or not reason.strip():
            raise CheckError(f"{path}: images.{name}.reason must say why")
        budgets[name] = Budget(
            entry["max_uncompressed_mib"], entry["max_compressed_mib"], reason
        )
    return budgets


def budget_for(budgets: dict[str, Budget], name: str, path: Path) -> Budget:
    budget = budgets.get(name)
    if budget is None:
        raise CheckError(
            f"{path} has no budget for '{name}'. Every published image needs one:"
            " add it under images with both limits and a reason."
        )
    return budget


def _docker(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(["docker", *args], capture_output=True, check=False)
    except OSError as exc:
        raise CheckError(f"cannot run docker: {exc}") from exc


def _detail(proc: subprocess.CompletedProcess[bytes]) -> str:
    detail = proc.stderr.decode("utf-8", errors="replace").strip()
    return detail or f"docker exited {proc.returncode}"


def check_image_store() -> None:
    """Refuse an engine whose .Size is not the classic sum of layer files."""
    proc = _docker(["info", "--format", "{{json .DriverStatus}}"])
    if proc.returncode != 0:
        raise CheckError(f"docker info failed: {_detail(proc)}")
    try:
        status = json.loads(proc.stdout or b"null")
    except ValueError as exc:
        raise CheckError(f"docker info gave no readable driver status: {exc}") from exc
    if status is None:
        return
    if not isinstance(status, list):
        raise CheckError(
            f"docker info gave a driver status that is not a list: {status}"
        )
    for pair in status:
        if (
            isinstance(pair, list)
            and len(pair) == 2
            and pair[0] == "driver-type"
            and str(pair[1]).startswith(CONTAINERD_SNAPSHOTTER)
        ):
            raise CheckError(
                f"docker uses the containerd image store ({pair[1]}), where .Size"
                " counts the compressed content plus the unpacked snapshots' disk"
                " usage, 1.33-1.45x the classic overlay2 figure the budgets are"
                " calibrated on. Measure on a classic store (GitHub's ubuntu"
                " runners), or recalibrate every max_uncompressed_mib."
            )


def local_size(image: str) -> int:
    proc = _docker(["image", "inspect", "--format", "{{.Size}}", image])
    if proc.returncode != 0:
        raise CheckError(f"docker image inspect {image} failed: {_detail(proc)}")
    text = proc.stdout.decode("utf-8", errors="replace").strip()
    if BYTE_COUNT_RE.fullmatch(text) is None:
        raise CheckError(
            f"docker image inspect {image} gave {text!r} as its size, not a byte count"
        )
    return int(text)


def inspect_raw(ref: str) -> bytes:
    """Return the manifest bytes the registry serves for ref.

    A reference the registry does not have fails at once; any other failure
    (a timeout, a reset, a 5xx) is tried again, as check-devcontainer-images.py
    does.
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
        detail = _detail(proc)
        if any(marker in detail for marker in NOT_FOUND_MARKERS):
            break
        if attempt < REGISTRY_ATTEMPTS:
            time.sleep(REGISTRY_RETRY_DELAY_SECONDS * attempt)
    raise RegistryError(f"{ref}: {detail}")


def _sha256(raw: bytes) -> str:
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _fetch(repository: str, digest: str) -> dict[str, Any]:
    """Fetch repository@digest and check that the bytes hash to the digest."""
    ref = f"{repository}@{digest}"
    raw = inspect_raw(ref)
    served = _sha256(raw)
    if served != digest:
        raise RegistryError(f"the registry served {served} for {ref}")
    try:
        document = json.loads(raw)
    except ValueError as exc:
        raise RegistryError(f"{ref}: the registry answer is not JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise RegistryError(f"{ref}: the registry answer is not a JSON object")
    return document


def _platform_digest(document: dict[str, Any], ref: str, wanted: re.Match[str]) -> str:
    """Pick the one manifest of the wanted platform in an index.

    As scripts/resolve-platform-manifest.sh does: os and architecture must
    match, and attestation manifests (unknown/unknown) never do.
    """
    platform = wanted[0]
    matches = [
        entry.get("digest")
        for entry in document["manifests"]
        if isinstance(entry, dict)
        and isinstance(entry.get("platform"), dict)
        and entry["platform"].get("os") == wanted["os"]
        and entry["platform"].get("architecture") == wanted["arch"]
    ]
    if not matches:
        raise RegistryError(f"{ref} holds no {platform} manifest")
    if len(matches) > 1:
        raise RegistryError(f"{ref} holds {len(matches)} {platform} manifests")
    digest = matches[0]
    if not isinstance(digest, str) or DIGEST_RE.fullmatch(digest) is None:
        raise RegistryError(f"{ref} lists a malformed {platform} digest {digest!r}")
    return digest


def _compressed_size(manifest: dict[str, Any], ref: str) -> int:
    config = manifest.get("config")
    layers = manifest.get("layers")
    if not isinstance(config, dict) or not isinstance(layers, list):
        raise RegistryError(f"{ref} is neither an image index nor an image manifest")
    sizes = [config.get("size")]
    sizes.extend(
        layer.get("size") if isinstance(layer, dict) else None for layer in layers
    )
    if not all(isinstance(size, int) and not isinstance(size, bool) for size in sizes):
        raise RegistryError(
            f"{ref} lists a config or layer size that is not an integer"
        )
    if any(size < 0 for size in sizes):
        raise RegistryError(f"{ref} lists a negative config or layer size")
    return sum(sizes)


def registry_size(ref: str, platform: str) -> tuple[str, str, int]:
    """Return the manifest ref measured, the metric's label and its size."""
    match = REF_RE.match(ref)
    if match is None:
        raise CheckError(
            f"--ref {ref!r} is not <registry>/<repository>@sha256:<digest>"
        )
    wanted = PLATFORM_RE.fullmatch(platform)
    if wanted is None:
        raise CheckError(f"--platform {platform!r} is not <os>/<arch>")
    repository = match["repository"]
    document = _fetch(repository, match["digest"])
    if isinstance(document.get("manifests"), list):
        digest = _platform_digest(document, ref, wanted)
        measured = f"{repository}@{digest}"
        manifest = _fetch(repository, digest)
        metric = f"compressed, {platform}"
    else:
        measured = ref
        manifest = document
        metric = "compressed, single-platform manifest"
    return measured, metric, _compressed_size(manifest, measured)


def report(measurement: Measurement, name: str) -> None:
    verdict = "over budget" if measurement.over else "within budget"
    row = (
        f"| `{measurement.image}` | `{name}` | {measurement.metric}"
        f" | {_mib(measurement.size)} | {measurement.budget_mib} MiB"
        f" | {measurement.headroom_percent:.1f}% | {verdict} |"
    )
    print(
        f"{measurement.image} ({measurement.metric}): {_mib(measurement.size)}"
        f" ({measurement.size} bytes), budget {measurement.budget_mib} MiB,"
        f" headroom {measurement.headroom_percent:.1f}%: {verdict}",
        flush=True,
    )
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary:
        return
    table = (
        "| Image | Name | Metric | Size | Budget | Headroom | Verdict |\n"
        "| --- | --- | --- | ---: | ---: | ---: | --- |\n"
        f"{row}\n\n"
    )
    try:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(table)
    except OSError as exc:
        raise CheckError(f"cannot write the step summary {summary}: {exc}") from exc


def check_local(image: str, name: str, budget: Budget, path: Path) -> int:
    check_image_store()
    measurement = Measurement(
        image,
        "uncompressed, docker image inspect",
        local_size(image),
        budget.max_uncompressed_mib,
    )
    report(measurement, name)
    if not measurement.over:
        return 0
    print(
        f"::error::{image} is {_mib(measurement.size)} uncompressed,"
        f" {_mib(measurement.size - measurement.budget)} over the"
        f" {budget.max_uncompressed_mib} MiB budget of '{name}' in {path}. Shrink"
        " the image, or raise max_uncompressed_mib in a reviewed change to that"
        " file that says what grew and why.",
        file=sys.stderr,
    )
    return EXIT_OVER_BUDGET


def check_registry(
    ref: str, platform: str, name: str, budget: Budget, path: Path
) -> int:
    measured, metric, size = registry_size(ref, platform)
    measurement = Measurement(measured, metric, size, budget.max_compressed_mib)
    report(measurement, name)
    if measurement.over:
        print(
            f"::warning::{measured} downloads {_mib(size)} compressed,"
            f" {_mib(size - measurement.budget)} over the"
            f" {budget.max_compressed_mib} MiB budget of '{name}' in {path}. Report"
            " only, the publish goes on: find what grew, and raise"
            " max_compressed_mib only in a reviewed change that says why.",
            file=sys.stderr,
        )
    return 0


def _parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--name",
        required=True,
        help="Budget key: the image name without devcontainer-, e.g. ansible-aws.",
    )
    common.add_argument(
        "--budgets",
        type=Path,
        default=DEFAULT_BUDGETS,
        help="Budgets file (default: .github/image-size-budgets.json of this repository).",
    )
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    modes = parser.add_subparsers(dest="mode", required=True)
    local = modes.add_parser(
        "local", parents=[common], help="Gate a local image on max_uncompressed_mib."
    )
    local.add_argument(
        "--image", required=True, help="Image in the local Docker engine."
    )
    registry = modes.add_parser(
        "registry",
        parents=[common],
        help="Report a pushed image against max_compressed_mib (always exits 0 on size).",
    )
    registry.add_argument(
        "--ref", required=True, help="<registry>/<repository>@sha256:<digest>."
    )
    registry.add_argument(
        "--platform",
        default="linux/amd64",
        help="<os>/<arch> to measure in an index (default: linux/amd64).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        budget = budget_for(load_budgets(args.budgets), args.name, args.budgets)
        if args.mode == "local":
            return check_local(args.image, args.name, budget, args.budgets)
        return check_registry(args.ref, args.platform, args.name, budget, args.budgets)
    except CheckError as exc:
        print(f"::error::check-image-size: {exc}", file=sys.stderr)
        return EXIT_UNJUDGED


if __name__ == "__main__":
    sys.exit(main())
