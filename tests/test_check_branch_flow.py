import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "scripts/check-branch-flow.sh", *args],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )


def test_main_allows_develop():
    proc = _run("--base", "main", "--head", "develop")
    assert proc.returncode == 0
    assert "allowed to target main" in proc.stdout


def test_main_allows_hotfix():
    proc = _run("--base", "main", "--head", "hotfix/security-fix")
    assert proc.returncode == 0
    assert "allowed to target main" in proc.stdout


def test_main_rejects_feature_branch():
    proc = _run("--base", "main", "--head", "feature/new-ui")
    assert proc.returncode == 1
    assert "must come from 'develop' or 'hotfix/*'" in proc.stderr


def test_develop_accepts_feature_branch():
    proc = _run("--base", "develop", "--head", "feature/new-ui")
    assert proc.returncode == 0
    assert "allowed to target develop" in proc.stdout


def test_develop_warns_on_unconventional_branch():
    proc = _run("--base", "develop", "--head", "experiment/foo")
    assert proc.returncode == 0
    assert "does not follow the documented naming convention" in proc.stderr


def test_requires_arguments():
    proc = _run("--base", "main")
    assert proc.returncode == 1
    assert "Both --base and --head are required." in proc.stderr
