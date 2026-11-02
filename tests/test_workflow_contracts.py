"""What the workflows promise each other, which neither actionlint nor a green
run shows: a required check that always reports, an aggregate that can fail, a
filter that covers its own workflow, a matrix that reaches the -aws stages.
"""

import json
import os
import re
import subprocess
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


def test_resource_benchmark_reads_the_cache_of_the_active_template() -> None:
    job = _workflow("benchmark")["jobs"]["resource-usage-benchmark"]
    script = _step(job, "Resolve registry cache")["run"]

    assert ".devcontainer/.template-metadata.json" in script
    assert 'devcontainer-${STACK}:buildcache-publish"' in script


@pytest.mark.parametrize(
    ("workflow", "job", "matrix_key", "name_prefix", "stage_key"),
    [
        ("sbom-verification", "generate-sbom", "target", "devcontainer-", "stage"),
        ("benchmark", "container-startup-benchmark", "container", "", "target"),
        ("benchmark", "build-time-benchmark", "container", "", "target"),
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


def test_sbom_and_startup_builds_pass_the_stage_to_buildx() -> None:
    sbom = _workflow("sbom-verification")["jobs"]["generate-sbom"]
    startup = _workflow("benchmark")["jobs"]["container-startup-benchmark"]

    assert (
        _step(sbom, "Build container for SBOM")["with"]["target"]
        == "${{ matrix.target.stage }}"
    )
    assert (
        _step(startup, "Build container")["with"]["target"]
        == "${{ matrix.container.target }}"
    )


@pytest.mark.parametrize(
    "step",
    ["Benchmark build time (cold cache)", "Benchmark build time (warm cache)"],
)
def test_build_time_benchmarks_pass_the_stage_to_buildx(step: str) -> None:
    job = _workflow("benchmark")["jobs"]["build-time-benchmark"]
    benchmark = _step(job, step)

    assert "matrix.container.target" in benchmark["env"]["TARGET_ARGS"]
    assert '"${TARGET_FLAGS[@]}"' in benchmark["run"]


def test_benchmarks_run_when_the_aws_lock_export_changes() -> None:
    triggers = _triggers(_workflow("benchmark"))

    for event in ("pull_request", "push"):
        assert "requirements-aws.txt" in triggers[event]["paths"], event


def test_ci_success_needs_every_job_but_the_advisory_scan() -> None:
    jobs = _workflow("ci")["jobs"]
    needs = set(jobs["ci-success"]["needs"])

    assert "devcontainer-state" in needs
    assert set(jobs) - needs - {"ci-success"} == {"security"}


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
                assert open_cases.pop(), (name, job, step)
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
