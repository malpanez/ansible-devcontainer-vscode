import json
import tomllib
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]


def _molecule_distros() -> list[str]:
    ci = yaml.safe_load(
        (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    )
    return ci["jobs"]["molecule"]["strategy"]["matrix"]["distro"]


def test_ubuntu_2404_hosts_can_install_the_ansible_requirements() -> None:
    # ansible_environment runs `uv pip install --system` on the host, and
    # Ubuntu 24.04's interpreter is 3.12. ansible-core 2.22 requires
    # Python >= 3.13, so while ubuntu2404 is supported the pin stays on 2.21
    # (#659 broke develop's Molecule run on 2026-11-17).
    assert "ubuntu2404" in _molecule_distros()
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]

    assert project["requires-python"] == ">=3.12"
    assert "ansible-core>=2.21.5,<2.22.0" in project["dependencies"]


def test_renovate_holds_ansible_core_below_2_22() -> None:
    renovate = json.loads((REPO_ROOT / "renovate.json").read_text(encoding="utf-8"))
    rules = [
        rule
        for rule in renovate["packageRules"]
        if rule.get("matchPackageNames") == ["ansible-core"]
        # The legacy 2.16 env's hold (tests/test_ansible_legacy.py).
        and "matchFileNames" not in rule
    ]

    assert len(rules) == 1
    assert rules[0]["matchDatasources"] == ["pypi"]
    assert rules[0]["allowedVersions"] == "<2.22"
