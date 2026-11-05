import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "scenarios" / "run-latex-cv.sh"

# Logs every call, one per line; `image inspect` fails when FAKE_MISSING_IMAGE
# is set, everything else succeeds.
FAKE_DOCKER = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "${FAKE_STATE}/docker.log"
if [[ "$1 $2" == "image inspect" && -n "${FAKE_MISSING_IMAGE:-}" ]]; then
  exit 1
fi
exit 0
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
    fake: Path, *args: str, missing_image: bool = False
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "PATH": f"{fake / 'bin'}{os.pathsep}{os.environ['PATH']}",
        "FAKE_STATE": str(fake),
    }
    if missing_image:
        env["FAKE_MISSING_IMAGE"] = "1"
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _calls(fake: Path) -> list[str]:
    log = fake / "docker.log"
    return log.read_text().splitlines() if log.exists() else []


def test_an_existing_image_is_used_as_it_is(fake: Path) -> None:
    proc = _run(fake, "--image", "devcontainer-latex:ci")

    assert proc.returncode == 0, proc.stderr
    calls = _calls(fake)
    assert calls[0] == "image inspect -- devcontainer-latex:ci"
    runs = [call for call in calls if call.startswith("run ")]
    assert len(runs) == 2
    assert all("devcontainer-latex:ci" in call for call in runs)
    assert "tectonic resume.tex" in runs[-1]
    for call in calls:
        assert not call.startswith(("build", "pull", "image rm", "rmi")), call


def test_a_missing_image_is_never_pulled(fake: Path) -> None:
    proc = _run(
        fake, "--image", "ghcr.io/example/devcontainer-latex:v1", missing_image=True
    )

    assert proc.returncode == 2
    assert "is not in the local image store" in proc.stderr
    assert _calls(fake) == ["image inspect -- ghcr.io/example/devcontainer-latex:v1"]


def test_by_default_both_images_are_built_and_removed(fake: Path) -> None:
    proc = _run(fake)

    assert proc.returncode == 0, proc.stderr
    calls = _calls(fake)
    builds = [call for call in calls if call.startswith("build ")]
    assert len(builds) == 2
    assert "devcontainers/base/Dockerfile" in builds[0]
    assert "devcontainers/latex/Dockerfile" in builds[1]
    removed = [call for call in calls if call.startswith("image rm ")]
    assert len(removed) == 2


@pytest.mark.parametrize("args", [("--image",), ("--image", ""), ("--build",)])
def test_usage_errors_exit_2(fake: Path, args: tuple[str, ...]) -> None:
    proc = _run(fake, *args)

    assert proc.returncode == 2
    assert _calls(fake) == []
