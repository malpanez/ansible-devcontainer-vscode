import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "assert-image-id.sh"

BUILT = "sha256:" + "a" * 64
OTHER = "sha256:" + "b" * 64

# Answers `docker image inspect --format '{{.Id}}' -- IMAGE` with FAKE_ID, or
# fails as docker does for an image it does not have.
FAKE_DOCKER = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "${FAKE_STATE}/docker.log"
if [[ -z "${FAKE_ID}" ]]; then
  echo "Error response from daemon: No such image: ${!#}" >&2
  exit 1
fi
printf '%s\\n' "${FAKE_ID}"
"""


@pytest.fixture
def fake(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    docker.write_text(FAKE_DOCKER)
    docker.chmod(0o755)
    return tmp_path


def _run(
    fake: Path, *args: str, image_id: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        env={
            **os.environ,
            "PATH": f"{fake / 'bin'}{os.pathsep}{os.environ['PATH']}",
            "FAKE_STATE": str(fake),
            "FAKE_ID": image_id,
        },
    )


def test_the_image_the_job_built_passes(fake: Path) -> None:
    proc = _run(fake, "devcontainer-golang:ci", BUILT, image_id=BUILT)

    assert proc.returncode == 0, proc.stderr
    assert BUILT in proc.stdout
    assert (fake / "docker.log").read_text().split() == [
        "image",
        "inspect",
        "--format",
        "{{.Id}}",
        "--",
        "devcontainer-golang:ci",
    ]


def test_another_image_under_the_tag_fails(fake: Path) -> None:
    proc = _run(fake, "devcontainer-golang:ci", BUILT, image_id=OTHER)

    assert proc.returncode == 1
    assert f"::error::devcontainer-golang:ci is {OTHER}" in proc.stderr
    assert BUILT in proc.stderr


def test_a_missing_image_fails(fake: Path) -> None:
    proc = _run(fake, "devcontainer-golang:ci", BUILT)

    assert proc.returncode == 1
    assert "::error::devcontainer-golang:ci is not in the local image store" in (
        proc.stderr
    )


@pytest.mark.parametrize(
    "args",
    [(), ("devcontainer-golang:ci",), ("devcontainer-golang:ci", ""), ("", BUILT)],
)
def test_usage_errors_exit_2(fake: Path, args: tuple[str, ...]) -> None:
    proc = _run(fake, *args, image_id=BUILT)

    assert proc.returncode == 2
    assert not (fake / "docker.log").exists()
