"""The side-by-side ansible-core 2.16 env of devcontainer-ansible.

2.16 is the last ansible-core that manages Python 2.7 and 3.6 targets
(RHEL 7 and 8); 2.17 removed them. These tests tie its pins together: the
legacy uv project, its hashed export, the Dockerfile stage that installs it,
the collections list, and the Renovate rules that keep all of them on lines
that still admit 2.16.
"""

from __future__ import annotations

import json
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY = "devcontainers/ansible/legacy/ansible-core-2.16"
COLLECTIONS = "devcontainers/ansible/collections-legacy-2.16.txt"
DOCKERFILE = "devcontainers/ansible/Dockerfile"
PIN_LINE = re.compile(
    r"(?P<name>[a-z0-9_]+\.[a-z0-9_]+) (?P<version>[0-9]+\.[0-9]+\.[0-9]+) [a-f0-9]{64}"
)


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _renovate() -> dict[str, Any]:
    renovate: dict[str, Any] = json.loads(_read("renovate.json"))
    return renovate


def _rule_index(predicate: Any) -> list[int]:
    return [
        index
        for index, rule in enumerate(_renovate()["packageRules"])
        if predicate(rule)
    ]


def _legacy_lock_version(package: str) -> str:
    lock = tomllib.loads(_read(f"{LEGACY}/uv.lock"))
    versions = [p["version"] for p in lock["package"] if p["name"] == package]
    assert len(versions) == 1, versions
    version: str = versions[0]
    return version


def test_legacy_project_pins_ansible_core_2_16_on_python_3_12() -> None:
    project = tomllib.loads(_read(f"{LEGACY}/pyproject.toml"))["project"]

    assert project["requires-python"] == "==3.12.*"
    assert project["dependencies"] == ["ansible-core>=2.16.20,<2.17"]
    assert _legacy_lock_version("ansible-core").startswith("2.16.")


def test_legacy_export_is_hashed_and_matches_the_lock() -> None:
    export = _read(f"{LEGACY}/requirements.txt")
    pinned = re.findall(r"^([a-z0-9-]+)==(\S+)", export, flags=re.MULTILINE)

    assert pinned, "no pinned requirement in the export"
    for name, version in pinned:
        assert _legacy_lock_version(name) == version, name
    requirements = [
        block for block in export.split("\n") if re.match(r"^[a-z0-9-]+==", block)
    ]
    assert all(line.rstrip().endswith("\\") for line in requirements)
    assert export.count("--hash=sha256:") >= len(pinned)


def test_renovate_post_process_regenerates_the_export_as_it_was_made() -> None:
    # The export's header records the command that wrote it; the workflow
    # must run that same command, or every Renovate PR rewrites the header.
    header = _read(f"{LEGACY}/requirements.txt").splitlines()[1].lstrip("# ").strip()
    workflow = _read(".github/workflows/renovate-postprocess.yml")
    line = next(
        text.strip() for text in workflow.splitlines() if "uv export --project" in text
    )

    assert f"legacy={LEGACY}" in workflow
    assert line.replace('"${legacy}', LEGACY).replace('"', "") == header


def test_renovate_holds_the_legacy_ansible_core_below_2_17() -> None:
    rules = _renovate()["packageRules"]
    legacy = _rule_index(
        lambda r: (
            r.get("matchPackageNames") == ["ansible-core"]
            and r.get("matchFileNames") == [f"{LEGACY}/**"]
        )
    )
    root = _rule_index(
        lambda r: (
            r.get("matchPackageNames") == ["ansible-core"] and "matchFileNames" not in r
        )
    )

    assert len(legacy) == 1 and len(root) == 1
    assert rules[legacy[0]]["allowedVersions"] == "<2.17"
    assert rules[legacy[0]]["matchDatasources"] == ["pypi"]
    # Later rules win: the legacy hold must come after the root one.
    assert legacy[0] > root[0]


def test_renovate_disables_the_generated_legacy_export() -> None:
    generated = _rule_index(
        lambda r: "requirements-ansible.txt" in r.get("matchFileNames", [])
    )

    assert len(generated) == 1
    rule = _renovate()["packageRules"][generated[0]]
    assert f"{LEGACY}/requirements.txt" in rule["matchFileNames"]
    assert rule["enabled"] is False


def test_legacy_python_is_a_3_12_pin_renovate_tracks_and_holds() -> None:
    dockerfile = _read(DOCKERFILE)
    renovate = _renovate()
    managers = [
        m
        for m in renovate["customManagers"]
        if any("LEGACY_ANSIBLE_PYTHON_VERSION" in s for s in m["matchStrings"])
    ]

    assert len(managers) == 1
    pattern = managers[0]["matchStrings"][0].replace("(?<", "(?P<")
    found = re.findall(pattern, dockerfile)
    assert len(found) == 1 and re.fullmatch(r"3\.12\.[0-9]+", found[0])
    assert managers[0]["depNameTemplate"] == "python"
    assert managers[0]["datasourceTemplate"] == "docker"

    rules = renovate["packageRules"]
    hold = _rule_index(
        lambda r: (
            r.get("matchFileNames") == [DOCKERFILE]
            and r.get("matchPackageNames") == ["python"]
        )
    )
    python_group = _rule_index(
        lambda r: (
            r.get("groupName") == "python" and r.get("matchPackageNames") == ["python"]
        )
    )
    assert len(hold) == 1 and len(python_group) == 1
    assert re.match(rules[hold[0]]["allowedVersions"].strip("/"), "3.12.99")
    assert not re.match(rules[hold[0]]["allowedVersions"].strip("/"), "3.13.0")
    assert hold[0] > python_group[0]


def _collection_holds() -> dict[str, int]:
    holds: dict[str, int] = {}
    for rule in _renovate()["packageRules"]:
        if rule.get("matchFileNames") != [COLLECTIONS]:
            continue
        match = re.fullmatch(r"<([0-9]+)\.0\.0", rule["allowedVersions"])
        assert match, rule
        for name in rule["matchPackageNames"]:
            holds[name] = int(match.group(1))
    return holds


def test_legacy_collections_stay_below_their_renovate_hold() -> None:
    pins = [
        line
        for line in _read(COLLECTIONS).splitlines()
        if line and not line.startswith("#")
    ]
    holds = _collection_holds()

    assert pins
    names = set()
    for line in pins:
        match = PIN_LINE.fullmatch(line)
        assert match, line
        name, version = match.group("name", "version")
        names.add(name)
        # community.general 12.x requires ansible-core >= 2.17.
        assert int(version.split(".")[0]) < holds[name], line
    assert names == set(holds)
    assert holds["community.general"] == 12


def test_legacy_list_is_one_the_shared_tooling_picks_up() -> None:
    # refresh-collection-pins.py and the Renovate collection manager both
    # select collections*.txt in devcontainers/ansible.
    manager = next(
        m
        for m in _renovate()["customManagers"]
        if m.get("datasourceTemplate") == "galaxy-collection"
    )
    pattern = manager["managerFilePatterns"][0].strip("/")

    assert re.search(pattern, COLLECTIONS)
    assert (REPO_ROOT / COLLECTIONS) in (REPO_ROOT).glob(
        "devcontainers/ansible/collections*.txt"
    )


def test_dockerfile_installs_the_legacy_export_and_links_the_commands() -> None:
    dockerfile = _read(DOCKERFILE)

    assert f"source={LEGACY}/requirements.txt" in dockerfile
    assert f"source={COLLECTIONS}" in dockerfile
    assert "--require-hashes --only-binary :all: -r /tmp/requirements-legacy.txt" in (
        dockerfile
    )
    assert f"{LEGACY}/wrapper.sh /opt/ansible-core-2.16/bin/wrapper" in dockerfile
    for tool in ("ansible-console", "ansible-pull", "ansible-vault"):
        assert re.search(rf"for TOOL in [^;]*\b{tool}\b", dockerfile), tool
    assert '"/usr/local/bin/${TOOL}-2.16"' in dockerfile
    # Never in the podman image, which ansible.yaml also tests.
    assert "2.16" not in _read("devcontainers/ansible/Dockerfile.podman")


@pytest.mark.parametrize(
    ("image", "legacy"),
    [("ansible", True), ("ansible-aws", True), ("ansible-podman", False)],
)
def test_structure_tests_cover_the_legacy_env_where_it_ships(
    image: str, legacy: bool
) -> None:
    out = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/resolve-image-files.sh"), image],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    configs = dict(line.split("=", 1) for line in out.splitlines())["configs"].split()

    assert ("ansible-legacy" in configs) is legacy
    assert configs[0] == "ansible"


def test_renovate_never_moves_the_legacy_requires_python() -> None:
    # ansible-core 2.16 runs on CPython 3.12; Renovate's pep621 manager read
    # requires-python "==3.12.*" as a dependency and opened #679 for 3.15.
    rules = [
        rule
        for rule in _renovate()["packageRules"]
        if rule.get("matchDepTypes") == ["requires-python"]
        and rule.get("matchFileNames") == [f"{LEGACY}/pyproject.toml"]
    ]

    assert len(rules) == 1
    assert rules[0]["enabled"] is False
