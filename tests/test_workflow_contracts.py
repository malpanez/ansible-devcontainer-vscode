"""What the workflows promise each other, which neither actionlint nor a green
run shows: a required check that always reports, an aggregate that can fail, a
filter that covers its own workflow, a matrix that reaches the -aws stages.
"""

import fnmatch
import hashlib
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
IMAGE_SUMMARY_NEEDS = ["changes", "lint", "base", "image"]
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
    tmp_path: Path, job: str, results: dict[str, str]
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
    assert jobs["base"]["if"] == "needs.changes.outputs.base == 'true'"
    condition = jobs["image"]["if"]
    assert "needs.changes.outputs.images != '[]'" in condition
    assert "needs.changes.result == 'success'" in condition
    assert "needs.lint.result == 'success'" in condition
    # A base skipped because no image in the list takes it, or failed on a
    # check of its own, must not skip the rest: the implicit success() would
    # (actions/runner#2205). An image built on base fails at its layout check.
    assert condition.startswith("!cancelled()")
    assert "needs.base" not in condition
    assert "base" in jobs["image"]["needs"]
    assert jobs["image"]["strategy"]["matrix"] == {
        "image": "${{ fromJSON(needs.changes.outputs.images) }}"
    }


def _resolve_images(tmp_path: Path, event: str, changes: str) -> dict[str, str]:
    output = tmp_path / "output"
    proc = _run_step(
        "ci",
        "changes",
        "Resolve the images to test",
        {"GITHUB_EVENT_NAME": event, "CHANGES": changes, "GITHUB_OUTPUT": str(output)},
    )
    assert proc.returncode == 0, proc.stderr
    return _outputs(output)


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
    for step in jobs["base"]["steps"]:
        for script in _scripts_run(step):
            assert _matches(script, filters["base"]), script
    for step in jobs["image"]["steps"]:
        only = re.findall(r"matrix\.image == '([\w-]+)'", step.get("if", ""))
        for image in only or sorted(set(filters) - {"base"}):
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
        "steps.files.outputs.base_from_run == 'true' && needs.base.result != 'success'"
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
    ],
)
def test_only_a_push_writes_the_registry_cache(
    tmp_path: Path, event: str, head_repo: str
) -> None:
    cache = _cache_strategy(tmp_path, event, head_repo)

    assert "type=registry" not in cache["cache_to"]
    assert cache["login"] == "false"


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


def test_a_push_writes_the_registry_cache(tmp_path: Path) -> None:
    cache = _cache_strategy(tmp_path, "push", "")

    assert cache["cache_from"] == REGISTRY_CACHE
    assert cache["cache_to"] == f"{REGISTRY_CACHE},mode=max"
    assert cache["login"] == "true"


def test_a_missing_registry_cache_is_not_read(tmp_path: Path) -> None:
    cache = _cache_strategy(tmp_path, "push", "", cache_exists=False)

    assert cache["cache_from"] == ""
    assert cache["cache_to"] == f"{REGISTRY_CACHE},mode=max"


def test_no_pull_request_build_writes_a_cache_the_strategy_did_not_choose() -> None:
    for name, workflow in _all_workflows().items():
        if "pull_request" not in _triggers(workflow):
            continue
        for job_name, job in workflow["jobs"].items():
            for step in job.get("steps", []):
                if not step.get("uses", "").startswith(BUILD_PUSH_ACTION):
                    continue
                cache_to = step["with"].get("cache-to", "").strip()
                assert cache_to in ("", "${{ steps.cache.outputs.cache_to }}"), (
                    name,
                    job_name,
                    step.get("name"),
                )
    image = _workflow("ci")["jobs"]["image"]
    assert _step(image, "Login to GHCR")["if"] == "steps.cache.outputs.login == 'true'"


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


def test_the_scan_still_blocks_on_critical_and_reports_high() -> None:
    image = _workflow("ci")["jobs"]["image"]
    scan = _step(image, "Scan image with Grype")

    assert scan["with"]["severity-cutoff"] == "critical"
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
