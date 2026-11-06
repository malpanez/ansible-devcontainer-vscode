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
