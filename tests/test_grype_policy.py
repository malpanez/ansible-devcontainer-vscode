from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]


def _rules(vulnerability: str) -> list[dict[str, Any]]:
    policy = yaml.safe_load((REPO_ROOT / ".grype.yaml").read_text(encoding="utf-8"))
    return [
        rule for rule in policy["ignore"] if rule.get("vulnerability") == vulnerability
    ]


def test_the_compress_exception_lapses_when_either_binary_changes() -> None:
    # grype ANDs a rule's conditions and compares the version for equality
    # (grype/match/ignore.go at v0.118.0), so a rule that names the embedded
    # version stops matching when Renovate moves the tool: the gate asks
    # again. The versions are the ones grype printed for #636's candidates.
    rules = _rules("GO-2026-6865")

    assert {
        (rule["package"]["location"], rule["package"]["version"]) for rule in rules
    } == {
        ("/usr/local/bin/terraform", "v1.19.1"),
        ("/usr/local/bin/terragrunt", "v1.19.2"),
    }
    for rule in rules:
        assert set(rule) == {"vulnerability", "package"}
        assert set(rule["package"]) == {"name", "version", "location"}
        assert rule["package"]["name"] == "github.com/klauspost/compress"


def test_the_cpython_fips_exception_covers_only_3_14_10() -> None:
    # CVE-2026-119170 affects only CPython 3.14.10, and grype compares the
    # rule's version for equality, so these rules lapse on the first bump.
    # The locations are the ones the scans of 2026-11-16 reported.
    rules = _rules("CVE-2026-119170")

    assert {rule["package"]["location"] for rule in rules} == {
        "/usr/local/bin/python3.14",
        "/opt/devcontainer-tools/python/cpython-3.14.10-*/bin/python3.14",
    }
    for rule in rules:
        assert set(rule) == {"vulnerability", "package"}
        assert rule["package"] == {
            "name": "python",
            "version": "3.14.10",
            "location": rule["package"]["location"],
        }
