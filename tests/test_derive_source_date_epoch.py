import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "derive-source-date-epoch.sh"

FIXED_EPOCH = 1793261762
FIXED_CREATED = "2026-10-29T08:16:02Z"


def _env(tmp_path: Path) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"}
    }
    env.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CEILING_DIRECTORIES": str(tmp_path.parent),
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
        }
    )
    return env


def _git(repo: Path, env: dict[str, str], *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=repo, env=env, check=True, capture_output=True, text=True
    )


def _repo(tmp_path: Path, committer_date: str, author_date: str | None = None) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    env = _env(tmp_path)
    _git(repo, env, "init", "-q", "-b", "main")
    (repo / "README").write_text("x\n", encoding="utf-8")
    _git(repo, env, "add", "README")
    commit_env = {
        **env,
        "GIT_COMMITTER_DATE": committer_date,
        "GIT_AUTHOR_DATE": author_date or committer_date,
    }
    _git(repo, commit_env, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "c")
    return repo


def _run(cwd: Path, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=cwd,
        env=_env(tmp_path),
        capture_output=True,
        text=True,
        check=False,
    )


def _parse(stdout: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in stdout.splitlines())


def test_derive_source_date_epoch_fixed_committer_date_prints_its_epoch(tmp_path):
    repo = _repo(tmp_path, f"{FIXED_EPOCH} +0000")

    result = _run(repo, tmp_path)

    assert result.returncode == 0, result.stderr
    assert _parse(result.stdout)["epoch"] == str(FIXED_EPOCH)


def test_derive_source_date_epoch_fixed_committer_date_prints_utc_created(tmp_path):
    repo = _repo(tmp_path, f"{FIXED_EPOCH} +0000")

    result = _run(repo, tmp_path)

    assert result.returncode == 0, result.stderr
    assert _parse(result.stdout)["created"] == FIXED_CREATED


def test_derive_source_date_epoch_fixed_committer_date_prints_only_two_keys(tmp_path):
    repo = _repo(tmp_path, f"{FIXED_EPOCH} +0000")

    result = _run(repo, tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"epoch={FIXED_EPOCH}\ncreated={FIXED_CREATED}\n"
    assert result.stderr == ""


def test_derive_source_date_epoch_non_utc_committer_zone_prints_utc_created(tmp_path):
    repo = _repo(tmp_path, f"{FIXED_EPOCH} +0200")

    result = _run(repo, tmp_path)

    assert result.returncode == 0, result.stderr
    assert _parse(result.stdout) == {
        "epoch": str(FIXED_EPOCH),
        "created": FIXED_CREATED,
    }


def test_derive_source_date_epoch_author_date_differs_uses_committer_time(tmp_path):
    repo = _repo(
        tmp_path, f"{FIXED_EPOCH} +0000", author_date=f"{FIXED_EPOCH - 86400} +0000"
    )

    result = _run(repo, tmp_path)

    assert result.returncode == 0, result.stderr
    assert _parse(result.stdout)["epoch"] == str(FIXED_EPOCH)


def test_derive_source_date_epoch_non_repository_exits_non_zero(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()

    result = _run(plain, tmp_path)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "derive-source-date-epoch: git log found no commit" in result.stderr


def test_derive_source_date_epoch_repository_without_commits_exits_non_zero(tmp_path):
    repo = tmp_path / "empty"
    repo.mkdir()
    _git(repo, _env(tmp_path), "init", "-q", "-b", "main")

    result = _run(repo, tmp_path)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "derive-source-date-epoch:" in result.stderr
