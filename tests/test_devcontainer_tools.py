import hashlib
import json
import subprocess
import sys
from pathlib import Path


def _compute_signature(template_root: Path) -> str:
    checksums = []
    for file_path in sorted(template_root.rglob("*")):
        if file_path.is_file():
            data = file_path.read_bytes()
            checksums.append(hashlib.sha1(data).hexdigest())
    joined = "".join(checksums).encode()
    return hashlib.sha256(joined).hexdigest()


def _run_script(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_metadata_matches(tmp_path: Path):
    devcontainers = tmp_path / "devcontainers" / "ansible"
    devcontainers.mkdir(parents=True)
    template_file = devcontainers / "devcontainer.json"
    template_file.write_text('{\n  "name": "ansible"\n}\n', encoding="utf-8")

    target = tmp_path / ".devcontainer"
    target.mkdir()
    target_file = target / "devcontainer.json"
    target_file.write_text(template_file.read_text(encoding="utf-8"), encoding="utf-8")

    metadata = {
        "stack": "ansible",
        "source": str(devcontainers),
        "signature": _compute_signature(devcontainers),
    }
    (target / ".template-metadata.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )

    proc = _run_script(
        Path("scripts/devcontainer-metadata.py"),
        "--target",
        str(target),
        "--templates",
        str(tmp_path / "devcontainers"),
    )
    assert proc.returncode == 0, proc.stderr
    assert "Status: OK" in proc.stdout


def test_metadata_mismatch(tmp_path: Path):
    devcontainers = tmp_path / "devcontainers" / "ansible"
    devcontainers.mkdir(parents=True)
    template_file = devcontainers / "devcontainer.json"
    template_file.write_text('{\n  "name": "ansible"\n}\n', encoding="utf-8")

    target = tmp_path / ".devcontainer"
    target.mkdir()
    target_file = target / "devcontainer.json"
    target_file.write_text(template_file.read_text(encoding="utf-8"), encoding="utf-8")

    metadata = {
        "stack": "ansible",
        "source": str(devcontainers),
        "signature": _compute_signature(devcontainers),
    }
    (target / ".template-metadata.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )

    # Modify template after metadata snapshot to create mismatch.
    template_file.write_text(
        '{\n  "name": "ansible", "toggled": true\n}\n', encoding="utf-8"
    )

    proc = _run_script(
        Path("scripts/devcontainer-metadata.py"),
        "--target",
        str(target),
        "--templates",
        str(tmp_path / "devcontainers"),
    )
    assert proc.returncode == 2
    assert "Status: mismatch" in proc.stderr


def test_devcontainer_diff_reports_changes(tmp_path: Path):
    devcontainers = tmp_path / "devcontainers" / "ansible"
    devcontainers.mkdir(parents=True)
    template_file = devcontainers / "devcontainer.json"
    template_file.write_text("root", encoding="utf-8")

    target = tmp_path / ".devcontainer"
    target.mkdir()
    target_file = target / "devcontainer.json"
    target_file.write_text("root-modified", encoding="utf-8")

    (target / ".template-metadata.json").write_text(
        json.dumps({"stack": "ansible"}),
        encoding="utf-8",
    )

    proc = _run_script(
        Path("scripts/devcontainer-diff.py"),
        "--target",
        str(target),
        "--templates",
        str(tmp_path / "devcontainers"),
        "--stack",
        "ansible",
    )
    assert proc.returncode == 2
    assert "@@" in proc.stdout or "+++" in proc.stdout


def test_devcontainer_diff_no_changes(tmp_path: Path):
    devcontainers = tmp_path / "devcontainers" / "ansible"
    devcontainers.mkdir(parents=True)
    template_file = devcontainers / "devcontainer.json"
    template_file.write_text("root", encoding="utf-8")

    target = tmp_path / ".devcontainer"
    target.mkdir()
    target_file = target / "devcontainer.json"
    target_file.write_text("root", encoding="utf-8")

    proc = _run_script(
        Path("scripts/devcontainer-diff.py"),
        "--target",
        str(target),
        "--templates",
        str(tmp_path / "devcontainers"),
        "--stack",
        "ansible",
    )
    assert proc.returncode == 0
    assert "No differences" in proc.stdout
