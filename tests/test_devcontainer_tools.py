"""
Comprehensive tests for devcontainer tooling scripts.
Target: 95%+ code coverage
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

# lgtm[py/unused-import]
import pytest


# ========== Helper Functions ==========


def _compute_signature(template_root: Path) -> str:
    """Compute signature the same way as devcontainer-metadata.py."""
    checksums = []
    for file_path in sorted(template_root.rglob("*")):
        if file_path.is_file():
            data = file_path.read_bytes()
            checksums.append(hashlib.sha1(data).hexdigest())
    joined = "".join(checksums).encode()
    return hashlib.sha256(joined).hexdigest()


def _run_script(script: Path, *args: str) -> subprocess.CompletedProcess:
    """Run a Python script with given arguments."""
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        check=False,
    )


# ========== devcontainer-metadata.py Tests ==========


def test_metadata_matches(tmp_path: Path):
    """Test that metadata validation passes when signatures match."""
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
    assert "ansible" in proc.stdout


def test_metadata_mismatch(tmp_path: Path):
    """Test that metadata validation fails when signatures don't match."""
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


def test_metadata_file_not_found(tmp_path: Path):
    """Test error when metadata file doesn't exist."""
    target = tmp_path / ".devcontainer"
    target.mkdir()

    proc = _run_script(
        Path("scripts/devcontainer-metadata.py"),
        "--target",
        str(target),
        "--templates",
        str(tmp_path / "devcontainers"),
    )
    assert proc.returncode == 1
    assert "Metadata file not found" in proc.stderr


def test_metadata_missing_stack_field(tmp_path: Path):
    """Test error when metadata is missing stack field."""
    target = tmp_path / ".devcontainer"
    target.mkdir()

    # Metadata without 'stack' field
    metadata = {"source": "some/path"}
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
    assert proc.returncode == 1
    assert "missing 'stack' field" in proc.stderr


def test_metadata_missing_source_field(tmp_path: Path):
    """Test error when metadata is missing source field."""
    target = tmp_path / ".devcontainer"
    target.mkdir()

    # Metadata without 'source' field
    metadata = {"stack": "ansible"}
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
    assert proc.returncode == 1
    assert "missing 'source' field" in proc.stderr


def test_metadata_template_directory_not_found(tmp_path: Path):
    """Test error when template directory doesn't exist."""
    target = tmp_path / ".devcontainer"
    target.mkdir()

    # Metadata pointing to non-existent stack
    metadata = {"stack": "nonexistent", "source": "some/path"}
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
    assert proc.returncode == 1
    assert "not found" in proc.stderr


def test_metadata_with_multiple_files(tmp_path: Path):
    """Test metadata computation with multiple files in template."""
    devcontainers = tmp_path / "devcontainers" / "terraform"
    devcontainers.mkdir(parents=True)

    # Create multiple files
    (devcontainers / "devcontainer.json").write_text('{"name": "terraform"}', encoding="utf-8")
    (devcontainers / "Dockerfile").write_text("FROM ubuntu:latest", encoding="utf-8")
    (devcontainers / "README.md").write_text("# Terraform DevContainer", encoding="utf-8")

    target = tmp_path / ".devcontainer"
    target.mkdir()

    # Copy all files
    for file in devcontainers.rglob("*"):
        if file.is_file():
            rel_path = file.relative_to(devcontainers)
            dest = target / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(file.read_bytes())

    metadata = {
        "stack": "terraform",
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
    assert proc.returncode == 0
    assert "Status: OK" in proc.stdout


# ========== devcontainer-diff.py Tests ==========


def test_devcontainer_diff_reports_changes(tmp_path: Path):
    """Test that diff reports changes when files differ."""
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
    assert "@@" in proc.stdout or "+++" in proc.stdout or "---" in proc.stdout


def test_devcontainer_diff_no_changes(tmp_path: Path):
    """Test that diff shows no changes when files match."""
    devcontainers = tmp_path / "devcontainers" / "ansible"
    devcontainers.mkdir(parents=True)
    template_file = devcontainers / "devcontainer.json"
    template_file.write_text("root", encoding="utf-8")

    target = tmp_path / ".devcontainer"
    target.mkdir()
    target_file = target / "devcontainer.json"
    target_file.write_text("root", encoding="utf-8")

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
    assert proc.returncode == 0
    assert "No differences" in proc.stdout


def test_diff_target_not_found(tmp_path: Path):
    """Test error when target directory doesn't exist."""
    proc = _run_script(
        Path("scripts/devcontainer-diff.py"),
        "--target",
        str(tmp_path / "nonexistent"),
        "--templates",
        str(tmp_path / "devcontainers"),
    )
    assert proc.returncode == 1
    assert "Target directory not found" in proc.stderr


def test_diff_metadata_not_found(tmp_path: Path):
    """Test error when metadata file doesn't exist."""
    target = tmp_path / ".devcontainer"
    target.mkdir()

    proc = _run_script(
        Path("scripts/devcontainer-diff.py"),
        "--target",
        str(target),
        "--templates",
        str(tmp_path / "devcontainers"),
    )
    assert proc.returncode == 1
    assert "Metadata file not found" in proc.stderr


def test_diff_stack_not_specified(tmp_path: Path):
    """Test error when stack is not specified and metadata missing stack."""
    target = tmp_path / ".devcontainer"
    target.mkdir()

    # Metadata without 'stack' field
    (target / ".template-metadata.json").write_text(
        json.dumps({}), encoding="utf-8"
    )

    proc = _run_script(
        Path("scripts/devcontainer-diff.py"),
        "--target",
        str(target),
        "--templates",
        str(tmp_path / "devcontainers"),
    )
    assert proc.returncode == 1
    assert "Stack not specified" in proc.stderr


def test_diff_template_not_found(tmp_path: Path):
    """Test error when template stack doesn't exist."""
    target = tmp_path / ".devcontainer"
    target.mkdir()

    (target / ".template-metadata.json").write_text(
        json.dumps({"stack": "nonexistent"}),
        encoding="utf-8",
    )

    proc = _run_script(
        Path("scripts/devcontainer-diff.py"),
        "--target",
        str(target),
        "--templates",
        str(tmp_path / "devcontainers"),
    )
    assert proc.returncode == 1
    assert "not found" in proc.stderr


def test_diff_added_files(tmp_path: Path):
    """Test that diff reports added files."""
    devcontainers = tmp_path / "devcontainers" / "ansible"
    devcontainers.mkdir(parents=True)
    (devcontainers / "base.json").write_text("{}", encoding="utf-8")

    target = tmp_path / ".devcontainer"
    target.mkdir()
    (target / "base.json").write_text("{}", encoding="utf-8")
    (target / "extra.json").write_text('{"extra": true}', encoding="utf-8")

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
    )
    assert proc.returncode == 2
    assert "Added file" in proc.stdout
    assert "extra.json" in proc.stdout


def test_diff_deleted_files(tmp_path: Path):
    """Test that diff reports missing files from template."""
    devcontainers = tmp_path / "devcontainers" / "ansible"
    devcontainers.mkdir(parents=True)
    (devcontainers / "base.json").write_text("{}", encoding="utf-8")
    (devcontainers / "required.json").write_text('{"required": true}', encoding="utf-8")

    target = tmp_path / ".devcontainer"
    target.mkdir()
    (target / "base.json").write_text("{}", encoding="utf-8")
    # required.json is missing from target

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
    )
    assert proc.returncode == 2
    assert "Missing file from template" in proc.stdout
    assert "required.json" in proc.stdout


def test_diff_explicit_metadata_path(tmp_path: Path):
    """Test diff with explicitly specified metadata path."""
    devcontainers = tmp_path / "devcontainers" / "ansible"
    devcontainers.mkdir(parents=True)
    (devcontainers / "file.txt").write_text("content", encoding="utf-8")

    target = tmp_path / ".devcontainer"
    target.mkdir()
    (target / "file.txt").write_text("content", encoding="utf-8")

    custom_metadata = tmp_path / "custom-metadata.json"
    custom_metadata.write_text(
        json.dumps({"stack": "ansible"}),
        encoding="utf-8",
    )

    proc = _run_script(
        Path("scripts/devcontainer-diff.py"),
        "--target",
        str(target),
        "--templates",
        str(tmp_path / "devcontainers"),
        "--metadata",
        str(custom_metadata),
    )
    assert proc.returncode == 0
    assert "No differences" in proc.stdout


def test_diff_explicit_stack_override(tmp_path: Path):
    """Test diff with --stack argument overriding metadata."""
    devcontainers = tmp_path / "devcontainers" / "terraform"
    devcontainers.mkdir(parents=True)
    (devcontainers / "file.txt").write_text("terraform content", encoding="utf-8")

    target = tmp_path / ".devcontainer"
    target.mkdir()
    (target / "file.txt").write_text("terraform content", encoding="utf-8")

    # Metadata says ansible, but we'll override with --stack terraform
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
        "terraform",
    )
    assert proc.returncode == 0
    assert "No differences" in proc.stdout


def test_diff_binary_file_handling(tmp_path: Path):
    """Test that diff handles binary files correctly."""
    devcontainers = tmp_path / "devcontainers" / "ansible"
    devcontainers.mkdir(parents=True)

    # Create a binary file (non-UTF-8)
    binary_content = bytes([0xFF, 0xFE, 0x00, 0x01, 0x80, 0x90])
    (devcontainers / "binary.bin").write_bytes(binary_content)

    target = tmp_path / ".devcontainer"
    target.mkdir()

    # Different binary content
    different_binary = bytes([0xFF, 0xFE, 0x00, 0x02, 0x80, 0x90])
    (target / "binary.bin").write_bytes(different_binary)

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
    )
    # Should detect difference and show hex diff
    assert proc.returncode == 2


def test_diff_nested_directories(tmp_path: Path):
    """Test diff with nested directory structures."""
    devcontainers = tmp_path / "devcontainers" / "golang"
    devcontainers.mkdir(parents=True)

    # Create nested structure
    (devcontainers / "config" / "settings").mkdir(parents=True)
    (devcontainers / "config" / "settings" / "app.json").write_text(
        '{"nested": true}', encoding="utf-8"
    )
    (devcontainers / "scripts" / "init.sh").write_text(
        "#!/bin/bash\necho init", encoding="utf-8"
    )

    target = tmp_path / ".devcontainer"
    target.mkdir()

    # Copy structure
    (target / "config" / "settings").mkdir(parents=True)
    (target / "config" / "settings" / "app.json").write_text(
        '{"nested": true}', encoding="utf-8"
    )
    (target / "scripts").mkdir()
    (target / "scripts" / "init.sh").write_text(
        "#!/bin/bash\necho init", encoding="utf-8"
    )

    (target / ".template-metadata.json").write_text(
        json.dumps({"stack": "golang"}),
        encoding="utf-8",
    )

    proc = _run_script(
        Path("scripts/devcontainer-diff.py"),
        "--target",
        str(target),
        "--templates",
        str(tmp_path / "devcontainers"),
    )
    assert proc.returncode == 0
    assert "No differences" in proc.stdout
