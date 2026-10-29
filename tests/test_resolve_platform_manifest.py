import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "resolve-platform-manifest.sh"

IMAGE = "ghcr.io/example/devcontainer-base"
INDEX_DIGEST = "sha256:" + "0" * 64
AMD64 = "sha256:" + "a" * 64
ARM64 = "sha256:" + "b" * 64
ARM64_OTHER = "sha256:" + "c" * 64
INHERITED = (
    "GITHUB_OUTPUT",
    "IMAGE",
    "DIGEST",
    "PLATFORM",
    "REQUIRED",
    "FAKE_DOCKER_INDEX",
    "FAKE_DOCKER_LOG",
    "FAKE_DOCKER_FAIL",
)

FAKE_DOCKER = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "${FAKE_DOCKER_LOG}"
if [[ -n "${FAKE_DOCKER_FAIL:-}" ]]; then
  echo "ERROR: fake registry failure" >&2
  exit 1
fi
cat "${FAKE_DOCKER_INDEX}"
"""


def _platform(digest: object, os_name: str, arch: str) -> dict[str, object]:
    return {
        "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "digest": digest,
        "size": 1234,
        "platform": {"architecture": arch, "os": os_name},
    }


def _attestation(digest: str, subject: str) -> dict[str, object]:
    entry = _platform(digest, "unknown", "unknown")
    entry["annotations"] = {
        "vnd.docker.reference.digest": subject,
        "vnd.docker.reference.type": "attestation-manifest",
    }
    return entry


def _index(*manifests: dict[str, object]) -> str:
    return json.dumps(
        {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.index.v1+json",
            "manifests": list(manifests),
        }
    )


MULTI_ARCH = _index(
    _platform(AMD64, "linux", "amd64"),
    _platform(ARM64, "linux", "arm64"),
    _attestation("sha256:" + "d" * 64, AMD64),
    _attestation("sha256:" + "e" * 64, ARM64),
)
AMD64_ONLY = _index(
    _platform(AMD64, "linux", "amd64"),
    _attestation("sha256:" + "d" * 64, AMD64),
)


def _run(
    tmp_path: Path,
    index: str = MULTI_ARCH,
    *,
    github: bool = True,
    docker_fails: bool = False,
    **env: str,
) -> subprocess.CompletedProcess[str]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(exist_ok=True)
    docker = fake_bin / "docker"
    docker.write_text(FAKE_DOCKER, encoding="utf-8")
    docker.chmod(docker.stat().st_mode | stat.S_IXUSR)
    (tmp_path / "index.json").write_text(index, encoding="utf-8")

    base = {key: value for key, value in os.environ.items() if key not in INHERITED}
    base["PATH"] = f"{fake_bin}:{base['PATH']}"
    base["FAKE_DOCKER_INDEX"] = str(tmp_path / "index.json")
    base["FAKE_DOCKER_LOG"] = str(tmp_path / "docker.log")
    if docker_fails:
        base["FAKE_DOCKER_FAIL"] = "1"
    if github:
        base["GITHUB_OUTPUT"] = str(tmp_path / "output")
    inputs = {
        "IMAGE": IMAGE,
        "DIGEST": INDEX_DIGEST,
        "PLATFORM": "linux/arm64",
        "REQUIRED": "true",
    }
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=tmp_path,
        env={**base, **inputs, **env},
        capture_output=True,
        text=True,
        check=False,
    )


def _output(tmp_path: Path) -> list[str]:
    path = tmp_path / "output"
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def _docker_calls(tmp_path: Path) -> list[str]:
    path = tmp_path / "docker.log"
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def test_resolve_platform_manifest_one_arm64_entry_writes_its_ref(
    tmp_path: Path,
) -> None:
    proc = _run(tmp_path)

    assert proc.returncode == 0, proc.stderr
    assert _output(tmp_path) == [f"ref={IMAGE}@{ARM64}"]
    assert _docker_calls(tmp_path) == [
        f"buildx imagetools inspect --raw {IMAGE}@{INDEX_DIGEST}"
    ]
    assert f"linux/arm64: {IMAGE}@{ARM64}" in proc.stdout


def test_resolve_platform_manifest_amd64_platform_writes_amd64_ref(
    tmp_path: Path,
) -> None:
    proc = _run(tmp_path, PLATFORM="linux/amd64")

    assert proc.returncode == 0, proc.stderr
    assert _output(tmp_path) == [f"ref={IMAGE}@{AMD64}"]


def test_resolve_platform_manifest_attestation_manifests_are_ignored(
    tmp_path: Path,
) -> None:
    index = _index(
        _attestation("sha256:" + "d" * 64, ARM64),
        _platform(ARM64, "linux", "arm64"),
        _attestation("sha256:" + "e" * 64, ARM64),
    )
    proc = _run(tmp_path, index)

    assert proc.returncode == 0, proc.stderr
    assert _output(tmp_path) == [f"ref={IMAGE}@{ARM64}"]


def test_resolve_platform_manifest_amd64_only_not_required_writes_empty_ref(
    tmp_path: Path,
) -> None:
    proc = _run(tmp_path, AMD64_ONLY, REQUIRED="false")

    assert proc.returncode == 0, proc.stderr
    assert _output(tmp_path) == ["ref="]
    assert "::notice::" in proc.stdout
    assert "holds no linux/arm64 manifest" in proc.stdout


def test_resolve_platform_manifest_amd64_only_required_exits_1(
    tmp_path: Path,
) -> None:
    proc = _run(tmp_path, AMD64_ONLY, REQUIRED="true")

    assert proc.returncode == 1
    assert "::error::" in proc.stderr
    assert "holds no linux/arm64 manifest" in proc.stderr
    assert _output(tmp_path) == []


@pytest.mark.parametrize("required", ["true", "false"])
def test_resolve_platform_manifest_two_arm64_entries_exits_1(
    tmp_path: Path, required: str
) -> None:
    index = _index(
        _platform(AMD64, "linux", "amd64"),
        _platform(ARM64, "linux", "arm64"),
        _platform(ARM64_OTHER, "linux", "arm64"),
    )
    proc = _run(tmp_path, index, REQUIRED=required)

    assert proc.returncode == 1
    assert "holds 2 linux/arm64 manifests" in proc.stderr
    assert _output(tmp_path) == []


@pytest.mark.parametrize(
    "digest",
    ["sha256:abc", "sha512:" + "b" * 64, "sha256:" + "B" * 64, None, ""],
    ids=["short", "algorithm", "uppercase", "null", "empty"],
)
def test_resolve_platform_manifest_malformed_manifest_digest_exits_1(
    tmp_path: Path, digest: object
) -> None:
    index = _index(
        _platform(AMD64, "linux", "amd64"),
        _platform(digest, "linux", "arm64"),
    )
    proc = _run(tmp_path, index)

    assert proc.returncode == 1
    assert "malformed linux/arm64 manifest digest" in proc.stderr
    assert _output(tmp_path) == []


@pytest.mark.parametrize("required", ["true", "false"])
def test_resolve_platform_manifest_imagetools_failure_exits_1(
    tmp_path: Path, required: str
) -> None:
    proc = _run(tmp_path, docker_fails=True, REQUIRED=required)

    assert proc.returncode == 1
    assert "fake registry failure" in proc.stderr
    assert f"could not read {IMAGE}@{INDEX_DIGEST}" in proc.stderr
    assert _output(tmp_path) == []


@pytest.mark.parametrize(
    "answer",
    [
        "",
        "not json",
        "null",
        "[]",
        json.dumps({"schemaVersion": 2, "config": {}, "layers": []}),
    ],
    ids=["empty", "text", "null", "array", "single-manifest"],
)
@pytest.mark.parametrize("required", ["true", "false"])
def test_resolve_platform_manifest_answer_not_an_index_exits_1(
    tmp_path: Path, answer: str, required: str
) -> None:
    proc = _run(tmp_path, answer, REQUIRED=required)

    assert proc.returncode == 1
    assert "is not a readable image index" in proc.stderr
    assert _output(tmp_path) == []


def test_resolve_platform_manifest_outside_github_prints_ref(tmp_path: Path) -> None:
    proc = _run(tmp_path, github=False)

    assert proc.returncode == 0, proc.stderr
    assert f"ref={IMAGE}@{ARM64}" in proc.stdout.splitlines()


@pytest.mark.parametrize(
    ("variable", "value", "message"),
    [
        ("IMAGE", "", "IMAGE is empty"),
        ("DIGEST", "", "is not sha256:<64 lowercase hex>"),
        ("DIGEST", "sha256:abc", "is not sha256:<64 lowercase hex>"),
        ("DIGEST", "latest", "is not sha256:<64 lowercase hex>"),
        ("DIGEST", f"{INDEX_DIGEST}\n", "is not sha256:<64 lowercase hex>"),
        ("REQUIRED", "", "REQUIRED must be true or false"),
        ("REQUIRED", "yes", "REQUIRED must be true or false"),
        ("REQUIRED", "True", "REQUIRED must be true or false"),
        ("PLATFORM", "", "is not <os>/<arch>"),
        ("PLATFORM", "arm64", "is not <os>/<arch>"),
        ("PLATFORM", "linux/arm64/v8", "is not <os>/<arch>"),
    ],
)
def test_resolve_platform_manifest_bad_input_is_a_usage_error(
    tmp_path: Path, variable: str, value: str, message: str
) -> None:
    proc = _run(tmp_path, **{variable: value})

    assert proc.returncode == 2
    assert message in proc.stderr
    assert _output(tmp_path) == []
    assert _docker_calls(tmp_path) == []
