"""What only a tag push or a nightly would otherwise exercise in these workflows."""

import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"


def _workflow(name: str) -> dict[str, Any]:
    return yaml.safe_load((WORKFLOWS / name).read_text())


def test_publish_waits_for_the_scan_and_the_smoke_of_every_leg() -> None:
    jobs = _workflow("release.yml")["jobs"]

    assert {"resolve", "gate", "smoke"} <= set(jobs["publish"]["needs"])


def test_nothing_runs_on_the_published_tag_after_publish() -> None:
    jobs = _workflow("release.yml")["jobs"]

    for name, job in jobs.items():
        needs = job.get("needs", [])
        assert "publish" not in ([needs] if isinstance(needs, str) else needs), name


def test_smoke_runs_the_digest_not_a_tag() -> None:
    steps = _workflow("release.yml")["jobs"]["smoke"]["steps"]

    refs = [step["env"]["REF"] for step in steps if "REF" in step.get("env", {})]
    assert len(refs) == 3
    assert set(refs) == {"${{ matrix.image }}@${{ matrix.digest }}"}


def test_arm64_is_required_in_the_gate_wherever_it_is_built() -> None:
    steps = _workflow("release.yml")["jobs"]["gate"]["steps"]

    arm64 = next(step for step in steps if step.get("id") == "arm64")
    assert (
        arm64["env"]["REQUIRED"] == "${{ contains(matrix.platforms, 'linux/arm64') }}"
    )


def test_only_the_newest_release_uploads_sarif() -> None:
    steps = _workflow("scan-release-images.yml")["jobs"]["scan"]["steps"]

    uploads = [step for step in steps if "upload-sarif" in step.get("uses", "")]
    assert len(uploads) == 2
    for step in uploads:
        assert "matrix.tag == needs.resolve.outputs.latest" in step["if"]


def test_renovate_manager_matches_the_syft_pin() -> None:
    renovate = json.loads((REPO_ROOT / "renovate.json").read_text())
    managers = [
        manager
        for manager in renovate["customManagers"]
        if any("workflows" in pattern for pattern in manager["managerFilePatterns"])
    ]
    assert len(managers) == 1
    # Renovate writes named groups the JavaScript way.
    pattern = re.compile(managers[0]["matchStrings"][0].replace("(?<", "(?P<"))
    workflow = (WORKFLOWS / "release.yml").read_text()

    matches = [
        match
        for match in pattern.finditer(workflow)
        if match["depName"] == "anchore/syft"
    ]

    assert len(matches) == 1
    assert matches[0]["datasource"] == "github-releases"
    assert re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", matches[0]["currentValue"])
    job = _workflow("release.yml")["jobs"]["publish"]
    assert job["env"]["SYFT_VERSION"] == matches[0]["currentValue"]
    syft = next(step for step in job["steps"] if step.get("id") == "install_syft")
    assert syft["with"]["syft-version"] == "${{ env.SYFT_VERSION }}"
