import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check-devcontainer-workload.sh"

STACK_TOOLS = {
    "ansible": "ansible",
    "golang": "go",
    "latex": "tectonic",
    "terraform": "terraform",
}


def _stub(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(0o755)


@pytest.fixture
def sandbox(tmp_path: Path) -> dict[str, Path]:
    """A home and a PATH on which every check passes, whatever the host is."""
    home = tmp_path / "home"
    home.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _stub(bin_dir, "ssh", "exit 0")
    # Only check_login_shell uses awk, to read the host's /etc/passwd.
    _stub(bin_dir, "awk", "echo /bin/bash")
    for tool in ("ansible", "tectonic", "terraform"):
        _stub(bin_dir, tool, "exit 0")
    _stub(
        bin_dir,
        "go",
        ": > workload\nchmod +x workload\nprintf '#!/bin/sh\\necho \"workload ok\"\\n' > workload",
    )
    return {"home": home, "bin": bin_dir, "tmp": tmp_path}


def _run(
    sandbox: dict[str, Path], *args: str, lang: str = "C.UTF-8"
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "HOME": str(sandbox["home"]),
        "LANG": lang,
        "PATH": f"{sandbox['bin']}{os.pathsep}{os.environ['PATH']}",
    }
    return subprocess.run(
        [str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


@pytest.mark.parametrize("args", [(), ("cobol",)])
def test_usage_error_exits_2(sandbox: dict[str, Path], args: tuple[str, ...]) -> None:
    result = _run(sandbox, *args)
    assert result.returncode == 2
    assert "usage:" in result.stderr


@pytest.mark.parametrize("stack", sorted(STACK_TOOLS))
def test_every_check_passing_exits_0(sandbox: dict[str, Path], stack: str) -> None:
    result = _run(sandbox, stack)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"{stack}: all checks passed" in result.stdout
    assert "FAILED" not in result.stdout


@pytest.mark.parametrize("stack,tool", sorted(STACK_TOOLS.items()))
def test_failing_stack_tool_exits_1(
    sandbox: dict[str, Path], stack: str, tool: str
) -> None:
    _stub(sandbox["bin"], tool, "echo broken >&2; exit 3")
    result = _run(sandbox, stack)
    assert result.returncode == 1
    assert "broken" in result.stdout
    assert "::error::" in result.stderr


def test_failing_ssh_exits_1(sandbox: dict[str, Path]) -> None:
    _stub(sandbox["bin"], "ssh", "echo 'ssh: not found' >&2; exit 127")
    result = _run(sandbox, "terraform")
    assert result.returncode == 1
    assert "FAILED  ssh -V: ssh: not found" in result.stdout


def test_login_shell_other_than_bash_exits_1(sandbox: dict[str, Path]) -> None:
    _stub(sandbox["bin"], "awk", "echo /bin/sh")
    result = _run(sandbox, "terraform")
    assert result.returncode == 1
    assert "is '/bin/sh', not /bin/bash" in result.stdout


def test_lang_other_than_utf8_exits_1(sandbox: dict[str, Path]) -> None:
    result = _run(sandbox, "terraform", lang="POSIX")
    assert result.returncode == 1
    assert "LANG is 'POSIX', not C.UTF-8" in result.stdout


# The section an image wrote with `git config --global` on v2.1.0 stopped the
# extension copying the user's file; the ones a template's lifecycle writes do not.
@pytest.mark.parametrize("section", ["[init]", '[url "git@github.com:"]', "[safely]"])
def test_gitconfig_section_blocking_the_copy_exits_1(
    sandbox: dict[str, Path], section: str
) -> None:
    (sandbox["home"] / ".gitconfig").write_text(f"{section}\n\tkey = value\n")
    result = _run(sandbox, "terraform")
    assert result.returncode == 1
    assert "stops the extension copying" in result.stdout
    assert section in result.stdout


@pytest.mark.parametrize("section", ["[safe]", '[filter "lfs"]', "[filter\t"])
def test_gitconfig_section_allowing_the_copy_passes(
    sandbox: dict[str, Path], section: str
) -> None:
    (sandbox["home"] / ".gitconfig").write_text(f"{section}\n\tkey = value\n")
    result = _run(sandbox, "terraform")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "does not stop the extension copying" in result.stdout


def test_writable_volume_target_passes_and_leaves_nothing(
    sandbox: dict[str, Path],
) -> None:
    target = sandbox["tmp"] / "volume"
    target.mkdir()
    result = _run(sandbox, "terraform", str(target))
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"volume target {target} is writable" in result.stdout
    assert list(target.iterdir()) == []


def test_missing_volume_target_exits_1(sandbox: dict[str, Path]) -> None:
    target = sandbox["tmp"] / "absent"
    result = _run(sandbox, "terraform", str(target))
    assert result.returncode == 1
    assert f"volume target {target} is not writable" in result.stdout


def test_relative_volume_target_exits_1(sandbox: dict[str, Path]) -> None:
    result = _run(sandbox, "terraform", "relative/path")
    assert result.returncode == 1
    assert "not an absolute path" in result.stdout


def test_a_failure_does_not_stop_the_later_checks(sandbox: dict[str, Path]) -> None:
    _stub(sandbox["bin"], "ssh", "exit 1")
    _stub(sandbox["bin"], "awk", "echo /bin/sh")
    _stub(sandbox["bin"], "terraform", "exit 1")
    result = _run(sandbox, "terraform", "relative/path", lang="POSIX")
    assert result.returncode == 1
    assert result.stdout.count("FAILED") == 5
    assert "terraform: 5 check(s) failed" in result.stdout
