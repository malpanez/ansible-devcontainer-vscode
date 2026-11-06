import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "tested-digests.py"

REPOSITORY = "malpanez/ansible-devcontainer-vscode"
MAIN_SHA = "a" * 40
HEAD_SHA = "b" * 40
BASE_SHA = "c" * 40
TREE = "d" * 40
DIGEST = "sha256:" + "e" * 64
OTHER_DIGEST = "sha256:" + "f" * 64

FAKE_GH = """#!/usr/bin/env bash
NAME="$(printf '%s' "$2" | tr -c 'A-Za-z0-9._-' '_')"
if [ -f "${FIXTURES}/${NAME}.json" ]; then
  cat "${FIXTURES}/${NAME}.json"
else
  echo "HTTP 404: Not Found ($2)" >&2
  exit 1
fi
"""


def _run(
    *args: str, env: dict[str, str] | None = None, stdin: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *args],
        env={**os.environ, **(env or {})},
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def _digests(tmp_path: Path, **digests: str) -> Path:
    directory = tmp_path / "digests"
    directory.mkdir(exist_ok=True)
    for name, digest in digests.items():
        name = name.replace("_", "-")
        (directory / f"{name}.json").write_text(
            json.dumps({"name": name, "digest": digest})
        )
    return directory


def _write(
    tmp_path: Path,
    directory: Path,
    images: str,
    base: str = "false",
    tree: str = TREE,
    # A promotion's run is attempt 2: attempt 1 waits, parked, until
    # promote-to-main.yml approves it.
    attempt: str = "2",
) -> tuple[subprocess.CompletedProcess[str], Path]:
    output = tmp_path / "tested-digests.json"
    proc = _run(
        "write",
        "--digests",
        str(directory),
        "--images",
        images,
        "--base",
        base,
        "--tree",
        tree,
        "--head",
        HEAD_SHA,
        "--base-sha",
        BASE_SHA,
        "--run-id",
        "42",
        "--attempt",
        attempt,
    )
    # The record is stdout, as ci.yml redirects it to tested-digests.json.
    if proc.returncode == 0:
        output.write_text(proc.stdout)
    return proc, output


def test_the_record_names_the_tree_the_commits_the_run_and_each_digest(
    tmp_path: Path,
) -> None:
    directory = _digests(tmp_path, base=DIGEST, ansible=OTHER_DIGEST)

    proc, output = _write(tmp_path, directory, '["ansible"]', base="true")

    assert proc.returncode == 0, proc.stderr
    assert json.loads(output.read_text()) == {
        "attempt": 2,
        "base": BASE_SHA,
        "head": HEAD_SHA,
        "images": {"ansible": OTHER_DIGEST, "base": DIGEST},
        "run_id": 42,
        "tree": TREE,
    }


def test_a_run_that_built_nothing_still_records_its_tree(tmp_path: Path) -> None:
    proc, output = _write(tmp_path, tmp_path / "never-downloaded", "[]")

    assert proc.returncode == 0, proc.stderr
    record = json.loads(output.read_text())
    assert record["images"] == {}
    assert record["tree"] == TREE


@pytest.mark.parametrize(
    ("digests", "images", "base", "named"),
    [
        # A build whose digest never arrived: the record would leave it out.
        ({"golang": DIGEST}, '["golang","latex"]', "false", "missing: latex"),
        ({"golang": DIGEST}, '["golang"]', "true", "missing: base"),
        # A digest of an image this run was not asked to build.
        (
            {"golang": DIGEST, "latex": DIGEST},
            '["golang"]',
            "false",
            "not built: latex",
        ),
    ],
)
def test_the_digests_must_be_exactly_the_images_built(
    tmp_path: Path, digests: dict[str, str], images: str, base: str, named: str
) -> None:
    proc, output = _write(tmp_path, _digests(tmp_path, **digests), images, base)

    assert proc.returncode == 1
    assert named in proc.stderr
    assert "::error" in proc.stderr
    assert not output.exists()


@pytest.mark.parametrize(
    "entry",
    [
        {"name": "golang", "digest": "latest"},
        {"name": "golang", "digest": "sha256:" + "E" * 64},
        {"name": "latex", "digest": DIGEST},
        {"name": "golang"},
        ["golang", DIGEST],
    ],
)
def test_a_malformed_digest_file_fails(tmp_path: Path, entry: Any) -> None:
    directory = tmp_path / "digests"
    directory.mkdir()
    (directory / "golang.json").write_text(json.dumps(entry))

    proc, output = _write(tmp_path, directory, '["golang"]')

    assert proc.returncode == 1
    assert not output.exists()


@pytest.mark.parametrize(
    ("tree", "base"), [("d" * 39, "false"), ("D" * 40, "false"), (TREE, "yes")]
)
def test_bad_arguments_fail(tmp_path: Path, tree: str, base: str) -> None:
    proc, output = _write(tmp_path, tmp_path / "none", "[]", base=base, tree=tree)

    assert proc.returncode == 1
    assert not output.exists()


@pytest.mark.parametrize("attempt", ["0", "-1", "two", "1.5", "02", ""])
def test_an_attempt_that_is_not_a_positive_integer_fails(
    tmp_path: Path, attempt: str
) -> None:
    proc, output = _write(tmp_path, tmp_path / "none", "[]", attempt=attempt)

    assert proc.returncode == 1
    assert "not a run attempt" in proc.stderr
    assert not output.exists()


def _record(tmp_path: Path, **overrides: Any) -> Path:
    record = {
        "base": BASE_SHA,
        "head": HEAD_SHA,
        "images": {"golang": DIGEST},
        "run_id": 42,
        "tree": TREE,
        **overrides,
    }
    path = tmp_path / "record.json"
    path.write_text(json.dumps(record))
    return path


def _verify(
    path: Path, tree: str = TREE, run_id: str = "42"
) -> subprocess.CompletedProcess[str]:
    stdin = path.read_text() if path.is_file() else ""
    return _run("verify", "--tree", tree, "--run-id", run_id, stdin=stdin)


def test_a_record_of_this_tree_passes(tmp_path: Path) -> None:
    proc = _verify(_record(tmp_path))

    assert proc.returncode == 0, proc.stderr
    assert f"golang {DIGEST}" in proc.stdout


def test_a_record_of_no_image_passes(tmp_path: Path) -> None:
    proc = _verify(_record(tmp_path, images={}))

    assert proc.returncode == 0, proc.stderr


# Until 2d-2b publishes from it, a record from before attempt existed passes;
# _record writes none.
def test_a_record_with_its_attempt_passes(tmp_path: Path) -> None:
    proc = _verify(_record(tmp_path, attempt=3))

    assert proc.returncode == 0, proc.stderr
    assert f"golang {DIGEST}" in proc.stdout


@pytest.mark.parametrize("attempt", [True, 0, -1, "2", 2.0, None])
def test_a_record_whose_attempt_is_not_a_positive_integer_fails(
    tmp_path: Path, attempt: Any
) -> None:
    proc = _verify(_record(tmp_path, attempt=attempt))

    assert proc.returncode == 1
    assert "not a run attempt" in proc.stderr


def test_a_record_of_another_tree_fails_and_says_what_to_do(tmp_path: Path) -> None:
    proc = _verify(_record(tmp_path), tree="0" * 40)

    assert proc.returncode == 1
    assert "main took a tree no candidate run tested" in proc.stderr
    assert "Merge main into develop" in proc.stderr


@pytest.mark.parametrize(
    "overrides",
    [
        {"run_id": 41},
        {"images": {"golang": "latest"}},
        {"images": []},
        {"head": "short"},
        {"extra": 1},
    ],
)
def test_a_record_that_is_not_this_run_s_or_malformed_fails(
    tmp_path: Path, overrides: dict[str, Any]
) -> None:
    proc = _verify(_record(tmp_path, **overrides))

    assert proc.returncode == 1
    assert "::error" in proc.stderr


def test_an_empty_record_fails(tmp_path: Path) -> None:
    proc = _verify(tmp_path / "missing.json")

    assert proc.returncode == 1
    assert "::error" in proc.stderr


def _fixture(fixtures: Path, path: str, answer: Any) -> None:
    name = re.sub(r"[^A-Za-z0-9._-]", "_", path)
    (fixtures / f"{name}.json").write_text(json.dumps(answer))


PULLS = f"repos/{REPOSITORY}/commits/{MAIN_SHA}/pulls"
RUNS = (
    f"repos/{REPOSITORY}/actions/workflows/ci.yml/runs"
    f"?event=pull_request&head_sha={HEAD_SHA}&status=success&per_page=100"
)


def _pull(**overrides: Any) -> dict[str, Any]:
    return {
        "number": 633,
        "merged_at": "2026-11-06T08:13:56Z",
        "merge_commit_sha": MAIN_SHA,
        "base": {"ref": "main"},
        "head": {
            "ref": "develop",
            "label": "malpanez:develop",
            "sha": HEAD_SHA,
            "repo": {"full_name": REPOSITORY},
        },
        **overrides,
    }


def _run_entry(
    run_id: int, started: str, repository: str = REPOSITORY
) -> dict[str, Any]:
    return {
        "id": run_id,
        "event": "pull_request",
        "conclusion": "success",
        "head_sha": HEAD_SHA,
        "head_branch": "develop",
        "head_repository": {"full_name": repository},
        "run_started_at": started,
    }


def _jobs_page(run_id: int, page: int) -> str:
    return (
        f"repos/{REPOSITORY}/actions/runs/{run_id}/jobs"
        f"?filter=latest&per_page=100&page={page}"
    )


# A candidate run's jobs, Candidate tag among them, as one page.
PASSED_JOBS = [
    {"name": "Lint", "conclusion": "success"},
    {"name": "Candidate tag", "conclusion": "success"},
    {"name": "Provenance", "conclusion": "skipped"},
]


def _github(
    tmp_path: Path,
    pulls: Any,
    runs: list[dict[str, Any]],
    artifacts: dict[int, list[dict[str, Any]]],
    jobs: dict[int, list[Any]] | None = None,
) -> dict[str, str]:
    """Fixtures for find-run. jobs maps a run to the pages of its jobs; each
    run with artifacts gets PASSED_JOBS when it is not given."""
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    _fixture(fixtures, PULLS, pulls)
    _fixture(fixtures, RUNS, {"workflow_runs": runs})
    for run_id, found in artifacts.items():
        path = f"repos/{REPOSITORY}/actions/runs/{run_id}/artifacts?name=tested-digests"
        _fixture(fixtures, path, {"artifacts": found})
    pages = {run_id: [PASSED_JOBS] for run_id in artifacts} | (jobs or {})
    for run_id, run_pages in pages.items():
        total = sum(len(page) for page in run_pages if isinstance(page, list))
        for number, page in enumerate(run_pages, start=1):
            answer = (
                {"total_count": total, "jobs": page} if isinstance(page, list) else page
            )
            _fixture(fixtures, _jobs_page(run_id, number), answer)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(0o755)
    return {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "FIXTURES": str(fixtures),
    }


def _find(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return _run("find-run", "--repository", REPOSITORY, "--sha", MAIN_SHA, env=env)


ARTIFACT = [{"name": "tested-digests", "expired": False}]


def test_the_newest_successful_run_of_the_promotion_is_found(tmp_path: Path) -> None:
    env = _github(
        tmp_path,
        [_pull(number=1, merge_commit_sha="0" * 40), _pull()],
        [_run_entry(7, "2026-11-06T08:00:00Z"), _run_entry(9, "2026-11-06T08:05:00Z")],
        {9: ARTIFACT},
    )

    proc = _find(env)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == ["run_id=9", "pr=633", f"head={HEAD_SHA}"]


@pytest.mark.parametrize(
    ("repository", "sha", "named"),
    [
        ("-x/ansible-devcontainer-vscode", MAIN_SHA, "not owner/name"),
        (f"{REPOSITORY}/extra", MAIN_SHA, "not owner/name"),
        (REPOSITORY, "-" + "a" * 39, "not a 40-character SHA-1"),
        (REPOSITORY, "A" * 40, "not a 40-character SHA-1"),
    ],
)
def test_find_run_hands_gh_only_a_repository_and_a_sha(
    tmp_path: Path, repository: str, sha: str, named: str
) -> None:
    # Fixtures that would answer, so a call that got through would pass.
    env = _github(
        tmp_path, [_pull()], [_run_entry(9, "2026-11-06T08:05:00Z")], {9: ARTIFACT}
    )

    proc = _run("find-run", f"--repository={repository}", f"--sha={sha}", env=env)

    assert proc.returncode == 1
    assert named in proc.stderr


def test_a_fork_s_run_of_the_same_head_is_not_the_promotion_s(tmp_path: Path) -> None:
    # A fork's pull request can have develop's exact head and a branch named
    # develop. Its run is newer here, and has no record.
    env = _github(
        tmp_path,
        [_pull()],
        [
            _run_entry(7, "2026-11-06T08:00:00Z"),
            _run_entry(9, "2026-11-06T08:05:00Z", repository="someone/fork"),
        ],
        {7: ARTIFACT},
    )

    proc = _find(env)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines()[0] == "run_id=7"


@pytest.mark.parametrize(
    ("pulls", "named"),
    [
        ([], "moved without the promotion pull request"),
        ([_pull(merged_at=None)], "moved without the promotion pull request"),
        ([_pull(base={"ref": "develop"})], "moved without the promotion pull request"),
        (
            [
                _pull(
                    head={
                        "ref": "feature/x",
                        "sha": HEAD_SHA,
                        "repo": {"full_name": REPOSITORY},
                    }
                )
            ],
            "which takes only",
        ),
        (
            [
                _pull(
                    head={
                        "ref": "develop",
                        "sha": HEAD_SHA,
                        "repo": {"full_name": "someone/fork"},
                    }
                )
            ],
            "which takes only",
        ),
    ],
)
def test_main_takes_only_the_promotion_of_this_repository_s_develop(
    tmp_path: Path, pulls: list[dict[str, Any]], named: str
) -> None:
    env = _github(
        tmp_path, pulls, [_run_entry(9, "2026-11-06T08:05:00Z")], {9: ARTIFACT}
    )

    proc = _find(env)

    assert proc.returncode == 1
    assert named in proc.stderr
    assert "::error" in proc.stderr


def test_a_promotion_merged_without_a_passing_run_fails(tmp_path: Path) -> None:
    other = {**_run_entry(9, "2026-11-06T08:05:00Z"), "head_branch": "feature/x"}
    env = _github(tmp_path, [_pull()], [other], {9: ARTIFACT})

    proc = _find(env)

    assert proc.returncode == 1
    assert "no successful ci.yml run" in proc.stderr


@pytest.mark.parametrize(
    "found", [[], [{"name": "tested-digests", "expired": True}], [{"name": "other"}]]
)
def test_a_run_without_its_record_fails(tmp_path: Path, found: list[Any]) -> None:
    env = _github(
        tmp_path, [_pull()], [_run_entry(9, "2026-11-06T08:05:00Z")], {9: found}
    )

    proc = _find(env)

    assert proc.returncode == 1
    assert "no unexpired tested-digests artifact" in proc.stderr


def test_an_api_error_fails_closed(tmp_path: Path) -> None:
    env = _github(tmp_path, {"message": "Not Found"}, [], {})

    proc = _find(env)

    assert proc.returncode == 1
    assert "not list" in proc.stderr


def _job(name: str, conclusion: str | None) -> dict[str, Any]:
    return {"name": name, "conclusion": conclusion}


@pytest.mark.parametrize(
    ("jobs", "found"),
    [
        # The run passed with the job skipped: nothing was tagged or recorded.
        ([_job("Lint", "success"), _job("Candidate tag", "skipped")], "(skipped)"),
        ([_job("Lint", "success")], "(no such job)"),
        ([_job("Candidate tag", None)], "(None)"),
        # Two jobs of that name: which one recorded is not known.
        (
            [_job("Candidate tag", "success"), _job("Candidate tag", "success")],
            "(success, success)",
        ),
        ([_job("Candidate tags", "success")], "(no such job)"),
    ],
)
def test_a_run_whose_candidate_tag_job_did_not_pass_fails(
    tmp_path: Path, jobs: list[dict[str, Any]], found: str
) -> None:
    # The artifact is there, so only the job's result can fail the run.
    env = _github(
        tmp_path,
        [_pull()],
        [_run_entry(9, "2026-11-06T08:05:00Z")],
        {9: ARTIFACT},
        {9: [jobs]},
    )

    proc = _find(env)

    assert proc.returncode == 1
    assert 'no successful "Candidate tag" job' in proc.stderr
    assert found in proc.stderr
    assert "::error" in proc.stderr
    assert proc.stdout == ""


def test_the_candidate_tag_job_is_found_on_a_later_page(tmp_path: Path) -> None:
    first = [_job(f"Image (golang, {index})", "success") for index in range(100)]
    env = _github(
        tmp_path,
        [_pull()],
        [_run_entry(9, "2026-11-06T08:05:00Z")],
        {9: ARTIFACT},
        {9: [first, [_job("Candidate tag", "success")]]},
    )

    proc = _find(env)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines()[0] == "run_id=9"


@pytest.mark.parametrize(
    "answer",
    [
        {"jobs": PASSED_JOBS},
        {"total_count": "3", "jobs": PASSED_JOBS},
        {"total_count": True, "jobs": PASSED_JOBS},
        {"total_count": 3, "jobs": {"name": "Candidate tag"}},
    ],
)
def test_a_jobs_answer_without_its_count_or_list_fails_closed(
    tmp_path: Path, answer: dict[str, Any]
) -> None:
    env = _github(
        tmp_path,
        [_pull()],
        [_run_entry(9, "2026-11-06T08:05:00Z")],
        {9: ARTIFACT},
        {9: [answer]},
    )

    proc = _find(env)

    assert proc.returncode == 1
    assert "has no jobs list and total_count" in proc.stderr
