import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "smoke-podman-profile.sh"
PROFILE = REPO_ROOT / "devcontainers" / "ansible" / "devcontainer.podman.json"

REF = "ghcr.io/example/devcontainer-ansible-podman@sha256:" + "a" * 64
STORAGE = "/home/vscode/.local/share/containers"

# One argument per line, a blank line between calls. The check's attempts are
# counted, and each logs the mode of what it got on /workspace.
FAKE_DOCKER = """#!/usr/bin/env bash
printf '%s\\n' "$@" '' >> "${FAKE_STATE}/docker.log"
if [[ " $* " != *" podman-smoke-test --ee "* ]]; then
  exit 0
fi
for arg in "$@"; do
  if [[ "${arg}" == type=bind,*,target=/workspace ]]; then
    source="${arg#type=bind,source=}"
    stat -c '%a' "${source%,target=/workspace}" >> "${FAKE_STATE}/modes.log"
    touch "${source%,target=/workspace}/left-by-the-check"
  fi
done
printf 'check\\n' >> "${FAKE_STATE}/checks.log"
checks="$(wc -l < "${FAKE_STATE}/checks.log")"
((checks > FAKE_CHECK_FAILURES))
"""


def _stub(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text(body)
    path.chmod(0o755)


@pytest.fixture
def fake(tmp_path: Path) -> Path:
    """A docker that fails the check on demand, and a sleep that returns at once."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (tmp_path / "scratch").mkdir()
    _stub(bin_dir, "docker", FAKE_DOCKER)
    _stub(bin_dir, "sleep", "#!/bin/sh\nexit 0\n")
    return tmp_path


def _run(
    fake: Path,
    *args: str,
    check_failures: int = 0,
    script: Path = SCRIPT,
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "PATH": f"{fake / 'bin'}{os.pathsep}{os.environ['PATH']}",
        "FAKE_STATE": str(fake),
        "FAKE_CHECK_FAILURES": str(check_failures),
        "TMPDIR": str(fake / "scratch"),
    }
    return subprocess.run(
        ["bash", str(script), *args],
        cwd=fake,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _docker_calls(fake: Path) -> list[list[str]]:
    log = fake / "docker.log"
    if not log.exists():
        return []
    calls = log.read_text().split("\n\n")
    return [call.splitlines() for call in calls if call.strip()]


def _checks(fake: Path) -> list[list[str]]:
    return [
        call
        for call in _docker_calls(fake)
        if call[-2:] == ["podman-smoke-test", "--ee"]
    ]


def _mount(call: list[str], kind: str, target: str) -> str:
    """Return the source of the mount of that kind on that target; fail without one."""
    sources = []
    for arg in call:
        prefix = f"type={kind},source="
        suffix = f",target={target}"
        if arg.startswith(prefix) and arg.endswith(suffix):
            sources.append(arg[len(prefix) : -len(suffix)])
    assert len(sources) == 1, call
    return sources[0]


def test_check_uses_the_profiles_run_args_and_nothing_else_from_it(fake: Path) -> None:
    proc = _run(fake, REF)

    assert proc.returncode == 0, proc.stderr
    checks = _checks(fake)
    assert len(checks) == 1
    call = checks[0]
    run_args = json.loads(PROFILE.read_text())["runArgs"]
    assert "--init" in run_args
    assert call[:2] == ["run", "--rm"]
    assert call[2 : 2 + len(run_args)] == run_args
    assert call.count("--init") == 1
    joined = " ".join(call)
    assert "uv-cache" not in joined
    assert "ansible-galaxy-cache" not in joined
    assert "--privileged" not in joined


def test_check_runs_as_vscode_with_storage_volume_and_workspace(fake: Path) -> None:
    proc = _run(fake, REF)

    assert proc.returncode == 0, proc.stderr
    call = _checks(fake)[0]
    assert call[call.index("--user") + 1] == "vscode"
    assert _mount(call, "volume", STORAGE).startswith("podman-smoke-")
    assert Path(_mount(call, "bind", "/workspace")).parent == fake / "scratch"
    assert call[-3:] == [REF, "podman-smoke-test", "--ee"]


def test_workspace_is_writable_by_a_vscode_with_another_uid(fake: Path) -> None:
    proc = _run(fake, REF)

    assert proc.returncode == 0, proc.stderr
    assert (fake / "modes.log").read_text().split() == ["777"]


def test_every_attempt_starts_fresh_and_removes_what_it_used(fake: Path) -> None:
    proc = _run(fake, REF, check_failures=2)

    assert proc.returncode == 0, proc.stderr
    assert proc.stderr.count("::warning::") == 2
    checks = _checks(fake)
    assert len(checks) == 3
    volumes = [_mount(call, "volume", STORAGE) for call in checks]
    workspaces = [_mount(call, "bind", "/workspace") for call in checks]
    assert len(set(volumes)) == 3
    assert len(set(workspaces)) == 3
    removed = [call[-1] for call in _docker_calls(fake) if call[:2] == ["volume", "rm"]]
    assert removed == volumes
    assert list((fake / "scratch").iterdir()) == []


def test_workspace_is_emptied_as_root_in_the_image(fake: Path) -> None:
    proc = _run(fake, REF)

    assert proc.returncode == 0, proc.stderr
    empties = [call for call in _docker_calls(fake) if "find" in call]
    assert len(empties) == 1
    call = empties[0]
    assert call[call.index("--user") + 1] == "root"
    assert _mount(call, "bind", "/scratch") == _mount(
        _checks(fake)[0], "bind", "/workspace"
    )
    assert call[call.index("find") - 1] == REF


def test_fails_after_three_attempts_and_still_cleans_up(fake: Path) -> None:
    proc = _run(fake, REF, check_failures=3)

    assert proc.returncode == 1
    assert "::error::" in proc.stderr
    assert "failed after 3 attempts" in proc.stderr
    assert proc.stderr.count("::warning::") == 2
    assert len(_checks(fake)) == 3
    assert list((fake / "scratch").iterdir()) == []


@pytest.mark.parametrize("args", [(), ("",), (REF, "extra")])
def test_usage_errors_exit_2_without_touching_docker(
    fake: Path, args: tuple[str, ...]
) -> None:
    proc = _run(fake, *args)

    assert proc.returncode == 2
    assert _docker_calls(fake) == []


@pytest.mark.parametrize(
    "profile",
    [
        "{}",
        '{"runArgs": []}',
        '{"runArgs": "--init"}',
        "not json",
    ],
)
def test_a_profile_without_run_args_fails_before_running_anything(
    fake: Path, profile: str
) -> None:
    tree = fake / "tree"
    (tree / "scripts").mkdir(parents=True)
    (tree / "devcontainers" / "ansible").mkdir(parents=True)
    script = tree / "scripts" / SCRIPT.name
    shutil.copy(SCRIPT, script)
    (tree / "devcontainers" / "ansible" / PROFILE.name).write_text(profile)

    proc = _run(fake, REF, script=script)

    assert proc.returncode == 1
    assert "no readable runArgs" in proc.stderr
    assert _docker_calls(fake) == []
