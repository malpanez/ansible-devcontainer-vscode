import dataclasses
import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "refresh-tool-pins.py"
AWS_CLI_SCRIPT = REPO_ROOT / "devcontainers" / "scripts" / "install-aws-cli.sh"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("refresh_tool_pins", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_module()


def _tool(name: str) -> Any:
    return next(tool for tool in MODULE.TOOLS if tool.name == name)


@pytest.mark.parametrize("tool", MODULE.TOOLS, ids=lambda tool: tool.name)
def test_every_pin_pattern_matches_the_repository_once(tool: Any) -> None:
    assert re.fullmatch(r"[0-9]+(\.[0-9]+)+", MODULE.current_version(tool))
    for path, pattern, _url in tool.hash_patterns:
        assert len(re.findall(pattern, path.read_text())) == 1, (path, pattern)


def test_aws_cli_is_pinned_only_in_the_shared_script() -> None:
    aws = _tool("aws-cli")
    assert {path for path, _pattern, _url in aws.hash_patterns} == {AWS_CLI_SCRIPT}
    assert aws.version_pattern[0] == AWS_CLI_SCRIPT
    dockerfiles = [
        *REPO_ROOT.glob("devcontainers/*/Dockerfile*"),
        *REPO_ROOT.glob(".devcontainer/Dockerfile*"),
    ]
    assert dockerfiles
    for dockerfile in dockerfiles:
        text = dockerfile.read_text()
        assert "awscli-exe-linux" not in text, dockerfile
        assert "AWS_CLI_VERSION" not in text, dockerfile


def test_sync_hashes_rewrites_both_aws_cli_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = tmp_path / "install-aws-cli.sh"
    script.write_text(
        "# renovate: datasource=github-tags depName=aws/aws-cli\n"
        "AWS_CLI_VERSION=2.99.1\n"
        f"AWS_CLI_SHA256_X86_64={'a' * 64}\n"
        f"AWS_CLI_SHA256_AARCH64={'a' * 64}\n"
        'echo "${AWS_CLI_SHA256_X86_64}"\n'
    )
    aws = _tool("aws-cli")
    relocated = dataclasses.replace(
        aws,
        version_pattern=(script, aws.version_pattern[1]),
        hash_patterns=[
            (script, pattern, url) for _path, pattern, url in aws.hash_patterns
        ],
    )
    digests = {
        "https://awscli.amazonaws.com/awscli-exe-linux-x86_64-2.99.1.zip": "b" * 64,
        "https://awscli.amazonaws.com/awscli-exe-linux-aarch64-2.99.1.zip": "c" * 64,
    }
    monkeypatch.setattr(MODULE, "TOOLS", [relocated])
    monkeypatch.setattr(MODULE, "sha256_of", lambda url: digests[url])

    assert MODULE.sync_hashes() == 0

    assert script.read_text() == (
        "# renovate: datasource=github-tags depName=aws/aws-cli\n"
        "AWS_CLI_VERSION=2.99.1\n"
        f"AWS_CLI_SHA256_X86_64={'b' * 64}\n"
        f"AWS_CLI_SHA256_AARCH64={'c' * 64}\n"
        'echo "${AWS_CLI_SHA256_X86_64}"\n'
    )
