"""What the workflows promise each other, which neither actionlint nor a green
run shows: a required check that always reports, an aggregate that can fail, a
filter that covers its own workflow, a matrix that reaches the -aws stages.
"""

import fnmatch
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
CI_WORKFLOW = ".github/workflows/ci.yml"
METADATA_ACTION = "docker/metadata-action@"
PATHS_FILTER_ACTION = "dorny/paths-filter@"
BUILD_PUSH_ACTION = "docker/build-push-action@"
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
    "SBOM Verification Success": ("ci", "sbom-verification-success"),
    "Test Summary": ("ci", "test-summary"),
    "CodeQL Summary": ("codeql", "codeql-summary"),
}
# ci.yml's jobs that only repeat other jobs' results under a required name.
REQUIRED_CHECK_ALIASES = {
    "quality-summary",
    "test-summary",
    "sbom-verification-success",
}
# The aliases of the image jobs, and the jobs each one reports on.
IMAGE_SUMMARIES = ("test-summary", "sbom-verification-success")
IMAGE_SUMMARY_NEEDS = [
    "changes",
    "lint",
    "base",
    "candidate-base",
    "candidate-build",
    "image",
    "candidate-tag",
]
# The jobs that push to GHCR, from a pull_request run in candidate mode and
# from a dispatch or a schedule in nightly mode, and only then.
CANDIDATE_JOBS = ("candidate-base", "candidate-build", "candidate-tag")
PUSHED_MODES = 'fromJSON(\'["candidate", "nightly"]\')'
CANDIDATE_IF = f"contains({PUSHED_MODES}, needs.changes.outputs.mode)"
# The legs' condition for testing a pushed candidate digest.
PULLED_IF = f"contains({PUSHED_MODES}, env.MODE)"
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
REPOSITORY = "malpanez/ansible-devcontainer-vscode"


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


def _filters(workflow: str) -> dict[str, list[Any]]:
    jobs = _workflow(workflow)["jobs"]
    steps = [
        step
        for job in jobs.values()
        for step in job.get("steps", [])
        if step.get("uses", "").startswith(PATHS_FILTER_ACTION)
    ]
    assert len(steps) == 1, workflow
    return yaml.safe_load(steps[0]["with"]["filters"])


def _patterns(entries: list[Any]) -> list[str]:
    """A filter's patterns, with the lists its YAML anchors bring in flattened,
    as paths-filter flattens them."""
    flat: list[str] = []
    for entry in entries:
        flat.extend(_patterns(entry) if isinstance(entry, list) else [entry])
    return flat


def _image_filters() -> dict[str, list[str]]:
    """The image-<name> filters of ci.yml, by image name."""
    return {
        name.removeprefix("image-"): _patterns(entries)
        for name, entries in _filters("ci").items()
        if name.startswith("image-")
    }


def _matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def _run_step(
    workflow: str, job: str, step: str, env: dict[str, str], cwd: Path = REPO_ROOT
) -> subprocess.CompletedProcess[str]:
    script = _step(_workflow(workflow)["jobs"][job], step)["run"]
    return subprocess.run(
        ["bash", "-e", "-c", script],
        env={**_clean_environ(), **env},
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _clean_environ() -> dict[str, str]:
    """os.environ without what would point git at another repository, as a git
    hook running these tests would."""
    return {
        key: value
        for key, value in os.environ.items()
        if key not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"}
    }


def _outputs(path: Path) -> dict[str, str]:
    return dict(
        line.split("=", 1) for line in path.read_text(encoding="utf-8").splitlines()
    )


def _stub(bin_dir: Path, name: str, body: str) -> None:
    bin_dir.mkdir(exist_ok=True)
    path = bin_dir / name
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _run_summary(
    tmp_path: Path, job: str, results: dict[str, str], event: str = "pull_request"
) -> tuple[int, str, str]:
    script = _step(_workflow("ci")["jobs"][job], "Check results")["run"]
    summary = tmp_path / "summary.md"
    needs = {
        name: {"result": result, "outputs": {}} for name, result in results.items()
    }
    env = {
        **os.environ,
        "NEEDS_JSON": json.dumps(needs),
        "BASE_RESULT": results["base"],
        "IMAGE_RESULT": results["image"],
        "EVENT_NAME": event,
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


def _results(**results: str) -> dict[str, str]:
    return {"changes": "success", "lint": "success", **results}


@pytest.mark.parametrize("job", IMAGE_SUMMARIES)
@pytest.mark.parametrize(
    ("base", "image"),
    [("success", "success"), ("skipped", "success"), ("skipped", "skipped")],
)
def test_image_summaries_allow_listed_results_pass(
    tmp_path: Path, job: str, base: str, image: str
) -> None:
    returncode, stdout, _summary = _run_summary(
        tmp_path, job, _results(base=base, image=image)
    )

    assert returncode == 0, stdout


@pytest.mark.parametrize("job", IMAGE_SUMMARIES)
@pytest.mark.parametrize(
    ("results", "named"),
    [
        (_results(base="success", image="failure"), "image (failure)"),
        (_results(base="skipped", image="cancelled"), "image (cancelled)"),
        (_results(base="failure", image="skipped"), "base (failure)"),
        (_results(base="success", image="neutral"), "image (neutral)"),
        (
            _results(
                changes="failure", lint="skipped", base="skipped", image="skipped"
            ),
            "changes (failure)",
        ),
        (_results(lint="failure", base="skipped", image="skipped"), "lint (failure)"),
        (
            _results(lint="cancelled", base="skipped", image="skipped"),
            "lint (cancelled)",
        ),
    ],
)
def test_image_summaries_anything_else_fails_and_names_the_job(
    tmp_path: Path, job: str, results: dict[str, str], named: str
) -> None:
    returncode, stdout, summary = _run_summary(tmp_path, job, results)

    assert returncode == 1
    assert named in stdout
    assert named in summary
    assert "✅" not in summary


@pytest.mark.parametrize("job", IMAGE_SUMMARIES)
def test_image_summaries_say_when_nothing_ran(tmp_path: Path, job: str) -> None:
    _returncode, _stdout, summary = _run_summary(
        tmp_path, job, _results(base="skipped", image="skipped")
    )

    assert "No image changed" in summary
    assert "✅" not in summary


@pytest.mark.parametrize("job", IMAGE_SUMMARIES)
def test_image_summaries_say_a_push_tests_no_image(tmp_path: Path, job: str) -> None:
    returncode, _stdout, summary = _run_summary(
        tmp_path, job, _results(base="skipped", image="skipped"), event="push"
    )

    assert returncode == 0
    assert "A push tests no image" in summary
    assert "No image changed" not in summary


@pytest.mark.parametrize("job", IMAGE_SUMMARIES)
def test_image_summaries_watch_the_filter_and_lint_and_always_run(job: str) -> None:
    summary = _workflow("ci")["jobs"][job]

    assert summary["if"] == "always()"
    assert summary["needs"] == IMAGE_SUMMARY_NEEDS


def test_test_summary_name_is_unique_across_workflows() -> None:
    owners = [
        f"{workflow_name}:{job_name}"
        for workflow_name, workflow in _all_workflows().items()
        for job_name, job in workflow["jobs"].items()
        if job.get("name") == "Test Summary"
    ]

    assert owners == ["ci:test-summary"]


def test_image_jobs_skip_on_an_empty_image_list() -> None:
    jobs = _workflow("ci")["jobs"]
    outputs = jobs["changes"]["outputs"]

    assert outputs["images"] == "${{ steps.images.outputs.images }}"
    assert outputs["base"] == "${{ steps.images.outputs.base }}"
    assert outputs["legs"] == "${{ steps.legs.outputs.legs }}"
    assert jobs["base"]["if"] == (
        "needs.changes.outputs.mode == 'verification' && needs.changes.outputs.base == 'true'"
    )
    condition = jobs["image"]["if"]
    assert "needs.changes.outputs.legs != '[]'" in condition
    assert "needs.changes.result == 'success'" in condition
    assert "needs.lint.result == 'success'" in condition
    # A base skipped because no image in the list takes it, or failed on a
    # check of its own, must not skip the rest: the implicit success() would
    # (actions/runner#2205). An image built on base fails at its layout check.
    assert condition.startswith("!cancelled()")
    assert "needs.base" not in condition
    assert "needs.candidate" not in condition
    assert {"base", "candidate-base", "candidate-build"} <= set(jobs["image"]["needs"])
    assert jobs["image"]["strategy"]["matrix"] == {
        "include": "${{ fromJSON(needs.changes.outputs.legs) }}"
    }


def _resolve_images(
    tmp_path: Path, event: str, changes: str, mode: str = "verification"
) -> dict[str, str]:
    output = tmp_path / "output"
    proc = _run_step(
        "ci",
        "changes",
        "Resolve the images to test",
        {
            "MODE": mode,
            "GITHUB_EVENT_NAME": event,
            "CHANGES": changes,
            "GITHUB_OUTPUT": str(output),
        },
    )
    assert proc.returncode == 0, proc.stderr
    return _outputs(output)


@pytest.mark.parametrize(
    "changes", ["[]", '["image-base","image-golang"]', '["images-all"]']
)
def test_a_push_tests_no_image(tmp_path: Path, changes: str) -> None:
    resolved = _resolve_images(tmp_path, "push", changes)

    assert resolved["images"] == "[]"
    assert resolved["base"] == "false"


def test_dispatch_tests_every_image_with_a_filter(tmp_path: Path) -> None:
    resolved = _resolve_images(tmp_path, "workflow_dispatch", "")
    images = sorted(set(_image_filters()) - {"base"})

    assert sorted(json.loads(resolved["images"])) == images
    assert resolved["base"] == "true"


@pytest.mark.parametrize(
    ("changes", "images", "base"),
    [
        ("[]", [], "false"),
        ('["python","scripts"]', [], "false"),
        (
            '["images-all","image-latex","python","image-golang"]',
            ["golang", "latex"],
            "false",
        ),
        ('["image-base"]', [], "true"),
        ('["image-ansible-aws"]', ["ansible-aws"], "true"),
        (
            '["image-ansible-podman","image-terraform-aws"]',
            ["ansible-podman", "terraform-aws"],
            "false",
        ),
    ],
)
def test_images_are_the_matched_image_filters(
    tmp_path: Path, changes: str, images: list[str], base: str
) -> None:
    resolved = _resolve_images(tmp_path, "pull_request", changes)

    assert sorted(json.loads(resolved["images"])) == images
    assert resolved["base"] == base


def test_image_filters_run_every_image_on_a_change_to_how_images_are_tested() -> None:
    filters = _filters("ci")
    shared = _patterns(filters["images-all"])

    for path in (
        CI_WORKFLOW,
        ".grype.yaml",
        ".github/image-size-budgets.json",
        "tests/container-structure/base.yaml",
        "scripts/check-image-size.py",
        "scripts/test-devcontainer-profile.sh",
        "scripts/assert-image-id.sh",
        "scripts/devcontainers-cli/package-lock.json",
    ):
        assert _matches(path, shared), path
    assert set(_image_filters()) == {
        "base",
        "ansible",
        "ansible-podman",
        "ansible-aws",
        "terraform",
        "terraform-aws",
        "golang",
        "latex",
    }
    for image, patterns in _image_filters().items():
        assert set(shared) <= set(patterns), image
    assert set(shared) <= set(_patterns(filters["devcontainer"]))


def test_image_filter_patterns_all_match_a_file() -> None:
    for name, entries in _filters("ci").items():
        if name == "images-all" or name.startswith("image-"):
            for pattern in _patterns(entries):
                assert next(REPO_ROOT.glob(pattern), None) is not None, (name, pattern)


def _scripts_run(step: dict[str, Any]) -> set[str]:
    return set(re.findall(r"\bscripts/[\w./-]+\.(?:sh|py)\b", step.get("run", "")))


def test_each_image_filter_covers_the_scripts_its_job_runs() -> None:
    jobs = _workflow("ci")["jobs"]
    filters = _image_filters()
    everything = sorted(filters)
    stacks = sorted(set(filters) - {"base"})
    steps = [
        *(
            (step, ["base"])
            for job in ("base", "candidate-base")
            for step in jobs[job]["steps"]
        ),
        # The image job tests base too, in candidate mode.
        *((step, everything) for step in jobs["image"]["steps"]),
        *((step, stacks) for step in jobs["candidate-build"]["steps"]),
        # Which legs run, and how a candidate is tagged. tested-digests.py runs
        # in every candidate run, whatever changed, so it is no image input.
        (_step(jobs["changes"], "Resolve the image legs"), everything),
        (_step(jobs["candidate-tag"], "Tag the tested digests"), everything),
    ]
    for step, images in steps:
        only = re.findall(r"matrix\.image == '([\w-]+)'", step.get("if", ""))
        for image in only or images:
            for script in _scripts_run(step):
                assert _matches(script, filters[image]), (
                    step.get("name"),
                    image,
                    script,
                )


def _resolve_files(tmp_path: Path, image: str) -> dict[str, str]:
    output = tmp_path / f"files-{image}"
    proc = _run_step(
        "ci",
        "image",
        "Resolve the image's files",
        {"IMAGE": image, "GITHUB_OUTPUT": str(output)},
    )
    assert proc.returncode == 0, proc.stderr
    return _outputs(output)


@pytest.mark.parametrize("image", sorted(set(_image_filters()) - {"base"}))
def test_image_gets_the_base_only_if_its_dockerfile_takes_it(
    tmp_path: Path, image: str
) -> None:
    resolved = _resolve_files(tmp_path, image)

    dockerfile = (REPO_ROOT / resolved["dockerfile"]).read_text(encoding="utf-8")
    takes_the_base = "FROM ${BASE_IMAGE}" in dockerfile
    assert resolved["base_from_run"] == str(takes_the_base).lower()
    if resolved["target"]:
        assert f" AS {resolved['target']}\n" in dockerfile
    for config in resolved["configs"].split():
        assert (REPO_ROOT / f"tests/container-structure/{config}.yaml").is_file()
    # The base job runs exactly when an image built on it is in the list.
    changes = json.dumps([f"image-{image}"])
    assert (
        _resolve_images(tmp_path, "pull_request", changes)["base"]
        == (resolved["base_from_run"])
    )
    if resolved["template"] == "true":
        assert (REPO_ROOT / f"devcontainers/{image}/devcontainer.json").is_file()


def test_base_is_tested_with_its_own_structure_tests(tmp_path: Path) -> None:
    resolved = _resolve_files(tmp_path, "base")

    assert resolved == {
        "dockerfile": "devcontainers/base/Dockerfile",
        "target": "",
        "configs": "base",
        "base_from_run": "false",
        "template": "false",
        "cli": "false",
    }


@pytest.mark.parametrize("image", sorted(set(_image_filters()) - {"base"}))
def test_aws_images_are_built_from_their_own_stage(tmp_path: Path, image: str) -> None:
    resolved = _resolve_files(tmp_path, image)

    if image in AWS_IMAGES:
        assert resolved["target"] == image
        assert resolved["dockerfile"] == f"{AWS_IMAGES[image]}/Dockerfile"
        assert resolved["configs"].split()[-1] == image
    else:
        assert resolved["target"] == ""


def _dockerfile_instructions(text: str) -> list[tuple[str, list[str]]]:
    """(keyword, arguments) per instruction. Comment lines go first, as Docker
    drops them even inside a continued RUN; then continuations are joined."""
    lines = [line for line in text.splitlines() if not line.lstrip().startswith("#")]
    joined = re.sub(r"\\\n", " ", "\n".join(lines))
    return [
        (words[0].upper(), words[1:])
        for words in (line.split() for line in joined.splitlines())
        if words
    ]


def _context_reads(dockerfile: str, target: str) -> set[str]:
    """The build-context paths that the stages building target read: COPY and
    ADD sources and bind mounts, except those taken from another stage or
    image. An empty target is the last stage."""
    names: list[str] = []
    needs: list[set[str]] = []
    reads: list[set[str]] = []
    for keyword, args in _dockerfile_instructions(dockerfile):
        flags: list[str] = []
        for arg in args:
            if not arg.startswith("--"):
                break
            flags.append(arg)
        rest = args[len(flags) :]
        if keyword == "FROM":
            named = len(rest) == 3 and rest[1].upper() == "AS"
            names.append(rest[2].lower() if named else "")
            needs.append({rest[0].lower()})
            reads.append(set())
            continue
        for flag in flags:
            key, _, value = flag[2:].partition("=")
            if key == "from":
                needs[-1].add(value.lower())
            elif key == "mount":
                mount = dict(option.split("=", 1) for option in value.split(","))
                if mount.get("type", "bind") != "bind":
                    continue
                if "from" in mount:
                    needs[-1].add(mount["from"].lower())
                else:
                    reads[-1].add(mount.get("source", mount.get("src", ".")))
        if keyword in ("COPY", "ADD") and not any(
            f.startswith("--from=") for f in flags
        ):
            assert not rest[0].startswith(("[", "<<")), f"unparsed: {keyword} {rest}"
            reads[-1].update(rest[:-1])

    stages = {name: index for index, name in enumerate(names) if name}
    todo = [stages[target] if target else len(names) - 1]
    built: set[int] = set()
    while todo:
        stage = todo.pop()
        if stage not in built:
            built.add(stage)
            todo.extend(stages[need] for need in needs[stage] if need in stages)
    return set().union(*(reads[stage] for stage in built))


@pytest.mark.parametrize("image", sorted(_image_filters()))
def test_each_image_filter_covers_what_its_dockerfile_reads(
    tmp_path: Path, image: str
) -> None:
    # A path the filter misses skips the image on a change to that path, and
    # the summaries pass a skipped image: the change goes green untested.
    base = ("devcontainers/base/Dockerfile", "")
    builds = [base]
    if image != "base":
        resolved = _resolve_files(tmp_path, image)
        builds = [(resolved["dockerfile"], resolved["target"])]
        if resolved["base_from_run"] == "true":
            builds.append(base)
    patterns = _image_filters()[image]

    for dockerfile, target in builds:
        assert _matches(dockerfile, patterns), (image, dockerfile)
        text = (REPO_ROOT / dockerfile).read_text(encoding="utf-8")
        for source in _context_reads(text, target):
            if "://" in source:
                continue
            assert "$" not in source, f"{dockerfile} reads {source}: resolve it here"
            files = [
                path
                for found in REPO_ROOT.glob(source)
                for path in ([found] if found.is_file() else found.rglob("*"))
                if path.is_file()
            ]
            assert files, (dockerfile, source)
            for path in files:
                relative = path.relative_to(REPO_ROOT).as_posix()
                assert _matches(relative, patterns), (image, dockerfile, relative)


def test_image_builds_pass_the_target_to_buildx() -> None:
    build = _step(_workflow("ci")["jobs"]["image"], "Build ${{ matrix.image }}")["with"]

    assert build["file"] == "${{ steps.files.outputs.dockerfile }}"
    assert build["target"] == "${{ steps.files.outputs.target }}"
    assert build["platforms"] == "linux/amd64"
    assert build["push"] is False


def test_children_build_on_the_base_this_run_built() -> None:
    jobs = _workflow("ci")["jobs"]
    base = jobs["base"]
    image = jobs["image"]

    assert base["outputs"]["digest"] == "${{ steps.layout.outputs.digest }}"
    built = _step(base, "Build base")["with"]
    outputs = built["outputs"].splitlines()
    assert (
        "type=oci,dest=${{ runner.temp }}/devcontainer-base,tar=false,rewrite-timestamp=true"
        in outputs
    )
    assert "type=docker,name=${{ env.IMAGE_REF }},rewrite-timestamp=true" in outputs
    assert built["build-args"] == "SOURCE_DATE_EPOCH=${{ steps.epoch.outputs.epoch }}"
    assert built["provenance"] is False
    # Read-only: build-base in build-containers.yml is the cache's one writer.
    assert "cache-to" not in built
    uploaded = _step(base, "Upload the base layout")["with"]
    downloaded = _step(image, "Download the base layout")["with"]
    assert uploaded["name"] == downloaded["name"]
    assert uploaded["path"] == downloaded["path"]
    check = _step(image, "Check the base layout")
    assert check["env"]["EXPECTED"] == "${{ needs.base.outputs.digest }}"
    gate = _step(image, "Check this run built the base")
    assert gate["if"] == (
        "env.MODE == 'verification' && steps.files.outputs.base_from_run == 'true'"
        " && needs.base.result != 'success'"
    )
    names = [step.get("name") for step in image["steps"]]
    assert names.index("Check this run built the base") < names.index(
        "Download the base layout"
    )

    stack = _step(image, "Build ${{ matrix.image }}")["with"]
    assert "BASE_IMAGE=devcontainer-base" in stack["build-args"]
    assert "SOURCE_DATE_EPOCH=" in stack["build-args"]
    assert (
        "devcontainer-base=oci-layout://{0}/devcontainer-base@{1}', runner.temp, "
        "needs.base.outputs.digest" in stack["build-contexts"]
    )


def _oci_layout(root: Path, blobs: dict[str, bytes], index: list[str]) -> None:
    store = root / "blobs" / "sha256"
    store.mkdir(parents=True)
    for digest, content in blobs.items():
        (store / digest.removeprefix("sha256:")).write_bytes(content)
    (root / "oci-layout").write_text('{"imageLayoutVersion": "1.0.0"}')
    (root / "index.json").write_text(
        json.dumps({"schemaVersion": 2, "manifests": [{"digest": d} for d in index]})
    )


def _blob(content: dict[str, Any]) -> tuple[str, bytes]:
    data = json.dumps(content).encode()
    return f"sha256:{hashlib.sha256(data).hexdigest()}", data


def _base_layout(root: Path, diff_ids: list[str]) -> str:
    config, config_data = _blob({"rootfs": {"type": "layers", "diff_ids": diff_ids}})
    manifest, manifest_data = _blob({"schemaVersion": 2, "config": {"digest": config}})
    _oci_layout(root, {config: config_data, manifest: manifest_data}, [manifest])
    return manifest


def test_children_take_only_the_layout_the_base_job_built(tmp_path: Path) -> None:
    layout = tmp_path / "devcontainer-base"
    manifest = _base_layout(layout, ["sha256:" + "1" * 64])

    def check(expected: str) -> subprocess.CompletedProcess[str]:
        return _run_step(
            "ci",
            "image",
            "Check the base layout",
            {"EXPECTED": expected, "LAYOUT": str(layout)},
        )

    assert check(manifest).returncode == 0, check(manifest).stdout
    other = "sha256:" + "f" * 64
    assert check(other).returncode == 1
    assert check("").returncode == 1
    (layout / "blobs" / "sha256" / manifest.removeprefix("sha256:")).write_text("{}")
    assert check(manifest).returncode != 0


FAKE_INSPECT = """#!/usr/bin/env bash
case "$4" in
  '{{json .RootFS.Layers}}') printf '%s\\n' "${FAKE_LAYERS}" ;;
  '{{.Id}}') printf '%s\\n' "${FAKE_ID}" ;;
  *) exit 1 ;;
esac
"""


@pytest.mark.parametrize("same_layers", [True, False])
def test_the_base_checks_run_on_the_layout_s_image(
    tmp_path: Path, same_layers: bool
) -> None:
    layout = tmp_path / "devcontainer-base"
    diff_ids = ["sha256:" + "1" * 64, "sha256:" + "2" * 64]
    manifest = _base_layout(layout, diff_ids)
    _stub(tmp_path / "bin", "docker", FAKE_INSPECT)
    output = tmp_path / "output"
    loaded = diff_ids if same_layers else diff_ids[:1]

    proc = _run_step(
        "ci",
        "base",
        "Check the loaded base is the layout's image",
        {
            "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}",
            "LAYOUT": str(layout),
            "IMAGE_REF": "devcontainer-base:ci",
            "FAKE_LAYERS": json.dumps(loaded),
            "FAKE_ID": "sha256:" + "c" * 64,
            "GITHUB_OUTPUT": str(output),
        },
    )

    if same_layers:
        assert proc.returncode == 0, proc.stdout
        assert _outputs(output) == {"digest": manifest, "id": "sha256:" + "c" * 64}
    else:
        assert proc.returncode == 1
        assert not output.exists()


FAKE_BUILDX = """#!/usr/bin/env bash
[[ -n "${FAKE_CACHE_EXISTS}" ]]
"""


def _cache_strategy(
    tmp_path: Path, event: str, head_repo: str, cache_exists: bool = True
) -> dict[str, str]:
    _stub(tmp_path / "bin", "docker", FAKE_BUILDX)
    output = tmp_path / "output"
    proc = _run_step(
        "ci",
        "image",
        "Determine cache strategy",
        {
            "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}",
            "FAKE_CACHE_EXISTS": "1" if cache_exists else "",
            "GITHUB_EVENT_NAME": event,
            "HEAD_REPO": head_repo,
            "GITHUB_REPOSITORY": REPOSITORY,
            "GITHUB_REPOSITORY_OWNER": "malpanez",
            "IMAGE": "golang",
            "GITHUB_OUTPUT": str(output),
        },
    )
    assert proc.returncode == 0, proc.stderr
    return _outputs(output)


REGISTRY_CACHE = "type=registry,ref=ghcr.io/malpanez/devcontainer-golang:buildcache"


@pytest.mark.parametrize(
    ("event", "head_repo"),
    [
        ("pull_request", REPOSITORY),
        ("pull_request", "someone/ansible-devcontainer-vscode"),
        ("workflow_dispatch", ""),
        ("push", ""),
    ],
)
def test_verification_never_writes_the_registry_cache(
    tmp_path: Path, event: str, head_repo: str
) -> None:
    # :buildcache has one writer, candidate mode. A push builds nothing now,
    # and wrote it before 2c.
    cache = _cache_strategy(tmp_path, event, head_repo)

    assert "type=registry" not in cache["cache_to"]
    assert "login" not in cache


def test_a_pull_request_from_this_repository_reads_the_registry_cache(
    tmp_path: Path,
) -> None:
    cache = _cache_strategy(tmp_path, "pull_request", REPOSITORY)

    assert cache["cache_from"] == REGISTRY_CACHE
    assert cache["cache_to"] == ""


def test_a_fork_keeps_the_actions_cache(tmp_path: Path) -> None:
    cache = _cache_strategy(tmp_path, "pull_request", "someone/fork")

    assert cache["cache_from"] == "type=gha,scope=golang"
    assert cache["cache_to"] == "type=gha,scope=golang"


def test_a_missing_registry_cache_is_not_read(tmp_path: Path) -> None:
    cache = _cache_strategy(tmp_path, "pull_request", REPOSITORY, cache_exists=False)

    assert cache["cache_from"] == ""
    assert cache["cache_to"] == ""


CANDIDATE_CACHE = (
    "type=registry,ref=ghcr.io/${{ github.repository_owner }}/devcontainer-%s"
    ":buildcache,mode=max,ignore-error=true"
)


@pytest.mark.parametrize(
    ("job", "image"),
    [("candidate-base", "base"), ("candidate-build", "${{ matrix.image }}")],
)
def test_candidates_build_uncached_and_write_only_their_own_cache(
    job: str, image: str
) -> None:
    # A candidate is what 2d publishes: a cached upgrade layer shipped apt
    # 3.0.3 and libexpat 2.9.0 in #636's first candidate run, when the fixed
    # packages were already out. :buildcache-publish has one writer,
    # build-containers.yml.
    build = _build_step("ci", job)

    assert build["no-cache"] is True
    assert "cache-from" not in build
    assert build["cache-to"] == CANDIDATE_CACHE % image


def _candidate_job(job: dict[str, Any]) -> bool:
    return CANDIDATE_IF in str(job.get("if", ""))


def test_only_candidate_jobs_write_a_registry_cache_on_a_pull_request() -> None:
    for name, workflow in _all_workflows().items():
        if "pull_request" not in _triggers(workflow):
            continue
        for job_name, job in workflow["jobs"].items():
            for step in job.get("steps", []):
                if not step.get("uses", "").startswith(BUILD_PUSH_ACTION):
                    continue
                cache_to = step["with"].get("cache-to", "").strip()
                if (name, job_name) in (
                    ("ci", "candidate-base"),
                    ("ci", "candidate-build"),
                ):
                    assert _candidate_job(job), job_name
                    assert cache_to.startswith("type=registry,"), job_name
                    assert ":buildcache," in cache_to, job_name
                    continue
                assert cache_to in ("", "${{ steps.cache.outputs.cache_to }}"), (
                    name,
                    job_name,
                    step.get("name"),
                )
    # The verification build's strategy logs in nowhere: it writes nothing.
    image = _workflow("ci")["jobs"]["image"]
    assert _step(image, "Login to GHCR")["if"] == PULLED_IF
    assert (
        _step(image, "Determine cache strategy")["if"] == "env.MODE == 'verification'"
    )


@pytest.mark.parametrize(
    ("event", "head_repo"),
    [("push", ""), ("workflow_dispatch", ""), ("pull_request", REPOSITORY)],
)
def test_only_a_fork_pull_request_uses_the_actions_cache(
    tmp_path: Path, event: str, head_repo: str
) -> None:
    # A fork writes Actions cache entries under its pull request's ref. They
    # stay harmless only while no other build reads that cache.
    for name, workflow in _all_workflows().items():
        for job_name, job in workflow["jobs"].items():
            for step in job.get("steps", []):
                if "type=gha" in json.dumps(step):
                    assert (name, job_name, step.get("name")) == (
                        "ci",
                        "image",
                        "Determine cache strategy",
                    )
    cache = _cache_strategy(tmp_path, event, head_repo)

    assert "type=gha" not in cache["cache_from"]
    assert "type=gha" not in cache["cache_to"]


def test_every_check_of_an_image_asserts_the_image_first() -> None:
    jobs = _workflow("ci")["jobs"]
    for job_name, recorded in (("base", "layout"), ("image", "image")):
        steps = jobs[job_name]["steps"]
        names = [step.get("name", "") for step in steps]
        start = names.index(
            "Check the loaded base is the layout's image"
            if job_name == "base"
            else "Record the image under test"
        )
        for step in steps[start + 1 :]:
            run = step.get("run", "")
            # A step that runs or reads the image, not one that only names it
            # in a message.
            uses_the_image = (
                "IMAGE_REF" in run
                and re.search(r"\bdocker\b|scripts/|container-structure-test", run)
            ) or step.get("with", {}).get("image") == "${{ env.IMAGE_REF }}"
            if not uses_the_image or step.get("name", "").startswith("Assert"):
                continue
            if "uses" in step:
                # An action cannot run the script: an assert step comes right
                # before it, and the action runs only if that step passed.
                assert "_image.outcome == 'success'" in step["if"], step["name"]
                continue
            assert run.lstrip().startswith("set -euo pipefail\n"), step["name"]
            assert (
                'bash scripts/assert-image-id.sh "${IMAGE_REF}" "${IMAGE_ID}"' in run
            ), step["name"]
            assert step["env"]["IMAGE_ID"] == f"${{{{ steps.{recorded}.outputs.id }}}}"


def test_the_scan_blocks_on_critical_in_verification_and_high_in_candidate() -> None:
    image = _workflow("ci")["jobs"]["image"]
    scan = _step(image, "Scan image with Grype")

    assert image["env"]["MODE"] == "${{ needs.changes.outputs.mode }}"
    assert (
        scan["with"]["severity-cutoff"]
        == f"${{{{ {PULLED_IF} && 'high' || 'critical' }}}}"
    )
    assert scan["with"]["fail-build"] == "true"
    assert scan["with"]["only-fixed"] is True
    assert scan["with"]["output-format"] == "json"
    annotate = _step(image, "Annotate fixable high findings")
    assert annotate["env"]["REPORT"] == "${{ steps.grype.outputs.json }}"
    assert "continue-on-error" not in annotate


@pytest.mark.parametrize(
    ("severities", "warnings"),
    [([], 0), (["Critical"], 0), (["High", "Medium", "High"], 2)],
)
def test_fixable_high_findings_are_warnings_not_failures(
    tmp_path: Path, severities: list[str], warnings: int
) -> None:
    report = tmp_path / "grype.json"
    report.write_text(
        json.dumps(
            {
                "matches": [
                    {
                        "vulnerability": {
                            "id": f"CVE-2026-{index}",
                            "severity": severity,
                            "fix": {"versions": ["2.0"], "state": "fixed"},
                        },
                        "artifact": {"name": f"pkg{index}", "version": "1.0"},
                    }
                    for index, severity in enumerate(severities)
                ]
            }
        )
    )
    summary = tmp_path / "summary.md"
    summary.touch()

    proc = _run_step(
        "ci",
        "image",
        "Annotate fixable high findings",
        {
            "REPORT": str(report),
            "IMAGE_REF": "devcontainer-golang:ci",
            "MODE": "verification",
            "GITHUB_STEP_SUMMARY": str(summary),
        },
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.count("::warning title=") == warnings
    assert summary.read_text().count("\n- ") == warnings


def test_an_unreadable_scan_report_only_warns(tmp_path: Path) -> None:
    proc = _run_step(
        "ci",
        "image",
        "Annotate fixable high findings",
        {
            "REPORT": str(tmp_path / "missing.json"),
            "IMAGE_REF": "devcontainer-golang:ci",
            "MODE": "verification",
        },
    )

    assert proc.returncode == 0
    assert "::warning::No readable Grype report" in proc.stdout


@pytest.mark.parametrize(
    ("sbom", "passes"),
    [
        ({"spdxVersion": "SPDX-2.3", "packages": [{"name": "bash"}]}, True),
        ({"spdxVersion": "SPDX-2.3", "packages": []}, False),
        ({"spdxVersion": "SPDX-2.3"}, False),
        ("not json", False),
    ],
)
@pytest.mark.parametrize(
    ("job", "step"),
    [
        ("base", "Check the SBOM of base"),
        ("image", "Check the SBOM of ${{ matrix.image }}"),
    ],
)
def test_an_unusable_sbom_fails(
    tmp_path: Path, job: str, step: str, sbom: Any, passes: bool
) -> None:
    path = tmp_path / "sbom.spdx.json"
    path.write_text(sbom if isinstance(sbom, str) else json.dumps(sbom))

    proc = _run_step(
        "ci", job, step, {"SBOM": str(path), "IMAGE_REF": "devcontainer-golang:ci"}
    )

    assert (proc.returncode == 0) is passes, proc.stdout + proc.stderr


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


def test_ci_success_needs_every_job_but_the_aliases() -> None:
    jobs = _workflow("ci")["jobs"]
    needs = set(jobs["ci-success"]["needs"])

    assert {"devcontainer-state", "lint", "powershell-lint", "base", "image"} <= needs
    assert {*CANDIDATE_JOBS, "provenance"} <= needs
    assert set(jobs) - needs - {"ci-success"} == REQUIRED_CHECK_ALIASES


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


@pytest.mark.parametrize(("workflow", "expected"), [("ci", 3), ("build-containers", 3)])
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


# Candidate mode (phase 2c): the develop -> main promotion pull request builds
# each image as build-containers.yml publishes it, tests the pushed digest on
# every platform, tags it and records it. A push builds no image, and main
# proves its tree was tested.

DIGEST = "sha256:" + "d" * 64
TREE = "ab" * 20


def _release_images() -> ModuleType:
    path = REPO_ROOT / "scripts" / "release-images.py"
    spec = importlib.util.spec_from_file_location("release_images_contract", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _decide_mode(
    tmp_path: Path,
    event: str,
    head_repo: str,
    head_ref: str,
    base_ref: str,
    mode_input: str = "",
) -> tuple[subprocess.CompletedProcess[str], Path]:
    output = tmp_path / "mode"
    proc = _run_step(
        "ci",
        "changes",
        "Decide the image mode",
        {
            "EVENT_NAME": event,
            "HEAD_REPO": head_repo,
            "HEAD_REF": head_ref,
            "BASE_REF": base_ref,
            "REPOSITORY": REPOSITORY,
            "MODE_INPUT": mode_input,
            "GITHUB_OUTPUT": str(output),
        },
    )
    return proc, output


def _mode(
    tmp_path: Path,
    event: str,
    head_repo: str,
    head_ref: str,
    base_ref: str,
    mode_input: str = "",
) -> str:
    proc, output = _decide_mode(
        tmp_path, event, head_repo, head_ref, base_ref, mode_input
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return _outputs(output)["mode"]


@pytest.mark.parametrize(
    ("event", "head_repo", "head_ref", "base_ref", "mode"),
    [
        ("pull_request", REPOSITORY, "develop", "main", "candidate"),
        # A fork can name its branch develop: its run must never push.
        (
            "pull_request",
            "someone/ansible-devcontainer-vscode",
            "develop",
            "main",
            "verification",
        ),
        ("pull_request", "", "develop", "main", "verification"),
        ("pull_request", REPOSITORY, "feature/develop", "main", "verification"),
        ("pull_request", REPOSITORY, "renovate/uv", "develop", "verification"),
        ("pull_request", REPOSITORY, "develop", "develop", "verification"),
        ("pull_request_target", REPOSITORY, "develop", "main", "verification"),
        ("push", "", "", "", "verification"),
        ("workflow_dispatch", "", "", "", "verification"),
    ],
)
def test_candidate_mode_is_only_this_repository_s_develop_into_main(
    tmp_path: Path, event: str, head_repo: str, head_ref: str, base_ref: str, mode: str
) -> None:
    assert _mode(tmp_path, event, head_repo, head_ref, base_ref) == mode


def test_the_mode_reads_the_event_not_the_branch_name_alone() -> None:
    changes = _workflow("ci")["jobs"]["changes"]
    env = _step(changes, "Decide the image mode")["env"]

    assert changes["outputs"]["mode"] == "${{ steps.mode.outputs.mode }}"
    assert env == {
        "EVENT_NAME": "${{ github.event_name }}",
        "HEAD_REPO": "${{ github.event.pull_request.head.repo.full_name || '' }}",
        "HEAD_REF": "${{ github.head_ref }}",
        "BASE_REF": "${{ github.base_ref }}",
        "REPOSITORY": "${{ github.repository }}",
        "MODE_INPUT": "${{ inputs.mode || '' }}",
    }


def test_no_workflow_runs_on_pull_request_target() -> None:
    for name, workflow in _all_workflows().items():
        assert "pull_request_target" not in _triggers(workflow), name


def _conjuncts(condition: str) -> list[str]:
    assert "||" not in condition, condition
    return [part.strip() for part in condition.split("&&")]


def test_packages_write_on_a_pull_request_only_in_candidate_jobs() -> None:
    ci = _workflow("ci")
    assert ci["permissions"] == {"contents": "read"}
    for name, workflow in _all_workflows().items():
        if "pull_request" not in _triggers(workflow):
            continue
        assert workflow.get("permissions", {}).get("packages") != "write", name
        for job_name, job in workflow["jobs"].items():
            if job.get("permissions", {}).get("packages") != "write":
                continue
            assert (name, job_name) in {("ci", job) for job in CANDIDATE_JOBS}
            # Required, not one way in among others.
            assert CANDIDATE_IF in _conjuncts(job["if"]), job_name
    for job_name in CANDIDATE_JOBS:
        assert ci["jobs"][job_name]["permissions"]["packages"] == "write"


def test_every_checkout_in_ci_drops_its_credentials() -> None:
    for job_name, job in _workflow("ci")["jobs"].items():
        for step in job.get("steps", []):
            if step.get("uses", "").startswith("actions/checkout@"):
                assert step["with"]["persist-credentials"] is False, job_name


def test_candidates_build_and_test_the_pull_request_head() -> None:
    # Or, in nightly mode, which has no pull request, the run's commit.
    jobs = _workflow("ci")["jobs"]
    for job_name in CANDIDATE_JOBS:
        checkout = jobs[job_name]["steps"][0]
        assert checkout["with"]["ref"] == (
            "${{ needs.changes.outputs.mode == 'nightly' && github.sha"
            " || github.event.pull_request.head.sha }}"
        )
    image_checkout = jobs["image"]["steps"][0]["with"]["ref"]
    assert image_checkout == (
        "${{ needs.changes.outputs.mode == 'candidate'"
        " && github.event.pull_request.head.sha || '' }}"
    )


def _legs(tmp_path: Path, mode: str, images: list[str], base: str) -> dict[str, str]:
    output = tmp_path / f"legs-{mode}"
    proc = _run_step(
        "ci",
        "changes",
        "Resolve the image legs",
        {
            "MODE": mode,
            "IMAGES": json.dumps(images),
            "BASE": base,
            "GITHUB_OUTPUT": str(output),
        },
    )
    assert proc.returncode == 0, proc.stderr
    return _outputs(output)


STACKS = sorted(set(_image_filters()) - {"base"})


def test_candidate_legs_are_every_published_platform_on_its_runner(
    tmp_path: Path,
) -> None:
    module = _release_images()
    resolved = _legs(tmp_path, "candidate", STACKS, "true")
    legs = json.loads(resolved["legs"])

    assert {(leg["image"], leg["platform"]) for leg in legs} == {
        (name, platform)
        for name in [*STACKS, "base"]
        for platform in module.IMAGES[name].split(",")
    }
    assert ("latex", "linux/arm64") not in {
        (leg["image"], leg["platform"]) for leg in legs
    }
    for leg in legs:
        assert leg["runner"] == module.RUNNERS[leg["platform"]]
        assert leg["arch"] == leg["platform"].split("/")[1]
    assert json.loads(resolved["builds"]) == [
        {"image": name, "platforms": module.IMAGES[name]} for name in STACKS
    ]
    assert resolved["base_platforms"] == module.IMAGES["base"]


def test_verification_legs_are_each_image_s_amd64_build(tmp_path: Path) -> None:
    resolved = _legs(tmp_path, "verification", STACKS, "true")

    assert [leg["image"] for leg in json.loads(resolved["legs"])] == STACKS
    assert {leg["runner"] for leg in json.loads(resolved["legs"])} == {"ubuntu-24.04"}
    assert resolved["builds"] == "[]"


@pytest.mark.parametrize("mode", ["verification", "candidate"])
def test_no_image_resolved_is_no_leg_and_no_build(tmp_path: Path, mode: str) -> None:
    resolved = _legs(tmp_path, mode, [], "false")

    assert resolved["legs"] == "[]"
    assert resolved["builds"] == "[]"


def test_the_image_jobs_take_their_matrices_from_the_legs() -> None:
    jobs = _workflow("ci")["jobs"]

    assert jobs["image"]["runs-on"] == "${{ matrix.runner }}"
    assert jobs["candidate-build"]["strategy"]["matrix"] == {
        "include": "${{ fromJSON(needs.changes.outputs.builds) }}"
    }
    assert "max-parallel" not in jobs["candidate-build"]["strategy"]
    assert "needs.changes.outputs.builds != '[]'" in jobs["candidate-build"]["if"]
    assert "needs.changes.outputs.base == 'true'" in jobs["candidate-base"]["if"]
    build = _step(
        jobs["candidate-build"], "Build and push ${{ matrix.image }} by digest"
    )
    assert build["with"]["platforms"] == "${{ matrix.platforms }}"
    base = _step(jobs["candidate-base"], "Build and push base by digest")
    assert base["with"]["platforms"] == "${{ needs.changes.outputs.base_platforms }}"
    legs = _step(jobs["changes"], "Resolve the image legs")["run"]
    assert "python3 scripts/release-images.py ci-matrix" in legs


def test_the_size_gate_is_the_only_check_on_amd64_alone() -> None:
    image = _workflow("ci")["jobs"]["image"]
    on_amd64 = [
        step["name"] for step in image["steps"] if "matrix.arch" in step.get("if", "")
    ]

    assert on_amd64 == ["Check ${{ matrix.image }} image size against its budget"]
    size = _step(image, on_amd64[0])
    assert "matrix.arch == 'amd64'" in size["if"]


def test_every_candidate_leg_checks_the_pulled_platform_before_any_check() -> None:
    image = _workflow("ci")["jobs"]["image"]
    names = [step.get("name") for step in image["steps"]]
    pull = _step(image, "Pull the candidate by digest")
    record = _step(image, "Record the image under test")

    assert pull["if"] == PULLED_IF
    assert pull["env"]["PLATFORM"] == "${{ matrix.platform }}"
    assert names.index("Download the candidate digest") < names.index(
        "Pull the candidate by digest"
    )
    assert names.index("Pull the candidate by digest") < names.index(
        "Record the image under test"
    )
    # No if: it runs only when every step before it passed, the pull among
    # them, and every check after it runs only when it did, or after a step
    # that did.
    assert "if" not in record
    for step in image["steps"][names.index("Record the image under test") + 1 :]:
        condition = step.get("if", "")
        assert re.search(
            r"steps\.(image|scan_image|sbom_image)\.outcome == 'success'"
            r"|steps\.grype\.outputs\.json != ''",
            condition,
        ), step.get("name")


FAKE_PULL = """#!/usr/bin/env bash
echo "$*" >> "${FAKE_LOG}"
if [ "$1" = image ]; then
  echo "${FAKE_PLATFORM}"
fi
"""


def _pull(
    tmp_path: Path, digest: str, pulled: str
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    record = tmp_path / "golang.json"
    record.write_text(json.dumps({"name": "golang", "digest": digest}))
    log = tmp_path / "docker.log"
    log.touch()
    _stub(tmp_path / "bin", "docker", FAKE_PULL)
    proc = _run_step(
        "ci",
        "image",
        "Pull the candidate by digest",
        {
            "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}",
            "RECORD": str(record),
            "REPOSITORY": "ghcr.io/malpanez/devcontainer-golang",
            "PLATFORM": "linux/arm64",
            "IMAGE_REF": "devcontainer-golang:ci",
            "FAKE_PLATFORM": pulled,
            "FAKE_LOG": str(log),
        },
    )
    return proc, log.read_text().splitlines()


def test_a_leg_tags_the_digest_it_pulled_for_its_platform(tmp_path: Path) -> None:
    proc, calls = _pull(tmp_path, DIGEST, "linux/arm64")
    ref = f"ghcr.io/malpanez/devcontainer-golang@{DIGEST}"

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert calls[0] == f"pull {ref}"
    assert calls[-1] == f"tag {ref} devcontainer-golang:ci"


def test_a_leg_fails_when_the_pull_gives_another_platform(tmp_path: Path) -> None:
    proc, calls = _pull(tmp_path, DIGEST, "linux/amd64")

    assert proc.returncode == 1
    assert "proves nothing about linux/arm64" in proc.stdout
    assert not any(call.startswith("tag ") for call in calls)


def test_a_leg_without_a_digest_pulls_nothing(tmp_path: Path) -> None:
    proc, calls = _pull(tmp_path, "latest", "linux/arm64")

    assert proc.returncode == 1
    assert calls == []


def test_the_verification_build_steps_skip_in_candidate_mode() -> None:
    image = _workflow("ci")["jobs"]["image"]
    names = [step.get("name") for step in image["steps"]]
    first = names.index("Check this run built the base")
    last = names.index("Build ${{ matrix.image }}")

    for step in image["steps"][first : last + 1]:
        assert step["if"].startswith("env.MODE == 'verification'"), step["name"]
    for name in ("Login to GHCR", "Download the candidate digest"):
        assert _step(image, name)["if"] == PULLED_IF
    assert names.index("Build ${{ matrix.image }}") < names.index("Login to GHCR")


# build-containers.yml reads :buildcache-publish; candidates read no cache.
PUBLISH_ONLY = {"cache-from"}
# build-all's expressions, in candidate-build's words.
BUILD_ALL_TO_CANDIDATE = {
    "${{ matrix.stack }}${{ matrix.variant }}": "${{ matrix.image }}",
    "matrix.base_from_run": "steps.files.outputs.base_from_run == 'true'",
    "needs.build-base.outputs.digest": "needs.candidate-base.outputs.digest",
}


def _build_step(workflow: str, job: str) -> dict[str, Any]:
    steps = [
        step
        for step in _workflow(workflow)["jobs"][job]["steps"]
        if step.get("uses", "").startswith(BUILD_PUSH_ACTION)
    ]
    assert len(steps) == 1, (workflow, job)
    return steps[0]["with"]


def test_candidate_base_is_built_as_build_base_publishes_it() -> None:
    published = _build_step("build-containers", "build-base")
    candidate = _build_step("ci", "candidate-base")

    assert set(candidate) == set(published) - PUBLISH_ONLY
    for key in ("context", "file", "outputs", "tags", "labels", "build-args"):
        assert candidate[key] == published[key], key
    assert candidate["provenance"] is published["provenance"] is True
    assert candidate["sbom"] is published["sbom"] is True
    platforms = _workflow("build-containers")["jobs"]["build-base"]["env"]["PLATFORMS"]
    assert published["platforms"] == "${{ env.PLATFORMS }}"
    assert platforms == _release_images().IMAGES["base"]


def test_candidate_builds_are_built_as_build_all_publishes_them(tmp_path: Path) -> None:
    published = _build_step("build-containers", "build-all")
    candidate = _build_step("ci", "candidate-build")

    assert set(candidate) == set(published) - PUBLISH_ONLY
    for key in ("context", "outputs", "tags", "labels", "build-args"):
        expected = published[key]
        for words, ours in BUILD_ALL_TO_CANDIDATE.items():
            expected = expected.replace(words, ours)
        assert candidate[key] == expected, key
    assert candidate["provenance"] is published["provenance"] is True
    assert candidate["sbom"] is published["sbom"] is True
    assert candidate["file"] == "${{ steps.files.outputs.dockerfile }}"
    assert candidate["target"] == "${{ steps.files.outputs.target }}"
    assert candidate["platforms"] == published["platforms"] == "${{ matrix.platforms }}"
    # What those expressions resolve to, image by image.
    builds = {
        build["image"]: build
        for build in json.loads(_legs(tmp_path, "candidate", STACKS, "true")["builds"])
    }
    matrix = _workflow("build-containers")["jobs"]["build-all"]["strategy"]["matrix"]
    assert set(builds) == {e["stack"] + e["variant"] for e in matrix["include"]}
    for entry in matrix["include"]:
        name = entry["stack"] + entry["variant"]
        resolved = _resolve_files(tmp_path, name)
        assert (
            resolved["dockerfile"]
            == f"devcontainers/{entry['stack']}/{entry['dockerfile']}"
        )
        assert resolved["target"] == entry.get("target", ""), name
        assert (
            resolved["base_from_run"] == str(entry.get("base_from_run", False)).lower()
        )
        assert builds[name]["platforms"] == entry["platforms"], name


@pytest.mark.parametrize(
    ("candidate_job", "published_job"),
    [("candidate-base", "build-base"), ("candidate-build", "build-all")],
)
def test_candidates_carry_the_published_labels_of_the_head(
    candidate_job: str, published_job: str
) -> None:
    candidate = _workflow("ci")["jobs"][candidate_job]
    published = _workflow("build-containers")["jobs"][published_job]
    ours = _step(candidate, "Extract metadata")
    theirs = _step(published, "Extract metadata")

    assert ours["with"]["labels"] == theirs["with"]["labels"]
    assert ours["with"]["images"] == theirs["with"]["images"].replace(
        "${{ matrix.stack }}${{ matrix.variant }}", "${{ matrix.image }}"
    )
    # {{sha}}, type=sha and the revision label of the pull request's head, not
    # of refs/pull/N/merge.
    assert ours["env"] == {"DOCKER_METADATA_PR_HEAD_SHA": "true"}
    for name in (
        "Derive SOURCE_DATE_EPOCH from the commit",
        "Keep the Dockerfile's description label",
    ):
        assert _step(candidate, name)["run"] == _step(published, name)["run"]


def _git_env(tmp_path: Path) -> dict[str, str]:
    return {
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CEILING_DIRECTORIES": str(tmp_path),
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
    }


def _git(repo: Path, tmp_path: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=repo,
        env={**_clean_environ(), **_git_env(tmp_path)},
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _commit(repo: Path, tmp_path: Path, name: str, content: str) -> str:
    (repo / name).write_text(content)
    _git(repo, tmp_path, "add", name)
    _git(repo, tmp_path, "commit", "-q", "-m", name)
    return _git(repo, tmp_path, "rev-parse", "HEAD")


def _history(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """main at A; develop at B, with A as an ancestor; other at C, off A."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, tmp_path, "init", "-q", "-b", "main")
    shas = {"A": _commit(repo, tmp_path, "a", "1")}
    shas["B"] = _commit(repo, tmp_path, "b", "2")
    _git(repo, tmp_path, "checkout", "-q", "-b", "other", shas["A"])
    shas["C"] = _commit(repo, tmp_path, "c", "3")
    for name, ref in (("B tree", "B"), ("C tree", "C")):
        shas[name] = _git(repo, tmp_path, "rev-parse", f"{shas[ref]}^{{tree}}")
    # A merge commit with B's tree, as refs/pull/N/merge is when A is an ancestor.
    shas["M"] = _git(
        repo,
        tmp_path,
        "commit-tree",
        shas["B tree"],
        "-p",
        shas["A"],
        "-p",
        shas["B"],
        "-m",
        "m",
    )
    return repo, shas


def _ancestor_check(
    tmp_path: Path, repo: Path, base: str, head: str, merge: str
) -> subprocess.CompletedProcess[str]:
    return _run_step(
        "ci",
        "changes",
        "Check main is an ancestor of develop",
        {**_git_env(tmp_path), "BASE_SHA": base, "HEAD_SHA": head, "MERGE_SHA": merge},
        cwd=repo,
    )


def test_the_ancestor_check_passes_when_main_is_in_develop(tmp_path: Path) -> None:
    repo, shas = _history(tmp_path)

    proc = _ancestor_check(tmp_path, repo, shas["A"], shas["B"], shas["M"])

    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_the_ancestor_check_says_to_merge_main_into_develop(tmp_path: Path) -> None:
    repo, shas = _history(tmp_path)

    proc = _ancestor_check(tmp_path, repo, shas["C"], shas["B"], shas["M"])

    assert proc.returncode == 1
    assert "merge main into develop first" in proc.stdout


def test_the_ancestor_check_fails_when_the_merge_has_another_tree(
    tmp_path: Path,
) -> None:
    repo, shas = _history(tmp_path)

    proc = _ancestor_check(tmp_path, repo, shas["A"], shas["B"], shas["C"])

    assert proc.returncode == 1
    assert "merge main into develop first" in proc.stdout


def test_the_ancestor_check_runs_before_any_candidate_build() -> None:
    jobs = _workflow("ci")["jobs"]
    changes = jobs["changes"]
    check = _step(changes, "Check main is an ancestor of develop")

    assert check["if"] == "steps.mode.outputs.mode == 'candidate'"
    assert check["env"] == {
        "BASE_SHA": "${{ github.event.pull_request.base.sha }}",
        "HEAD_SHA": "${{ github.event.pull_request.head.sha }}",
        "MERGE_SHA": "${{ github.sha }}",
    }
    # Its history: the checkout fetches every commit.
    assert changes["steps"][0]["with"]["fetch-depth"] == 0
    # A failed check fails changes, and no candidate job runs after a failed
    # changes: one that sets aside the implicit success() asks for it.
    for job_name in CANDIDATE_JOBS:
        assert "changes" in jobs[job_name]["needs"]
        assert "!cancelled()" not in jobs[job_name]["if"] or (
            "needs.changes.result == 'success'" in jobs[job_name]["if"]
            or "!contains(needs.*.result, 'failure')" in jobs[job_name]["if"]
        )


def test_a_push_runs_no_image_job_and_main_checks_its_provenance() -> None:
    jobs = _workflow("ci")["jobs"]

    # A push resolves no image (test_a_push_tests_no_image), so no leg, build
    # or base, and the mode is never candidate (the mode test above).
    assert "needs.changes.outputs.legs != '[]'" in jobs["image"]["if"]
    assert "needs.changes.outputs.base == 'true'" in jobs["base"]["if"]
    provenance = jobs["provenance"]
    assert (
        provenance["if"]
        == "github.event_name == 'push' && github.ref == 'refs/heads/main'"
    )
    assert provenance["permissions"] == {
        "contents": "read",
        "actions": "read",
        "pull-requests": "read",
    }
    download = _step(provenance, "Download its record")["with"]
    upload = _step(jobs["candidate-tag"], "Upload the record")["with"]
    assert download["name"] == upload["name"] == "tested-digests"
    assert download["run-id"] == "${{ steps.run.outputs.run_id }}"
    assert download["github-token"] == "${{ github.token }}"
    check = _step(provenance, "Check the record names this tree")["run"]
    assert "git rev-parse 'HEAD^{tree}'" in check
    assert "scripts/tested-digests.py verify" in check


def _provenance_check(
    tmp_path: Path, record_tree: str
) -> subprocess.CompletedProcess[str]:
    repo = tmp_path / "main"
    repo.mkdir()
    _git(repo, tmp_path, "init", "-q", "-b", "main")
    _commit(repo, tmp_path, "file", "main\n")
    # Untracked, so not in HEAD's tree: the step runs scripts/ from the checkout.
    (repo / "scripts").symlink_to(REPO_ROOT / "scripts")
    tree = record_tree or _git(repo, tmp_path, "rev-parse", "HEAD^{tree}")
    temp = tmp_path / "runner-temp"
    (temp / "tested-digests").mkdir(parents=True)
    (temp / "tested-digests" / "tested-digests.json").write_text(
        json.dumps(
            {
                "base": "1" * 40,
                "head": "2" * 40,
                "images": {"golang": DIGEST},
                "run_id": 42,
                "tree": tree,
            }
        )
    )
    return _run_step(
        "ci",
        "provenance",
        "Check the record names this tree",
        {**_git_env(tmp_path), "RUNNER_TEMP": str(temp), "RUN_ID": "42"},
        cwd=repo,
    )


def test_provenance_passes_when_the_record_names_main_s_tree(tmp_path: Path) -> None:
    proc = _provenance_check(tmp_path, "")

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "golang" in proc.stdout


def test_provenance_fails_loudly_on_another_tree(tmp_path: Path) -> None:
    proc = _provenance_check(tmp_path, TREE)

    assert proc.returncode == 1
    assert "::error" in proc.stderr
    assert "main took a tree no candidate run tested" in proc.stderr


def test_the_record_is_written_only_once_the_whole_run_passed() -> None:
    jobs = _workflow("ci")["jobs"]
    tag = jobs["candidate-tag"]
    names = [step.get("name") for step in tag["steps"]]

    assert set(tag["needs"]) == set(jobs["ci-success"]["needs"]) - {
        "candidate-tag",
        "provenance",
    }
    assert _conjuncts(tag["if"]) == [
        "!cancelled()",
        CANDIDATE_IF,
        "!contains(needs.*.result, 'failure')",
        "!contains(needs.*.result, 'cancelled')",
    ]
    assert (
        names.index("Write the record of what this run tested")
        < names.index("Tag the tested digests")
        < names.index("Upload the record")
    )
    # Written when no image was built too: no if on the write or the upload.
    assert "if" not in _step(tag, "Write the record of what this run tested")
    upload = _step(tag, "Upload the record")
    assert "if" not in upload
    assert upload["with"]["retention-days"] == 90
    assert upload["with"]["if-no-files-found"] == "error"


@pytest.mark.parametrize(
    ("legs", "result", "passes"),
    [
        ("[]", "skipped", True),
        ('[{"image":"golang"}]', "success", True),
        ('[{"image":"golang"}]', "skipped", False),
    ],
)
def test_resolved_legs_that_did_not_run_record_nothing(
    legs: str, result: str, passes: bool
) -> None:
    proc = _run_step(
        "ci",
        "candidate-tag",
        "Check every leg ran",
        {"LEGS": legs, "IMAGE_RESULT": result},
    )

    assert (proc.returncode == 0) is passes, proc.stdout


FAKE_IMAGETOOLS = """#!/usr/bin/env bash
echo "$*" >> "${FAKE_LOG}"
case "$*" in
  "buildx imagetools create --dry-run "*)
    printf '%s\\n' "${FAKE_PLANNED}"
    ;;
  "buildx imagetools inspect --raw "*)
    printf '%s' "${FAKE_RESOLVED}"
    ;;
  *)
    ;;
esac
"""
INDEX = '{"schemaVersion":2,"manifests":[]}'
INDEX_DIGEST = "sha256:" + hashlib.sha256(INDEX.encode()).hexdigest()


def _tag(
    tmp_path: Path, images: dict[str, str], planned: str = INDEX, resolved: str = INDEX
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    record = tmp_path / "tested-digests.json"
    record.write_text(json.dumps({"tree": TREE, "images": images}))
    log = tmp_path / "docker.log"
    log.touch()
    _stub(tmp_path / "bin", "docker", FAKE_IMAGETOOLS)
    proc = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/tag-candidates.sh"), str(record)],
        env={
            **os.environ,
            "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}",
            "GITHUB_REPOSITORY_OWNER": "malpanez",
            "FAKE_LOG": str(log),
            "FAKE_PLANNED": planned,
            "FAKE_RESOLVED": resolved,
        },
        capture_output=True,
        text=True,
        check=False,
    )
    return proc, log.read_text().splitlines()


def test_each_tested_digest_is_tagged_with_its_tree(tmp_path: Path) -> None:
    proc, calls = _tag(tmp_path, {"base": INDEX_DIGEST, "golang": INDEX_DIGEST})
    tag = f"candidate-{TREE[:12]}"

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert re.fullmatch(r"candidate-[0-9a-f]{12}", tag)
    for name in ("base", "golang"):
        image = f"ghcr.io/malpanez/devcontainer-{name}"
        assert (
            f"buildx imagetools create --tag {image}:{tag} {image}@{INDEX_DIGEST}"
            in calls
        )
        assert f"buildx imagetools inspect --raw {image}:{tag}" in calls
    # Every dry run before the first tag.
    first_tag = next(
        i
        for i, call in enumerate(calls)
        if " --tag " in call and "--dry-run" not in call
    )
    assert all("--dry-run" in call for call in calls[:first_tag])
    assert len(calls[:first_tag]) == 2


def test_no_tag_moves_when_imagetools_would_write_another_index(tmp_path: Path) -> None:
    proc, calls = _tag(tmp_path, {"golang": INDEX_DIGEST}, planned=INDEX + " ")

    assert proc.returncode == 1
    assert "no tag was written" in proc.stdout
    assert all("--dry-run" in call for call in calls)


def test_a_tag_that_does_not_resolve_to_the_tested_digest_fails(tmp_path: Path) -> None:
    proc, _calls = _tag(tmp_path, {"golang": INDEX_DIGEST}, resolved="{}")

    assert proc.returncode == 1
    assert "not the tested" in proc.stdout


def test_a_run_that_built_nothing_tags_nothing(tmp_path: Path) -> None:
    proc, calls = _tag(tmp_path, {})

    assert proc.returncode == 0, proc.stderr
    assert calls == []


def test_the_candidate_tag_step_runs_the_script() -> None:
    tag = _workflow("ci")["jobs"]["candidate-tag"]
    script = (REPO_ROOT / "scripts/tag-candidates.sh").read_text()

    assert "scripts/tag-candidates.sh" in _step(tag, "Tag the tested digests")["run"]
    assert 'TAG="candidate-${TREE:0:12}"' in script
    assert "imagetools create --dry-run" in script


def test_the_promotion_fails_when_it_cannot_open_its_pull_request() -> None:
    job = _workflow("promote-to-main")["jobs"]["create-promotion-pr"]
    text = (WORKFLOWS / "promote-to-main.yml").read_text(encoding="utf-8")

    for name in ("Check if PR already exists", "Create promotion PR"):
        assert "continue-on-error" not in _step(job, name), name
    check = _step(job, "Check if PR already exists")["run"]
    assert check.lstrip().startswith("set -euo pipefail\n")
    assert "It uses continue-on-error" not in text


def _jq(expression: str, data: Any, env: dict[str, str] | None = None) -> str:
    proc = subprocess.run(
        ["jq", "-r", expression],
        input=json.dumps(data),
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _promotion_steps() -> list[dict[str, Any]]:
    return _workflow("promote-to-main")["jobs"]["create-promotion-pr"]["steps"]


# A fork's pull request first, as the API may list it: --head is a bare branch
# name, so `<fork>:develop -> main` matches it too.
PROMOTION_LOOKUP = [
    {"number": 9, "isCrossRepository": True},
    {"number": 633, "isCrossRepository": False},
]


def test_every_promotion_lookup_skips_a_fork_s_develop() -> None:
    lookups = []
    for step in _promotion_steps():
        run = re.sub(r"\\\n\s*", " ", step.get("run", ""))
        for command in re.findall(r"gh pr list .*?--jq '[^']*'", run):
            lookups.append((step["name"], command))
    assert len(lookups) == 4, lookups

    for name, command in lookups:
        assert re.search(r"--json number,isCrossRepository\s", command), name
        expression = re.search(r"--jq '([^']*)'", command)
        assert expression, name
        found = _jq(expression.group(1), PROMOTION_LOOKUP)
        only_fork = _jq(expression.group(1), PROMOTION_LOOKUP[:1])
        if expression.group(1).endswith("| length"):
            assert (found, only_fork) == ("1", "0"), name
        else:
            assert (found, only_fork) == ("633", ""), name


def test_the_promotion_approves_only_this_repository_s_runs() -> None:
    approve = _step(
        _workflow("promote-to-main")["jobs"]["create-promotion-pr"],
        "Approve parked workflow runs",
    )
    run = re.sub(r"\\\n\s*", " ", approve["run"])
    expression = re.search(r"actions/runs\?\$\{QUERY\}\"\s+--jq '([^']*)'", run)
    assert expression, "the parked-run lookup moved"
    runs = {
        "workflow_runs": [
            {"id": 5, "head_repository": {"full_name": "someone/fork"}},
            {"id": 6, "head_repository": {"full_name": REPOSITORY}},
        ]
    }

    approved = _jq(expression.group(1), runs, {"GITHUB_REPOSITORY": REPOSITORY})

    assert approved == "6"


def test_a_promotion_whose_runs_stay_parked_fails_red() -> None:
    job = _workflow("promote-to-main")["jobs"]["create-promotion-pr"]
    approve = _step(job, "Approve parked workflow runs")
    merge = _step(job, "Enable auto-merge on promotion PR")

    assert "continue-on-error" not in approve
    proc = _run_step(
        "promote-to-main",
        "create-promotion-pr",
        "Approve parked workflow runs",
        {"GH_TOKEN": ""},
    )
    assert proc.returncode == 1
    assert "::error::BOT_TOKEN missing" in proc.stdout
    assert "FAILED_ANY=true" in approve["run"]
    assert (
        approve["run"]
        .rstrip()
        .endswith('if [ "$FAILED_ANY" = "true" ]; then\n  exit 1\nfi')
    )
    # Auto-merge is still enabled when the approval failed.
    assert merge["if"].startswith("${{ !cancelled() && ")


# Phase 2d-1: every candidate run builds every image and attests it, the PR
# base reads the candidates' cache, and nightly mode (nightly.yml calling
# ci.yml) builds, tests and records every image without tagging it, and runs
# nothing but the image jobs.

ATTEST_ACTION = "actions/attest-build-provenance@"
# The jobs that test the repository rather than an image.
REPOSITORY_JOBS = (
    "test-playbooks",
    "powershell-lint",
    "devcontainer-state",
    "unit-tests",
    "ansible-test",
    "molecule",
    "scenario-tests",
)
NOT_NIGHTLY = "needs.changes.outputs.mode != 'nightly'"
CI_GROUP = (
    "${{ github.workflow }}-${{ github.ref }}"
    "${{ inputs.mode && format('-ci.yml-{0}', inputs.mode) || '' }}"
)
LEVELS = {"none": 0, "read": 1, "write": 2}


@pytest.mark.parametrize(
    ("event", "changes", "mode"),
    [
        # A promotion that changed no image file still builds them all.
        ("pull_request", '["python"]', "candidate"),
        ("pull_request", "[]", "candidate"),
        ("workflow_dispatch", "", "nightly"),
        # 2d-2's schedule: paths-filter does not run, so no changes output.
        ("schedule", "", "nightly"),
    ],
)
def test_candidate_and_nightly_mode_build_every_image(
    tmp_path: Path, event: str, changes: str, mode: str
) -> None:
    resolved = _resolve_images(tmp_path, event, changes, mode)

    assert sorted(json.loads(resolved["images"])) == STACKS
    assert resolved["base"] == "true"


def test_the_filter_decides_nothing_in_nightly_mode() -> None:
    changes = _workflow("ci")["jobs"]["changes"]
    filter_step = next(
        step
        for step in changes["steps"]
        if step.get("uses", "").startswith(PATHS_FILTER_ACTION)
    )
    images = _step(changes, "Resolve the images to test")

    assert filter_step["if"] == "steps.mode.outputs.mode != 'nightly'"
    assert images["env"]["MODE"] == "${{ steps.mode.outputs.mode }}"


@pytest.mark.parametrize(
    ("event", "head_repo", "head_ref", "base_ref", "mode_input", "mode"),
    [
        ("workflow_dispatch", "", "", "", "nightly", "nightly"),
        ("schedule", "", "", "", "nightly", "nightly"),
        ("workflow_dispatch", "", "", "", "verification", "verification"),
        # A caller in the promotion pull request asking for verification gets
        # the mode the event gives, as before the input existed.
        ("pull_request", REPOSITORY, "develop", "main", "verification", "candidate"),
    ],
)
def test_nightly_mode_is_a_dispatch_or_a_schedule_that_asks_for_it(
    tmp_path: Path,
    event: str,
    head_repo: str,
    head_ref: str,
    base_ref: str,
    mode_input: str,
    mode: str,
) -> None:
    assert _mode(tmp_path, event, head_repo, head_ref, base_ref, mode_input) == mode


@pytest.mark.parametrize(
    ("event", "head_repo", "head_ref", "base_ref", "mode_input", "named"),
    [
        # A pull request's run takes its workflow files from the pull request,
        # a fork's too: a caller there must not get the mode that pushes.
        (
            "pull_request",
            REPOSITORY,
            "develop",
            "main",
            "nightly",
            "not on pull_request",
        ),
        (
            "pull_request",
            "someone/fork",
            "develop",
            "main",
            "nightly",
            "not on pull_request",
        ),
        ("pull_request_target", REPOSITORY, "develop", "main", "nightly", "not on"),
        ("pull_request_review", REPOSITORY, "develop", "main", "nightly", "not on"),
        ("push", "", "", "", "nightly", "not on push"),
        ("workflow_run", "", "", "", "nightly", "not on workflow_run"),
        ("workflow_dispatch", "", "", "", "candidate", "Unknown mode 'candidate'"),
        ("workflow_dispatch", "", "", "", "Nightly", "Unknown mode 'Nightly'"),
    ],
)
def test_nightly_mode_cannot_be_asked_for_by_any_other_event(
    tmp_path: Path,
    event: str,
    head_repo: str,
    head_ref: str,
    base_ref: str,
    mode_input: str,
    named: str,
) -> None:
    proc, output = _decide_mode(
        tmp_path, event, head_repo, head_ref, base_ref, mode_input
    )

    assert proc.returncode == 1
    assert "::error::" in proc.stdout
    assert named in proc.stdout
    assert not output.exists()


def test_ci_takes_the_mode_from_a_dispatch_or_a_call_and_has_no_schedule() -> None:
    triggers = _triggers(_workflow("ci"))

    assert set(triggers) == {
        "push",
        "pull_request",
        "workflow_dispatch",
        "workflow_call",
    }
    assert "schedule" not in triggers
    dispatch = triggers["workflow_dispatch"]["inputs"]["mode"]
    assert dispatch["type"] == "choice"
    assert dispatch["default"] == "verification"
    assert dispatch["options"] == ["verification", "nightly"]
    call = triggers["workflow_call"]["inputs"]["mode"]
    assert call["type"] == "string"
    assert call["required"] is True


def _group(group: str, workflow: str, ref: str, mode: str | None) -> str:
    """The concurrency group as GitHub evaluates it, for the two forms used
    here: ci.yml's and nightly.yml's."""
    suffix = "${{ inputs.mode && format('-ci.yml-{0}', inputs.mode) || '' }}"
    rendered = group.replace(suffix, f"-ci.yml-{mode}" if mode else "")
    rendered = rendered.replace("${{ github.workflow }}", workflow)
    rendered = rendered.replace("${{ github.ref }}", ref)
    assert "${{" not in rendered, rendered
    return rendered


def test_a_call_never_shares_its_caller_s_concurrency_group() -> None:
    ci = _workflow("ci")
    nightly = _workflow("nightly")

    assert ci["concurrency"] == {"group": CI_GROUP, "cancel-in-progress": True}
    # A push and a pull request keep the group they always had.
    for ref in ("refs/heads/develop", "refs/pull/636/merge"):
        assert _group(CI_GROUP, ci["name"], ref, None) == f"CI Pipeline-{ref}"
    # A called run's github.workflow is the caller's name, so a caller grouped
    # as ci.yml groups would be cancelled by its own call without the suffix.
    called = _group(CI_GROUP, nightly["name"], "refs/heads/main", "nightly")
    plain_caller = _group(
        "${{ github.workflow }}-${{ github.ref }}",
        nightly["name"],
        "refs/heads/main",
        None,
    )
    ours = _group(
        nightly["concurrency"]["group"], nightly["name"], "refs/heads/main", None
    )
    assert called == "Nightly-refs/heads/main-ci.yml-nightly"
    # Compared without case, in case GitHub matches groups so.
    assert called.lower() not in {plain_caller.lower(), ours.lower()}
    # A nightly dispatched directly never cancels a push run of its branch.
    assert _group(CI_GROUP, ci["name"], "refs/heads/main", "nightly") != _group(
        CI_GROUP, ci["name"], "refs/heads/main", None
    )
    assert nightly["concurrency"]["cancel-in-progress"] is False


def test_nightly_is_dispatched_and_calls_ci_in_nightly_mode() -> None:
    nightly = _workflow("nightly")
    triggers = _triggers(nightly)

    # 2d-2 adds the schedule here; never in ci.yml (see its triggers).
    assert set(triggers) == {"workflow_dispatch"}
    assert nightly["permissions"] == {}
    assert list(nightly["jobs"]) == ["ci"]
    job = nightly["jobs"]["ci"]
    assert job["uses"] == "./.github/workflows/ci.yml"
    assert job["with"] == {"mode": "nightly"}
    assert "secrets" not in job
    callers = [
        (name, job_name)
        for name, workflow in _all_workflows().items()
        for job_name, job in workflow["jobs"].items()
        if "ci.yml" in str(job.get("uses", ""))
    ]
    assert callers == [("nightly", "ci")]


def test_nightly_grants_what_every_job_of_ci_asks_for() -> None:
    # GitHub checks every called job against the caller's grant before the run
    # starts, skipped jobs included, and fails the run at startup when one
    # asks for more. More than they ask for is more than the run needs.
    asked: dict[str, str] = {}
    for job in _workflow("ci")["jobs"].values():
        for scope, level in job.get("permissions", {}).items():
            if LEVELS[level] > LEVELS[asked.get(scope, "none")]:
                asked[scope] = level

    assert _workflow("nightly")["jobs"]["ci"]["permissions"] == asked
    assert asked["id-token"] == asked["attestations"] == asked["packages"] == "write"


def test_the_pull_request_base_reads_the_cache_the_candidates_write() -> None:
    jobs = _workflow("ci")["jobs"]
    probe = _step(jobs["base"], "Resolve the base build cache")
    written = _build_step("ci", "candidate-base")["cache-to"]

    cache_ref = probe["env"]["CACHE_REF"]
    assert (
        cache_ref
        == "ghcr.io/${{ github.repository_owner }}/devcontainer-base:buildcache"
    )
    assert written.startswith(f"type=registry,ref={cache_ref},")
    build = _build_step("ci", "base")
    assert build["cache-from"] == "${{ steps.base_cache.outputs.from }}"
    assert "cache-to" not in build


@pytest.mark.parametrize("exists", [True, False])
def test_the_base_cache_is_read_only_when_it_exists(
    tmp_path: Path, exists: bool
) -> None:
    # buildx aborts on a missing cache-from ref.
    _stub(tmp_path / "bin", "docker", FAKE_BUILDX)
    output = tmp_path / "output"
    cache_ref = "ghcr.io/malpanez/devcontainer-base:buildcache"

    proc = _run_step(
        "ci",
        "base",
        "Resolve the base build cache",
        {
            "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}",
            "FAKE_CACHE_EXISTS": "1" if exists else "",
            "CACHE_REF": cache_ref,
            "GITHUB_OUTPUT": str(output),
        },
    )

    assert proc.returncode == 0, proc.stderr
    expected = f"type=registry,ref={cache_ref}" if exists else ""
    assert _outputs(output) == {"from": expected}


def _attest_pin() -> str:
    """build-containers.yml's one pin of the attest action."""
    pins = {
        step["uses"]
        for job in _workflow("build-containers")["jobs"].values()
        for step in job.get("steps", [])
        if step.get("uses", "").startswith(ATTEST_ACTION)
    }
    assert len(pins) == 1, pins
    return pins.pop()


@pytest.mark.parametrize(
    ("job_name", "image"),
    [("candidate-base", "base"), ("candidate-build", "${{ matrix.image }}")],
)
def test_candidate_builds_attest_the_digest_they_pushed(
    job_name: str, image: str
) -> None:
    job = _workflow("ci")["jobs"][job_name]
    names = [step.get("name") for step in job["steps"]]
    attests = [
        step for step in job["steps"] if step.get("uses", "").startswith(ATTEST_ACTION)
    ]
    build = next(
        step
        for step in job["steps"]
        if step.get("uses", "").startswith(BUILD_PUSH_ACTION)
    )

    assert len(attests) == 1
    attest = attests[0]
    assert attest["uses"] == _attest_pin()
    assert attest["uses"] == (
        "actions/attest-build-provenance@4d101475d8b20a2381f78447822ac1eab6504dd8"
    )
    assert attest["with"] == {
        "subject-name": f"ghcr.io/${{{{ github.repository_owner }}}}/devcontainer-{image}",
        "subject-digest": "${{ steps.build.outputs.digest }}",
        "push-to-registry": True,
    }
    assert attest["with"]["subject-name"] == build["with"]["tags"]
    assert build["id"] == "build"
    # Unconditional, after the digest was checked and before it is handed on:
    # every digest a leg pulls is attested.
    assert "if" not in attest
    assert (
        names.index(build["name"])
        < names.index("Record the candidate digest")
        < names.index(attest["name"])
        < names.index("Upload the candidate digest")
    )
    text = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    assert f"uses: {attest['uses']}  # v4.2.2" in text


def test_only_the_candidate_builds_can_sign_and_attest() -> None:
    ci = _workflow("ci")
    granted = {
        job_name: {
            scope
            for scope in ("id-token", "attestations")
            if job.get("permissions", {}).get(scope) == "write"
        }
        for job_name, job in ci["jobs"].items()
    }

    assert ci["permissions"] == {"contents": "read"}
    assert {name for name, scopes in granted.items() if scopes} == {
        "candidate-base",
        "candidate-build",
    }
    for name in ("candidate-base", "candidate-build"):
        assert granted[name] == {"id-token", "attestations"}
        # Behind the mode, which only this repository's promotion or a
        # dispatch or schedule selects.
        assert CANDIDATE_IF in _conjuncts(ci["jobs"][name]["if"])


def _or_outside_parentheses(condition: str) -> bool:
    depth = 0
    for index, char in enumerate(condition):
        depth += {"(": 1, ")": -1}.get(char, 0)
        if depth == 0 and condition.startswith("||", index):
            return True
    return False


def test_the_repository_s_own_jobs_skip_in_nightly_mode() -> None:
    jobs = _workflow("ci")["jobs"]

    for name in REPOSITORY_JOBS:
        condition = " ".join(jobs[name]["if"].split())
        # A conjunct of the whole condition, not one way in among others.
        assert condition.startswith(f"{NOT_NIGHTLY} && "), name
        assert not _or_outside_parentheses(condition), name
    # Lint stays: the candidate builds need it. Provenance needs a push, and
    # nightly mode is never a push.
    assert "if" not in jobs["lint"]
    assert jobs["provenance"]["if"].startswith("github.event_name == 'push' && ")
    # Every other job runs in nightly mode, or is verification's own.
    gated = set(REPOSITORY_JOBS) | {"base", "provenance"}
    for name, job in jobs.items():
        if name not in gated:
            assert "nightly" not in str(job.get("if", "")).replace(PUSHED_MODES, ""), (
                name
            )


def _ci_success(
    tmp_path: Path, results: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    needs = {
        name: {"result": result, "outputs": {}} for name, result in results.items()
    }
    return _run_step(
        "ci",
        "ci-success",
        "Check results",
        {"NEEDS_JSON": json.dumps(needs), "GITHUB_STEP_SUMMARY": str(tmp_path / "s")},
    )


def test_the_summaries_pass_a_nightly_run(tmp_path: Path) -> None:
    jobs = _workflow("ci")["jobs"]
    skipped = {*REPOSITORY_JOBS, "base", "provenance"}
    results = {
        name: "skipped" if name in skipped else "success"
        for name in jobs["ci-success"]["needs"]
    }

    assert _ci_success(tmp_path, results).returncode == 0
    for job in IMAGE_SUMMARIES:
        returncode, stdout, summary = _run_summary(
            tmp_path,
            job,
            {name: results[name] for name in IMAGE_SUMMARY_NEEDS},
            event="workflow_dispatch",
        )
        assert returncode == 0, stdout
        assert "✅" in summary
    # A nightly run whose legs failed fails them all.
    results["image"] = "failure"
    assert _ci_success(tmp_path, results).returncode == 1


def test_nightly_mode_records_and_does_not_tag() -> None:
    tag = _workflow("ci")["jobs"]["candidate-tag"]
    write = _step(tag, "Write the record of what this run tested")

    for name in ("Login to GHCR", "Tag the tested digests"):
        assert _step(tag, name)["if"] == "needs.changes.outputs.mode == 'candidate'"
    assert "if" not in _step(tag, "Upload the record")
    assert write["env"]["HEAD_SHA"] == (
        "${{ needs.changes.outputs.mode == 'nightly' && github.sha"
        " || github.event.pull_request.head.sha }}"
    )
    assert write["env"]["BASE_SHA"] == (
        "${{ needs.changes.outputs.mode == 'nightly' && github.sha"
        " || github.event.pull_request.base.sha }}"
    )


def test_a_nightly_record_names_the_commit_it_built(tmp_path: Path) -> None:
    repo = tmp_path / "main"
    repo.mkdir()
    _git(repo, tmp_path, "init", "-q", "-b", "main")
    sha = _commit(repo, tmp_path, "file", "main\n")
    # Untracked, so not in HEAD's tree: the step runs scripts/ from the checkout.
    (repo / "scripts").symlink_to(REPO_ROOT / "scripts")
    temp = tmp_path / "runner-temp"
    digests = temp / "candidate-digest"
    digests.mkdir(parents=True)
    for name in ("base", "golang"):
        (digests / f"{name}.json").write_text(
            json.dumps({"name": name, "digest": DIGEST})
        )

    proc = _run_step(
        "ci",
        "candidate-tag",
        "Write the record of what this run tested",
        {
            **_git_env(tmp_path),
            "RUNNER_TEMP": str(temp),
            "IMAGES": '["golang"]',
            "BASE": "true",
            # What the step's expressions give in nightly mode: github.sha.
            "HEAD_SHA": sha,
            "BASE_SHA": sha,
            "GITHUB_RUN_ID": "77",
        },
        cwd=repo,
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    record = json.loads((temp / "tested-digests.json").read_text())
    assert record == {
        "base": sha,
        "head": sha,
        "images": {"base": DIGEST, "golang": DIGEST},
        "run_id": 77,
        "tree": _git(repo, tmp_path, "rev-parse", "HEAD^{tree}"),
    }
