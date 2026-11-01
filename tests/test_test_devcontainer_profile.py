import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "test-devcontainer-profile.sh"

PROFILES = [
    ("ansible", "devcontainer.docker-socket.json", None),
    ("ansible", "devcontainer.dind.json", None),
    ("ansible", "devcontainer.podman.json", "Dockerfile.podman"),
    ("terraform", "devcontainer.docker-socket.json", None),
]

FAKE_DEVCONTAINER = """#!/usr/bin/env bash
subcommand="$1"
shift
printf '%s\\n' "${subcommand}" >> "${FAKE_STATE}/calls.log"
if [[ "${subcommand}" == "up" ]]; then
  while (($#)); do
    if [[ "$1" == "--config" ]]; then
      cp "$2" "${FAKE_STATE}/config.json"
    fi
    shift
  done
  ups="$(grep -c '^up$' "${FAKE_STATE}/calls.log")"
  ((ups > FAKE_UP_FAILURES))
  exit
fi
while [[ "$1" != "--" ]]; do
  shift
done
shift
exec "$@"
"""

FAKE_DOCKER = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "${FAKE_STATE}/docker.log"
checks="$(wc -l < "${FAKE_STATE}/docker.log")"
((checks > FAKE_CHECK_FAILURES))
"""


def _stub(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text(body)
    path.chmod(0o755)


@pytest.fixture
def fake(tmp_path: Path) -> Path:
    """A devcontainer and docker that fail on demand, and a sleep that returns at once."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _stub(bin_dir, "devcontainer", FAKE_DEVCONTAINER)
    _stub(bin_dir, "docker", FAKE_DOCKER)
    _stub(bin_dir, "sleep", "#!/bin/sh\nexit 0\n")
    _stub(bin_dir, "id", '#!/bin/sh\necho "${FAKE_USER}"\n')
    return tmp_path


def _run(
    fake: Path,
    *args: str,
    base_image: str | None = None,
    dockerfile: str | None = None,
    check_attempts: int | None = None,
    user: str = "vscode",
    up_failures: int = 0,
    check_failures: int = 0,
    tmpdir: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "PATH": f"{fake / 'bin'}{os.pathsep}{os.environ['PATH']}",
        "FAKE_STATE": str(fake),
        "FAKE_USER": user,
        "FAKE_UP_FAILURES": str(up_failures),
        "FAKE_CHECK_FAILURES": str(check_failures),
    }
    for name in ("BASE_IMAGE", "DOCKERFILE", "CHECK_ATTEMPTS"):
        env.pop(name, None)
    if base_image is not None:
        env["BASE_IMAGE"] = base_image
    if dockerfile is not None:
        env["DOCKERFILE"] = dockerfile
    if check_attempts is not None:
        env["CHECK_ATTEMPTS"] = str(check_attempts)
    if tmpdir is not None:
        env["TMPDIR"] = str(tmpdir)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _calls(fake: Path, name: str) -> int:
    log = fake / "calls.log"
    return log.read_text().splitlines().count(name) if log.exists() else 0


@pytest.mark.parametrize(("stack", "profile", "dockerfile"), PROFILES)
def test_config_is_the_profile_built_from_the_stack_dockerfile(
    fake: Path, stack: str, profile: str, dockerfile: str | None
) -> None:
    proc = _run(fake, stack, profile, "docker version", dockerfile=dockerfile)

    assert proc.returncode == 0, proc.stderr
    rendered = json.loads((fake / "config.json").read_text())
    shipped = json.loads((REPO_ROOT / "devcontainers" / stack / profile).read_text())
    build = rendered.pop("build")
    assert build == {
        "dockerfile": str(
            REPO_ROOT / "devcontainers" / stack / (dockerfile or "Dockerfile")
        ),
        "context": "${localWorkspaceFolder}",
    }
    assert "image" in shipped
    del shipped["image"]
    assert rendered == shipped


def test_base_image_becomes_a_build_argument(fake: Path) -> None:
    proc = _run(
        fake,
        "ansible",
        "devcontainer.docker-socket.json",
        "docker version",
        base_image="devcontainer-base:ci",
    )

    assert proc.returncode == 0, proc.stderr
    rendered = json.loads((fake / "config.json").read_text())
    assert rendered["build"]["args"] == {"BASE_IMAGE": "devcontainer-base:ci"}


def test_the_config_directory_is_removed(fake: Path) -> None:
    scratch = fake / "scratch"
    scratch.mkdir()

    proc = _run(
        fake,
        "terraform",
        "devcontainer.docker-socket.json",
        "docker version",
        tmpdir=scratch,
    )

    assert proc.returncode == 0, proc.stderr
    assert list(scratch.iterdir()) == []


def test_up_is_retried(fake: Path) -> None:
    proc = _run(
        fake,
        "terraform",
        "devcontainer.docker-socket.json",
        "docker version",
        up_failures=2,
    )

    assert proc.returncode == 0, proc.stderr
    assert _calls(fake, "up") == 3
    assert proc.stderr.count("::warning::") == 2


def test_up_gives_up_and_never_runs_the_check(fake: Path) -> None:
    proc = _run(
        fake,
        "terraform",
        "devcontainer.docker-socket.json",
        "docker version",
        up_failures=3,
    )

    assert proc.returncode == 1
    assert _calls(fake, "up") == 3
    assert _calls(fake, "exec") == 0
    assert (
        "::error::devcontainer up of devcontainer.docker-socket.json failed"
        in proc.stderr
    )


def test_the_check_is_retried_until_it_passes(fake: Path) -> None:
    proc = _run(
        fake, "ansible", "devcontainer.dind.json", "docker info", check_failures=29
    )

    assert proc.returncode == 0, proc.stderr
    assert _calls(fake, "exec") == 30


def test_the_check_is_bounded(fake: Path) -> None:
    proc = _run(
        fake, "ansible", "devcontainer.dind.json", "docker info", check_failures=1000
    )

    assert proc.returncode == 1
    assert _calls(fake, "exec") == 30
    assert "::error::'docker info' did not succeed as vscode" in proc.stderr


def test_check_attempts_can_be_lowered(fake: Path) -> None:
    proc = _run(
        fake,
        "ansible",
        "devcontainer.podman.json",
        "docker info",
        dockerfile="Dockerfile.podman",
        check_attempts=2,
        check_failures=1000,
    )

    assert proc.returncode == 1
    assert _calls(fake, "exec") == 2


def test_the_check_only_counts_as_vscode(fake: Path) -> None:
    proc = _run(
        fake,
        "terraform",
        "devcontainer.docker-socket.json",
        "docker version",
        user="root",
    )

    assert proc.returncode == 1
    assert not (fake / "docker.log").exists()


@pytest.mark.parametrize(
    "args",
    [
        (),
        ("terraform", "devcontainer.docker-socket.json"),
        ("terraform", "devcontainer.nope.json", "docker version"),
        ("nope", "devcontainer.docker-socket.json", "docker version"),
    ],
)
def test_usage_errors_exit_2(fake: Path, args: tuple[str, ...]) -> None:
    proc = _run(fake, *args)

    assert proc.returncode == 2
    assert _calls(fake, "up") == 0


def test_a_missing_dockerfile_is_a_usage_error(fake: Path) -> None:
    proc = _run(
        fake,
        "ansible",
        "devcontainer.podman.json",
        "docker info",
        dockerfile="Dockerfile.nope",
    )

    assert proc.returncode == 2
    assert "Dockerfile.nope does not exist" in proc.stderr
    assert _calls(fake, "up") == 0


def test_a_profile_with_comments_fails_before_up(fake: Path, tmp_path: Path) -> None:
    """jq, which renders the config, reads plain JSON only."""
    stack = tmp_path / "repo" / "devcontainers" / "demo"
    (stack / "local-build").mkdir(parents=True)
    (stack / "devcontainer.commented.json").write_text(
        '{\n  // a comment\n  "image": "x"\n}\n'
    )
    (stack / "local-build" / "devcontainer.json").write_text(
        '{"build": {"dockerfile": "../Dockerfile", "context": "."}}\n'
    )

    env = {
        **os.environ,
        "PATH": f"{fake / 'bin'}{os.pathsep}{os.environ['PATH']}",
        "FAKE_STATE": str(fake),
        "FAKE_USER": "vscode",
        "FAKE_UP_FAILURES": "0",
        "FAKE_CHECK_FAILURES": "0",
    }
    proc = subprocess.run(
        ["bash", str(SCRIPT), "demo", "devcontainer.commented.json", "docker info"],
        cwd=tmp_path / "repo",
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert proc.returncode != 0
    assert _calls(fake, "up") == 0
