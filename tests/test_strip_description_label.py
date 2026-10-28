import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "strip-description-label.sh"

METADATA_LABELS = (
    "org.opencontainers.image.created=2026-10-28T15:05:11.874Z\n"
    "org.opencontainers.image.description=Modern, reproducible infrastructure "
    "development environments powered by VS Code Dev Containers\n"
    "org.opencontainers.image.licenses=MIT\n"
    "org.opencontainers.image.revision=8722d1a2ffba887fdb172717d572eb3eff69a2ea\n"
    "org.opencontainers.image.source=https://github.com/malpanez/ansible-devcontainer-vscode\n"
    "org.opencontainers.image.title=ansible-devcontainer-vscode\n"
    "org.opencontainers.image.version=main"
)


def _run(
    labels: str, github_output: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_OUTPUT"}
    env["LABELS"] = labels
    if github_output is not None:
        env["GITHUB_OUTPUT"] = str(github_output)
    return subprocess.run(
        ["bash", str(SCRIPT)], env=env, capture_output=True, text=True, check=False
    )


def test_strip_description_label_metadata_list_drops_only_description() -> None:
    result = _run(METADATA_LABELS)

    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert not [
        line
        for line in lines
        if line.startswith("org.opencontainers.image.description=")
    ]
    expected = [
        line
        for line in METADATA_LABELS.splitlines()
        if not line.startswith("org.opencontainers.image.description=")
    ]
    assert lines == expected


def test_strip_description_label_key_in_another_value_is_kept() -> None:
    labels = "com.example.note=see org.opencontainers.image.description=\norg.opencontainers.image.licenses=MIT"

    result = _run(labels)

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == labels.splitlines()


def test_strip_description_label_github_output_writes_labels_heredoc(
    tmp_path: Path,
) -> None:
    output = tmp_path / "github_output"

    result = _run(METADATA_LABELS, output)

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    written = output.read_text().splitlines()
    assert written[0].startswith("labels<<labels_")
    delimiter = written[0].removeprefix("labels<<")
    assert written[-1] == delimiter
    body = written[1:-1]
    assert (
        "org.opencontainers.image.revision=8722d1a2ffba887fdb172717d572eb3eff69a2ea"
        in body
    )
    assert not [
        line
        for line in body
        if line.startswith("org.opencontainers.image.description=")
    ]


@pytest.mark.parametrize("labels", ["", " \n"])
def test_strip_description_label_empty_labels_fails(labels: str) -> None:
    result = _run(labels)

    assert result.returncode == 1
    assert "LABELS is empty" in result.stderr
