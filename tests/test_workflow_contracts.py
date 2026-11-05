"""What the workflows promise each other, which neither actionlint nor a green
run shows: a required check that always reports, an aggregate that can fail, a
filter that covers its own workflow, a matrix that reaches the -aws stages.
"""

import json
import os
import re
import subprocess
import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
STRUCTURE_WORKFLOW = ".github/workflows/test-containers.yml"
METADATA_ACTION = "docker/metadata-action@"
PATHS_FILTER_ACTION = "dorny/paths-filter@"
# What a pre-commit hook runs, and so what no other workflow step may run.
LINTERS = (
    "ansible-lint",
    "detect-secrets",
    "hadolint",
    "pre-commit",
    "ruff",
    "shellcheck",
    "terraform fmt",
    "tflint",
    "yamllint",
)
# The executables whose package name differs from theirs.
LOCKED_EXECUTABLES = {"detect-secrets-hook": "detect-secrets"}
# Branch protection on develop and main requires these names (main also
# CodeQL Summary), each from exactly one job.
REQUIRED_CHECKS = {
    "CI Success": ("ci", "ci-success"),
    "Quality Summary": ("ci", "quality-summary"),
    "SBOM Verification Success": ("sbom-verification", "sbom-verification-success"),
    "Test Summary": ("test-containers", "summary"),
    "CodeQL Summary": ("codeql", "codeql-summary"),
}
GHCR_JOBS_OK = {
    "resolve_tags": "success",
    "cleanup_untagged": "success",
    "verify_protected_tags": "success",
    "report_tagged_cleanup_policy": "success",
}
AWS_IMAGES = {
    "terraform-aws": "devcontainers/terraform",
    "ansible-aws": "devcontainers/ansible",
}


def _workflow(name: str) -> dict[str, Any]:
    return yaml.safe_load((WORKFLOWS / f"{name}.yml").read_text(encoding="utf-8"))


def _all_workflows() -> dict[str, dict[str, Any]]:
    return {path.stem: _workflow(path.stem) for path in sorted(WORKFLOWS.glob("*.yml"))}


def _triggers(workflow: dict[str, Any]) -> dict[str, Any]:
    # YAML 1.1 reads the bare key `on` as the boolean true.
    return workflow[True]


def _step(job: dict[str, Any], name: str) -> dict[str, Any]:
    matches = [step for step in job["steps"] if step.get("name") == name]
    assert len(matches) == 1, name
    return matches[0]


def _run_scripts() -> Iterator[tuple[str, str, str, str]]:
    for workflow_name, workflow in _all_workflows().items():
        for job_name, job in workflow["jobs"].items():
            for step in job.get("steps", []):
                if "run" in step:
                    label = step.get("name", step["run"].splitlines()[0])
                    yield workflow_name, job_name, label, step["run"]


def _filters(workflow: str) -> dict[str, list[str]]:
    jobs = _workflow(workflow)["jobs"]
    steps = [
        step
        for job in jobs.values()
        for step in job.get("steps", [])
        if step.get("uses", "").startswith(PATHS_FILTER_ACTION)
    ]
    assert len(steps) == 1, workflow
    return yaml.safe_load(steps[0]["with"]["filters"])


def _run_summary(tmp_path: Path, **results: str) -> tuple[int, str, str]:
    job = _workflow("test-containers")["jobs"]["summary"]
    script = _step(job, "Check results")["run"]
    summary = tmp_path / "summary.md"
    needs = {
        name.replace("_", "-"): {"result": result, "outputs": {}}
        for name, result in results.items()
    }
    env = {
        **os.environ,
        "NEEDS_JSON": json.dumps(needs),
        "TEST_RESULT": results["test_containers"],
        "GITHUB_STEP_SUMMARY": str(summary),
    }
    proc = subprocess.run(
        ["bash", "-e", "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, summary.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("detect_changes", "test_containers"),
    [("success", "success"), ("success", "skipped")],
)
def test_structure_summary_allow_listed_results_pass(
    tmp_path: Path, detect_changes: str, test_containers: str
) -> None:
    returncode, stdout, _summary = _run_summary(
        tmp_path, detect_changes=detect_changes, test_containers=test_containers
    )

    assert returncode == 0, stdout


@pytest.mark.parametrize(
    ("detect_changes", "test_containers", "named"),
    [
        ("success", "failure", "test-containers (failure)"),
        ("success", "cancelled", "test-containers (cancelled)"),
        ("failure", "skipped", "detect-changes (failure)"),
        ("cancelled", "skipped", "detect-changes (cancelled)"),
        ("success", "neutral", "test-containers (neutral)"),
    ],
)
def test_structure_summary_anything_else_fails_and_names_the_job(
    tmp_path: Path, detect_changes: str, test_containers: str, named: str
) -> None:
    returncode, stdout, summary = _run_summary(
        tmp_path, detect_changes=detect_changes, test_containers=test_containers
    )

    assert returncode == 1
    assert named in stdout
    assert named in summary
    assert "passed" not in summary


def test_structure_summary_says_when_nothing_ran(tmp_path: Path) -> None:
    _returncode, _stdout, summary = _run_summary(
        tmp_path, detect_changes="success", test_containers="skipped"
    )

    assert "no structure test ran" in summary
    assert "passed" not in summary


def test_structure_summary_watches_the_filter_and_always_runs() -> None:
    job = _workflow("test-containers")["jobs"]["summary"]

    assert job["if"] == "always()"
    assert set(job["needs"]) == {"detect-changes", "test-containers"}


def test_structure_summary_name_is_unique_across_workflows() -> None:
    owners = [
        f"{workflow_name}:{job_name}"
        for workflow_name, workflow in _all_workflows().items()
        for job_name, job in workflow["jobs"].items()
        if job.get("name") == "Test Summary"
    ]

    assert owners == ["test-containers:summary"]


def test_structure_workflow_starts_on_every_change_of_a_branch() -> None:
    triggers = _triggers(_workflow("test-containers"))

    for event in ("pull_request", "push"):
        config = triggers[event] or {}
        assert "paths" not in config, event
        assert "paths-ignore" not in config, event


def test_structure_tests_skip_on_an_empty_filter_result() -> None:
    jobs = _workflow("test-containers")["jobs"]

    assert (
        jobs["test-containers"]["if"] == "needs.detect-changes.outputs.stacks != '[]'"
    )
    assert "steps.filter.outputs.changes" in jobs["detect-changes"]["outputs"]["stacks"]


def test_structure_filters_run_every_stack_on_a_change_to_the_workflow() -> None:
    filters = _filters("test-containers")

    assert filters
    for stack, patterns in filters.items():
        assert STRUCTURE_WORKFLOW in patterns, stack


def test_structure_dispatch_tests_exactly_the_filtered_stacks() -> None:
    jobs = _workflow("test-containers")["jobs"]
    stacks = jobs["detect-changes"]["outputs"]["stacks"]
    dispatch = re.search(r"'(\[[^']+\])'", stacks)

    assert dispatch is not None
    assert sorted(json.loads(dispatch.group(1))) == sorted(_filters("test-containers"))


@pytest.mark.parametrize("stack", sorted(_filters("test-containers")))
def test_structure_stack_gets_the_base_only_if_its_dockerfile_takes_it(
    tmp_path: Path, stack: str
) -> None:
    job = _workflow("test-containers")["jobs"]["test-containers"]
    output = tmp_path / "output"
    proc = subprocess.run(
        ["bash", "-e", "-c", _step(job, "Resolve the stack's files")["run"]],
        env={**os.environ, "STACK": stack, "GITHUB_OUTPUT": str(output)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    resolved = dict(
        line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines()
    )
    dockerfile = (REPO_ROOT / resolved["dockerfile"]).read_text(encoding="utf-8")
    takes_the_base = "FROM ${BASE_IMAGE}" in dockerfile
    assert resolved["base_from_run"] == str(takes_the_base).lower()
    if resolved["target"]:
        assert f" AS {resolved['target']}\n" in dockerfile
    for config in resolved["configs"].split():
        assert (REPO_ROOT / f"tests/container-structure/{config}.yaml").is_file()


def test_structure_builds_on_the_base_the_way_ci_gates_it() -> None:
    structure = _workflow("test-containers")["jobs"]["test-containers"]
    gate = _workflow("ci")["jobs"]["devcontainer-build"]

    base = _step(structure, "Build base for ${{ matrix.stack }}")["with"]
    gate_base = _step(gate, "Build base for ${{ matrix.stack }}${{ matrix.variant }}")[
        "with"
    ]
    for key in ("context", "file", "outputs", "build-args"):
        assert base[key] == gate_base[key], key

    stack = _step(structure, "Build ${{ matrix.stack }} container")["with"]
    assert "BASE_IMAGE=devcontainer-base" in stack["build-args"]
    assert "SOURCE_DATE_EPOCH=" in stack["build-args"]
    assert (
        "devcontainer-base=oci-layout://{0}/devcontainer-base"
        in stack["build-contexts"]
    )


def test_every_curl_retries_with_the_repository_flags() -> None:
    required = (
        "--proto '=https'",
        "--tlsv1.2",
        "-fsSL",
        "--retry 5",
        "--retry-delay 2",
        "--retry-max-time 120",
    )
    found = 0
    for workflow, job, step, script in _run_scripts():
        for line in script.replace("\\\n", " ").splitlines():
            if line.lstrip().startswith("#") or not re.search(r"\bcurl\s", line):
                continue
            found += 1
            for flag in required:
                assert flag in line, (workflow, job, step, flag)
    assert found


def test_jobs_only_read_matrix_keys_they_define() -> None:
    for workflow_name, workflow in _all_workflows().items():
        for job_name, job in workflow["jobs"].items():
            read = set(re.findall(r"\bmatrix\.([\w-]+)", json.dumps(job)))
            matrix = job.get("strategy", {}).get("matrix", {})
            include = matrix.get("include", []) if isinstance(matrix, dict) else ""
            if isinstance(include, str):
                # Built at run time, by a fromJSON: its keys are not in the file.
                continue
            defined = set(matrix)
            for entry in include:
                defined |= set(entry)
            assert read <= defined, (workflow_name, job_name, read - defined)


def test_jobs_name_their_ubuntu_release() -> None:
    # Renovate does not move runner labels, so an OS upgrade is a change made
    # by hand. release.yml's matrix takes its runners from release-images.py,
    # which tests/test_release_images.py pins.
    for workflow_name, workflow in _all_workflows().items():
        for job_name, job in workflow["jobs"].items():
            runs_on = str(job.get("runs-on", ""))
            assert "latest" not in runs_on, (workflow_name, job_name, runs_on)


def test_jobs_declare_a_timeout() -> None:
    for workflow_name, workflow in _all_workflows().items():
        for job_name, job in workflow["jobs"].items():
            if "uses" in job:
                continue
            assert "timeout-minutes" in job, (workflow_name, job_name)


@pytest.mark.parametrize(
    ("workflow", "job", "matrix_key", "name_prefix", "stage_key"),
    [
        ("sbom-verification", "generate-sbom", "target", "devcontainer-", "stage"),
    ],
)
def test_aws_images_are_measured_from_their_own_stage(
    workflow: str, job: str, matrix_key: str, name_prefix: str, stage_key: str
) -> None:
    entries = {
        entry["name"]: entry
        for entry in _workflow(workflow)["jobs"][job]["strategy"]["matrix"][matrix_key]
    }

    for image, directory in AWS_IMAGES.items():
        entry = entries[f"{name_prefix}{image}"]
        assert entry[stage_key] == image
        assert directory in entry.values()
        dockerfile = (REPO_ROOT / directory / "Dockerfile").read_text(encoding="utf-8")
        assert f" AS {image}\n" in dockerfile
    for name, entry in entries.items():
        if not name.endswith("-aws"):
            assert stage_key not in entry, name


def test_sbom_builds_pass_the_stage_to_buildx() -> None:
    sbom = _workflow("sbom-verification")["jobs"]["generate-sbom"]

    assert (
        _step(sbom, "Build container for SBOM")["with"]["target"]
        == "${{ matrix.target.stage }}"
    )


def test_ci_success_needs_every_job_but_the_quality_alias() -> None:
    jobs = _workflow("ci")["jobs"]
    needs = set(jobs["ci-success"]["needs"])

    assert {"devcontainer-state", "lint", "powershell-lint"} <= needs
    assert set(jobs) - needs - {"ci-success"} == {"quality-summary"}


def test_python_filter_covers_what_the_unit_tests_read() -> None:
    patterns = _filters("ci")["python"]

    for expected in (
        "pyproject.toml",
        "uv.lock",
        "Makefile",
        ".pre-commit-config.yaml",
        ".github/workflows/*.yml",
        ".github/image-size-budgets.json",
        ".devcontainer/Dockerfile*",
        ".devcontainer/**/devcontainer*.json",
        "devcontainers/*/Dockerfile*",
        "devcontainers/**/devcontainer*.json",
        "devcontainers/scripts/install-aws-cli.sh",
        "examples/*/.devcontainer/*.json",
    ):
        assert expected in patterns, expected


def test_python_filter_patterns_all_match_a_file() -> None:
    for pattern in _filters("ci")["python"]:
        assert next(REPO_ROOT.glob(pattern), None) is not None, pattern


@pytest.mark.parametrize(("workflow", "expected"), [("ci", 1), ("build-containers", 3)])
def test_every_image_label_versions_the_image_by_commit(
    workflow: str, expected: int
) -> None:
    steps = [
        step
        for job in _workflow(workflow)["jobs"].values()
        for step in job.get("steps", [])
        if step.get("uses", "").startswith(METADATA_ACTION)
    ]

    assert len(steps) == expected
    for step in steps:
        labels = step["with"]["labels"].splitlines()
        assert "org.opencontainers.image.version=sha-{{sha}}" in labels
        assert any(
            label.startswith("org.opencontainers.image.created=") for label in labels
        )


def test_case_statements_state_their_default() -> None:
    for name, job, step, script in _run_scripts():
        open_cases: list[bool] = []
        for line in script.splitlines():
            stripped = line.strip()
            if re.fullmatch(r"case\b.*\bin", stripped):
                open_cases.append(False)
            elif stripped.startswith("*)") and open_cases:
                open_cases[-1] = True
            elif re.match(r"esac\b", stripped):
                has_default = open_cases.pop()
                assert has_default, (name, job, step)
        assert not open_cases, (name, job, step)


@pytest.mark.parametrize("job", ["build-single", "build-all"])
@pytest.mark.parametrize(
    ("count", "returncode", "message"),
    [
        ("0", 0, ""),
        ("3", 1, "3 fixable"),
        ("", 1, "No usable Grype SARIF"),
        ("unknown", 1, "No usable Grype SARIF"),
    ],
)
def test_scan_gate_only_a_zero_count_passes(
    job: str, count: str, returncode: int, message: str
) -> None:
    gate = _step(
        _workflow("build-containers")["jobs"][job],
        "Fail when the image has fixable findings",
    )

    proc = subprocess.run(
        ["bash", "-e", "-c", gate["run"]],
        env={**os.environ, "COUNT": count, "IMAGE": "x", "EVENT_NAME": "push"},
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == returncode, proc.stdout
    assert message in proc.stdout


def _pre_commit_config() -> dict[str, Any]:
    text = (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(text)


def _locked_packages() -> set[str]:
    lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text(encoding="utf-8"))
    return {package["name"] for package in lock["package"]}


def _hook_command(entry: str) -> tuple[dict[str, str], list[str]]:
    """Split an `env NAME=value ... command` hook entry into its env and command."""
    words = entry.split()
    env: dict[str, str] = {}
    if words[0] == "env":
        words.pop(0)
        while "=" in words[0]:
            name, value = words.pop(0).split("=", 1)
            env[name] = value
    return env, words


def _hook(hook_id: str) -> dict[str, Any]:
    return next(
        hook
        for repo in _pre_commit_config()["repos"]
        for hook in repo["hooks"]
        if hook["id"] == hook_id
    )


def _make_recipe(target: str) -> list[str]:
    lines = (REPO_ROOT / "Makefile").read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"{target}:"))
    recipe = []
    for line in lines[start + 1 :]:
        if not line.startswith("\t"):
            break
        recipe.append(line.strip())
    return recipe


def _run_step(
    workflow: str, job: str, step: str, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    script = _step(_workflow(workflow)["jobs"][job], step)["run"]
    return subprocess.run(
        ["bash", "-e", "-c", script],
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        check=False,
    )


def test_lint_runs_pre_commit_on_every_event() -> None:
    workflow = _workflow("ci")
    job = workflow["jobs"]["lint"]
    runs = [step["run"] for step in job["steps"] if "run" in step]

    assert job["needs"] == "changes"
    assert "if" not in job
    assert "make lint-deps" in runs
    assert (
        "uv run --locked --no-build pre-commit run --all-files --show-diff-on-failure"
        in runs
    )
    for event in ("pull_request", "push"):
        config = _triggers(workflow)[event] or {}
        assert "paths" not in config, event
        assert "paths-ignore" not in config, event


def test_only_the_lint_job_runs_a_linter() -> None:
    for workflow, job, step, script in _run_scripts():
        if (workflow, job) == ("ci", "lint"):
            continue
        for line in script.splitlines():
            if line.lstrip().startswith("#"):
                continue
            for tool in LINTERS:
                pattern = rf"(^|[^\w-]){re.escape(tool)}([^\w-]|$)"
                assert not re.search(pattern, line), (workflow, job, step, tool)
    for workflow_name, workflow in _all_workflows().items():
        for job_name, job in workflow["jobs"].items():
            for step in job.get("steps", []):
                uses = step.get("uses", "")
                for tool in ("hadolint", "shellcheck", "yamllint", "ansible-lint"):
                    assert tool not in uses, (workflow_name, job_name, uses)


def test_make_lint_is_the_command_ci_runs() -> None:
    assert "@uv run --locked --no-build pre-commit run --all-files" in _make_recipe(
        "lint"
    )
    recipe = " ".join(_make_recipe("lint-deps"))
    assert "uv sync --locked --no-build" in recipe
    assert "devcontainers/ansible/install-collections.sh" in recipe
    assert "devcontainers/ansible/collections.txt" in recipe


def test_lint_installs_the_terraform_and_tflint_the_image_ships() -> None:
    jobs = _workflow("ci")["jobs"]
    outputs = jobs["changes"]["outputs"]
    lint = jobs["lint"]

    for tool in ("terraform", "tflint"):
        expected = f"${{{{ steps.toolchain.outputs.{tool}_version }}}}"
        assert outputs[f"{tool}_version"] == expected, tool
    terraform = _step(lint, "Set up Terraform")["with"]["terraform_version"]
    tflint = _step(lint, "Install tflint")
    assert terraform == "${{ needs.changes.outputs.terraform_version }}"
    assert (
        tflint["env"]["TFLINT_VERSION"] == "${{ needs.changes.outputs.tflint_version }}"
    )
    assert "sha256sum --check --strict" in tflint["run"]


def test_hooks_of_locked_tools_run_from_uv_lock() -> None:
    locked = _locked_packages()
    local = 0
    for repo in _pre_commit_config()["repos"]:
        for hook in repo["hooks"]:
            if repo["repo"] != "local":
                assert hook["id"] not in locked, (repo["repo"], hook["id"])
                continue
            local += 1
            _, entry = _hook_command(hook["entry"])
            assert entry[:4] == ["uv", "run", "--locked", "--no-build"], hook["id"]
            assert hook["language"] == "system", hook["id"]
            assert LOCKED_EXECUTABLES.get(entry[4], entry[4]) in locked, hook["id"]
    assert local


def test_ansible_lint_reads_only_the_collections_lint_deps_installs() -> None:
    env, _ = _hook_command(_hook("ansible-lint")["entry"])
    collections = env["ANSIBLE_COLLECTIONS_PATH"]
    recipe = " ".join(_make_recipe("lint-deps"))

    assert collections == f"{env['ANSIBLE_HOME']}/collections"
    assert f"rm -rf {collections} && mkdir -p {collections}" in recipe
    assert f"{collections} devcontainers/ansible/collections.txt" in recipe


def test_remote_hook_revs_are_frozen_commits() -> None:
    text = (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    revs = re.findall(r"^\s+rev: (\S+)(.*)$", text, re.MULTILINE)

    assert len(revs) == sum(
        1 for repo in _pre_commit_config()["repos"] if repo["repo"] != "local"
    )
    for rev, comment in revs:
        assert re.fullmatch(r"[0-9a-f]{40}", rev), rev
        assert re.fullmatch(r"\s+# frozen: v\S+", comment), rev


@pytest.mark.parametrize(("name", "owner"), sorted(REQUIRED_CHECKS.items()))
def test_required_check_has_one_producer_that_always_reports(
    name: str, owner: tuple[str, str]
) -> None:
    owners = [
        (workflow_name, job_name)
        for workflow_name, workflow in _all_workflows().items()
        for job_name, job in workflow["jobs"].items()
        if job.get("name") == name
    ]

    assert owners == [owner]
    workflow = _workflow(owner[0])
    assert workflow["jobs"][owner[1]]["if"] == "always()"
    for event in ("pull_request", "push"):
        config = _triggers(workflow)[event] or {}
        assert "paths" not in config, event
        assert "paths-ignore" not in config, event


def test_quality_summary_aliases_lint() -> None:
    job = _workflow("ci")["jobs"]["quality-summary"]

    assert job["needs"] == "lint"
    assert _step(job, "Check results")["env"] == {
        "LINT_RESULT": "${{ needs.lint.result }}"
    }


def test_quality_summary_passes_when_lint_passed() -> None:
    proc = _run_step(
        "ci", "quality-summary", "Check results", {"LINT_RESULT": "success"}
    )

    assert proc.returncode == 0, proc.stdout


@pytest.mark.parametrize("lint", ["failure", "cancelled", "skipped", ""])
def test_quality_summary_fails_on_anything_else(lint: str) -> None:
    proc = _run_step("ci", "quality-summary", "Check results", {"LINT_RESULT": lint})

    assert proc.returncode == 1
    assert "Lint did not pass" in proc.stdout


def _ghcr_report(
    tmp_path: Path, dry_run: str = "false", **results: str
) -> tuple[int, str, str]:
    summary = tmp_path / "summary.md"
    needs = {
        name.replace("_", "-"): {"result": result, "outputs": {}}
        for name, result in results.items()
    }
    proc = _run_step(
        "cleanup-ghcr",
        "report",
        "Report results",
        {
            "NEEDS_JSON": json.dumps(needs),
            "DRY_RUN": dry_run,
            "GITHUB_STEP_SUMMARY": str(summary),
        },
    )
    return proc.returncode, proc.stdout, summary.read_text(encoding="utf-8")


def test_ghcr_report_needs_every_other_job() -> None:
    jobs = _workflow("cleanup-ghcr")["jobs"]

    assert jobs["report"]["if"] == "always()"
    assert set(jobs["report"]["needs"]) == set(jobs) - {"report"}
    assert {name.replace("_", "-") for name in GHCR_JOBS_OK} == set(jobs) - {"report"}


def test_ghcr_report_says_completed_only_when_every_job_succeeded(
    tmp_path: Path,
) -> None:
    returncode, stdout, summary = _ghcr_report(tmp_path, **GHCR_JOBS_OK)

    assert returncode == 0, stdout
    assert "Cleanup completed" in summary
    assert "Dry run" not in summary


def test_ghcr_report_says_when_it_was_a_dry_run(tmp_path: Path) -> None:
    returncode, stdout, summary = _ghcr_report(tmp_path, dry_run="true", **GHCR_JOBS_OK)

    assert returncode == 0, stdout
    assert "Dry run completed: nothing was deleted" in summary


@pytest.mark.parametrize(
    ("job", "result"),
    [
        ("cleanup_untagged", "failure"),
        ("verify_protected_tags", "skipped"),
        ("resolve_tags", "cancelled"),
    ],
)
def test_ghcr_report_fails_and_names_a_job_that_did_not_succeed(
    tmp_path: Path, job: str, result: str
) -> None:
    returncode, stdout, summary = _ghcr_report(
        tmp_path, **{**GHCR_JOBS_OK, job: result}
    )
    named = f"{job.replace('_', '-')} ({result})"

    assert returncode == 1
    assert named in stdout
    assert named in summary
    assert "✅" not in summary


def test_ghcr_report_states_the_configured_retention() -> None:
    jobs = _workflow("cleanup-ghcr")["jobs"]
    cleanup = next(
        step
        for step in jobs["cleanup-untagged"]["steps"]
        if "ghcr-cleanup-action" in step.get("uses", "")
    )
    report = _step(jobs["report"], "Report results")["run"]

    assert f"older-than: {cleanup['with']['older-than']}" in report
    assert "keep-n-untagged" not in cleanup["with"]
    assert "Keep last" not in report


def test_jobs_only_test_for_events_their_workflow_declares() -> None:
    for name, workflow in _all_workflows().items():
        triggers = _triggers(workflow)
        declared = {triggers} if isinstance(triggers, str) else set(triggers)
        text = (WORKFLOWS / f"{name}.yml").read_text(encoding="utf-8")
        for event in re.findall(r"github\.event_name\s*[!=]=\s*'([a-z_]+)'", text):
            assert event in declared, (name, event)
