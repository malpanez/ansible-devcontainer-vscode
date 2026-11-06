import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "release-images.py"
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "smoke-devcontainer-image.sh"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

OWNER = "example"
NEWEST = "v2.2.0"
OLDER = "v2.0.0"
PYTAG = "py314"
DIGEST = "sha256:" + "a" * 64
MULTI_ARCH = "linux/amd64,linux/arm64"


@pytest.fixture(scope="module")
def module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("release_images", SCRIPT)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def _workflow(name: str) -> dict[str, Any]:
    return yaml.safe_load((WORKFLOWS / name).read_text())


def _run(
    *args: str, stdin: str = "", isolated: bool = True, cwd: Path = REPO_ROOT
) -> subprocess.CompletedProcess[str]:
    interpreter = [sys.executable, "-I"] if isolated else [sys.executable]
    return subprocess.run(
        [*interpreter, str(SCRIPT), *args],
        cwd=cwd,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def _pin(name: str = "ansible", tag: str = NEWEST, digest: str = DIGEST) -> str:
    return f"ghcr.io/{OWNER}/devcontainer-{name}:{tag}@{digest}"


def _template(
    root: Path, relative: str, image: object = None, text: str | None = None
) -> None:
    path = root / "devcontainers" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"name": "x", "image": image}) if text is None else text)


def _scan(root: Path, *extra: str) -> tuple[list[dict[str, str]], str]:
    proc = _run(
        "scan-targets",
        "--newest",
        NEWEST,
        "--pytag",
        PYTAG,
        "--owner",
        OWNER,
        "--root",
        str(root),
        *extra,
    )
    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.splitlines()
    assert len(lines) == 1
    key, value = lines[0].split("=", 1)
    assert key == "targets"
    return json.loads(value), proc.stderr


def _extra_legs(targets: list[dict[str, str]]) -> list[dict[str, str]]:
    return [target for target in targets if target["tag"] != NEWEST]


# The list against what really builds the images


def test_images_are_what_build_containers_builds(module: ModuleType) -> None:
    jobs = _workflow("build-containers.yml")["jobs"]
    built = {"base": jobs["build-base"]["env"]["PLATFORMS"]}
    for row in jobs["build-all"]["strategy"]["matrix"]["include"]:
        built[f"{row['stack']}{row['variant']}"] = row["platforms"]

    assert module.IMAGES == built


def test_every_image_has_a_stack_in_the_smoke_script_and_takes_a_digest_ref(
    module: ModuleType, tmp_path: Path
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    docker.write_text('#!/bin/sh\nprintf \'%s\\n\' "$*" >> "$FAKE_LOG"\n')
    docker.chmod(0o755)
    log = tmp_path / "docker.log"
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "FAKE_LOG": str(log),
    }
    for name in module.IMAGES:
        ref = f"ghcr.io/{OWNER}/devcontainer-{name}@{DIGEST}"
        proc = subprocess.run(
            [
                "bash",
                str(SMOKE_SCRIPT),
                "--stack",
                name.removesuffix("-podman"),
                "--image",
                ref,
            ],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        assert proc.returncode == 0, proc.stderr
        assert f" {ref} " in log.read_text().splitlines()[-1]


def test_names_prints_every_image_once_per_line(module: ModuleType) -> None:
    proc = _run("names")

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == list(module.IMAGES)


# release.yml's matrices


def _records(*names: str) -> list[dict[str, str]]:
    return [
        {
            "name": name,
            "image": f"ghcr.io/{OWNER}/devcontainer-{name}",
            "digest": DIGEST,
            "source": "main",
            "revision": "b" * 40,
            "version_tag": NEWEST,
        }
        for name in names
    ]


def test_gate_outputs_keep_the_records_and_add_platforms() -> None:
    records = _records("golang", "latex")

    proc = _run("gate-outputs", stdin=json.dumps(records))

    assert proc.returncode == 0, proc.stderr
    lines = dict(line.split("=", 1) for line in proc.stdout.splitlines())
    assert set(lines) == {"images", "smoke_legs"}
    images = json.loads(lines["images"])
    assert images == [
        {**records[0], "platforms": MULTI_ARCH},
        {**records[1], "platforms": "linux/amd64"},
    ]


def test_smoke_legs_are_one_per_image_and_platform_and_latex_has_no_arm64(
    module: ModuleType,
) -> None:
    _, legs = module.gate_outputs(_records(*module.IMAGES))

    assert len(legs) == 2 * len(module.IMAGES) - 1
    assert {leg["name"] for leg in legs if leg["arch"] == "amd64"} == set(module.IMAGES)
    assert {leg["name"] for leg in legs if leg["arch"] == "arm64"} == set(
        module.IMAGES
    ) - {"latex"}
    assert {(leg["platform"], leg["runner"]) for leg in legs} == {
        ("linux/amd64", "ubuntu-24.04"),
        ("linux/arm64", "ubuntu-24.04-arm"),
    }
    assert all(leg["digest"] == DIGEST for leg in legs)


@pytest.mark.parametrize(
    "stdin",
    [
        "not json",
        "[]",
        "{}",
        '["golang"]',
        '[{"name": "unknown", "image": "x", "digest": "y"}]',
        '[{"name": "golang"}]',
    ],
)
def test_gate_outputs_fail_closed_on_bad_records(stdin: str) -> None:
    proc = _run("gate-outputs", stdin=stdin)

    assert proc.returncode == 1
    assert "::error::" in proc.stderr
    assert proc.stdout == ""


# ci.yml's image legs and candidate builds


def _ci_matrix(mode: str, images: str, base: str) -> dict[str, str]:
    proc = _run("ci-matrix", "--mode", mode, "--images", images, "--base", base)
    assert proc.returncode == 0, proc.stderr
    return dict(line.split("=", 1) for line in proc.stdout.splitlines())


def test_verification_tests_the_amd64_build_of_each_image_and_builds_nothing() -> None:
    lines = _ci_matrix("verification", '["golang","latex"]', "true")

    assert json.loads(lines["legs"]) == [
        {
            "image": name,
            "platform": "linux/amd64",
            "arch": "amd64",
            "runner": "ubuntu-24.04",
        }
        for name in ("golang", "latex")
    ]
    assert json.loads(lines["builds"]) == []


def test_candidate_tests_every_published_platform_base_first(
    module: ModuleType,
) -> None:
    stacks = [name for name in module.IMAGES if name != "base"]

    lines = _ci_matrix("candidate", json.dumps(stacks), "true")

    legs = json.loads(lines["legs"])
    assert [leg["image"] for leg in legs[:2]] == ["base", "base"]
    assert len(legs) == 2 * len(module.IMAGES) - 1
    assert {leg["image"] for leg in legs if leg["arch"] == "arm64"} == set(
        module.IMAGES
    ) - {"latex"}
    assert all(leg["runner"] == module.RUNNERS[leg["platform"]] for leg in legs)
    assert json.loads(lines["builds"]) == [
        {"image": name, "platforms": module.IMAGES[name]} for name in stacks
    ]
    assert lines["base_platforms"] == module.IMAGES["base"]


def test_candidate_without_base_tests_no_base() -> None:
    lines = _ci_matrix("candidate", '["latex"]', "false")

    assert [leg["image"] for leg in json.loads(lines["legs"])] == ["latex"]
    assert json.loads(lines["builds"]) == [
        {"image": "latex", "platforms": "linux/amd64"}
    ]


@pytest.mark.parametrize(
    ("mode", "images", "base"),
    [
        ("publish", "[]", "false"),
        ("", "[]", "false"),
        ("candidate", "not json", "false"),
        ("candidate", '{"golang": 1}', "false"),
        ("candidate", '["base"]', "true"),
        ("candidate", '["unknown"]', "false"),
        ("candidate", '["golang","golang"]', "false"),
        ("candidate", "[]", "yes"),
    ],
)
def test_ci_matrix_fails_closed_on_bad_input(mode: str, images: str, base: str) -> None:
    proc = _run("ci-matrix", "--mode", mode, "--images", images, "--base", base)

    assert proc.returncode == 1
    assert "::error::" in proc.stderr
    assert proc.stdout == ""


# The nightly scan's targets


def test_pins_equal_to_the_newest_release_add_no_legs(
    module: ModuleType, tmp_path: Path
) -> None:
    _template(tmp_path, "ansible/devcontainer.json", _pin("ansible", NEWEST))
    _template(tmp_path, "golang/devcontainer.json", _pin("golang", NEWEST))

    targets, warnings = _scan(tmp_path)

    assert warnings == ""
    assert [target["name"] for target in targets] == list(module.IMAGES)
    assert {target["tag"] for target in targets} == {NEWEST}


def test_newest_release_gets_the_stream_tagged_base_and_plain_labels(
    tmp_path: Path,
) -> None:
    targets, _ = _scan(tmp_path)

    by_name = {target["name"]: target for target in targets}
    assert by_name["base"]["version_tag"] == f"{PYTAG}-{NEWEST}"
    assert by_name["ansible"]["version_tag"] == NEWEST
    assert by_name["latex"]["platforms"] == "linux/amd64"
    assert by_name["golang"]["platforms"] == MULTI_ARCH
    assert all(target["label"] == target["name"] for target in targets)


def test_a_lagging_pin_adds_a_leg_that_names_its_tag(tmp_path: Path) -> None:
    _template(tmp_path, "latex/devcontainer.json", _pin("latex", OLDER))

    targets, warnings = _scan(tmp_path)

    assert warnings == ""
    assert _extra_legs(targets) == [
        {
            "name": "latex",
            "tag": OLDER,
            "version_tag": OLDER,
            "platforms": "linux/amd64",
            "label": f"latex {OLDER}",
        }
    ]


def test_a_lagging_pin_adds_no_base_leg_of_its_own(tmp_path: Path) -> None:
    _template(tmp_path, "ansible/devcontainer.json", _pin("ansible", OLDER))

    targets, _ = _scan(tmp_path)

    assert [leg["name"] for leg in _extra_legs(targets)] == ["ansible"]
    assert [t["tag"] for t in targets if t["name"] == "base"] == [NEWEST]


def test_duplicate_pins_collapse(tmp_path: Path) -> None:
    other_digest = "sha256:" + "c" * 64
    _template(tmp_path, "ansible/devcontainer.json", _pin("ansible", OLDER))
    _template(tmp_path, "ansible/devcontainer.dind.json", _pin("ansible", OLDER))
    _template(
        tmp_path,
        "ansible/devcontainer.docker-socket.json",
        _pin("ansible", OLDER, other_digest),
    )

    targets, _ = _scan(tmp_path)

    assert [leg["label"] for leg in _extra_legs(targets)] == [f"ansible {OLDER}"]


def test_two_lagging_versions_of_an_image_are_two_legs_in_a_stable_order(
    tmp_path: Path,
) -> None:
    _template(tmp_path, "terraform/devcontainer.json", _pin("terraform", "v2.1.0"))
    _template(tmp_path, "terraform/devcontainer.aws.json", _pin("terraform", OLDER))
    _template(tmp_path, "ansible/devcontainer.json", _pin("ansible", OLDER))

    targets, _ = _scan(tmp_path)

    assert [leg["label"] for leg in _extra_legs(targets)] == [
        f"ansible {OLDER}",
        f"terraform {OLDER}",
        "terraform v2.1.0",
    ]


def test_a_pin_newer_than_the_newest_release_is_still_scanned(tmp_path: Path) -> None:
    _template(tmp_path, "golang/devcontainer.json", _pin("golang", "v9.9.9"))

    targets, _ = _scan(tmp_path)

    assert [leg["label"] for leg in _extra_legs(targets)] == ["golang v9.9.9"]


@pytest.mark.parametrize(
    ("image", "reason"),
    [
        (_pin("ansible", "latest"), 'pins the tag "latest"'),
        (f"ghcr.io/{OWNER}/devcontainer-ansible:latest", "not <registry>"),
        (f"ghcr.io/{OWNER}/devcontainer-ansible:{OLDER}", "not <registry>"),
        (f"ghcr.io/{OWNER}/devcontainer-ansible@{DIGEST}", "not <registry>"),
        (None, "not <registry>"),
        (42, "not <registry>"),
        (_pin("ansible", "py314-v2.0.0"), 'pins the tag "py314-v2.0.0"'),
        (_pin("unknown", OLDER), "not one of"),
        (f"ghcr.io/someone-else/devcontainer-ansible:{OLDER}@{DIGEST}", "not one of"),
        (f"docker.io/library/ansible:{OLDER}@{DIGEST}", "not one of"),
    ],
)
def test_a_pin_that_cannot_be_scanned_warns_and_adds_no_leg(
    module: ModuleType, tmp_path: Path, image: object, reason: str
) -> None:
    _template(tmp_path, "ansible/devcontainer.json", image)

    targets, warnings = _scan(tmp_path)

    assert warnings.startswith("::warning::devcontainers/ansible/devcontainer.json:")
    assert reason in warnings
    assert [target["name"] for target in targets] == list(module.IMAGES)
    assert _extra_legs(targets) == []


@pytest.mark.parametrize("text", ["{not json", "[]", '"a string"'])
def test_a_template_that_is_not_an_object_warns_and_adds_no_leg(
    tmp_path: Path, text: str
) -> None:
    _template(tmp_path, "ansible/devcontainer.json", text=text)
    _template(tmp_path, "golang/devcontainer.json", _pin("golang", OLDER))

    targets, warnings = _scan(tmp_path)

    assert "::warning::devcontainers/ansible/devcontainer.json:" in warnings
    assert [leg["label"] for leg in _extra_legs(targets)] == [f"golang {OLDER}"]


def test_a_template_with_comments_and_trailing_commas_is_read(tmp_path: Path) -> None:
    text = (
        "// the published image\n"
        '{\n  "image": "' + _pin("golang", OLDER) + '", // pinned\n}\n'
    )
    _template(tmp_path, "golang/devcontainer.json", text=text)

    targets, warnings = _scan(tmp_path)

    assert warnings == ""
    assert [leg["label"] for leg in _extra_legs(targets)] == [f"golang {OLDER}"]


def test_local_build_is_not_read(tmp_path: Path) -> None:
    _template(tmp_path, "golang/local-build/devcontainer.json", text="{not json")

    targets, warnings = _scan(tmp_path)

    assert warnings == ""
    assert _extra_legs(targets) == []


def test_requested_release_scans_only_that_release(
    module: ModuleType, tmp_path: Path
) -> None:
    _template(tmp_path, "ansible/devcontainer.json", _pin("ansible", OLDER))
    _template(tmp_path, "golang/devcontainer.json", text="{not json")

    targets, warnings = _scan(tmp_path, "--requested", "v1.5.0")

    assert warnings == ""
    assert [target["name"] for target in targets] == list(module.IMAGES)
    assert {target["tag"] for target in targets} == {"v1.5.0"}
    by_name = {target["name"]: target for target in targets}
    assert by_name["base"]["version_tag"] == f"{PYTAG}-v1.5.0"
    assert by_name["ansible"]["label"] == "ansible v1.5.0"


def test_requesting_the_newest_release_adds_no_pins_and_no_tag_in_labels(
    tmp_path: Path,
) -> None:
    _template(tmp_path, "ansible/devcontainer.json", _pin("ansible", OLDER))

    targets, _ = _scan(tmp_path, "--requested", NEWEST)

    assert _extra_legs(targets) == []
    assert all(target["label"] == target["name"] for target in targets)


@pytest.mark.parametrize(
    "args",
    [
        ("--newest", "", "--pytag", PYTAG, "--owner", OWNER),
        ("--newest", NEWEST, "--pytag", "", "--owner", OWNER),
        ("--newest", NEWEST, "--pytag", PYTAG, "--owner", ""),
    ],
)
def test_empty_inputs_fail_closed(args: tuple[str, ...]) -> None:
    proc = _run("scan-targets", *args)

    assert proc.returncode == 1
    assert "::error::" in proc.stderr
    assert proc.stdout == ""


def test_usage_errors_exit_2() -> None:
    assert _run().returncode == 2
    assert _run("unknown").returncode == 2
    assert _run("scan-targets", "--newest", NEWEST).returncode == 2


def test_works_without_isolation_as_the_workflows_call_it() -> None:
    proc = _run(
        "scan-targets",
        "--newest",
        NEWEST,
        "--pytag",
        PYTAG,
        "--owner",
        "malpanez",
        isolated=False,
    )

    assert proc.returncode == 0, proc.stderr


def test_this_repository_has_no_pin_the_scan_would_drop() -> None:
    proc = _run(
        "scan-targets",
        "--newest",
        NEWEST,
        "--pytag",
        PYTAG,
        "--owner",
        "malpanez",
        "--root",
        str(REPO_ROOT),
    )

    assert proc.returncode == 0
    assert proc.stderr == ""
