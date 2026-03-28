import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _compute_signature(template_root: Path) -> str:
    checksums = []
    for file_path in sorted(template_root.rglob("*")):
        if file_path.is_file():
            checksums.append(hashlib.sha1(file_path.read_bytes()).hexdigest())
    return hashlib.sha256("".join(checksums).encode()).hexdigest()


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _run_doctor(
    tmp_path: Path,
    *,
    strict: bool = False,
    fake_tools: tuple[str, ...] = (),
) -> subprocess.CompletedProcess:
    templates = tmp_path / "devcontainers" / "terraform"
    templates.mkdir(parents=True)
    (templates / "devcontainer.json").write_text(
        '{"name":"terraform"}\n', encoding="utf-8"
    )
    (templates / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")

    target = tmp_path / ".devcontainer"
    target.mkdir()
    for file in templates.iterdir():
        if file.is_file():
            (target / file.name).write_bytes(file.read_bytes())

    metadata = {
        "stack": "terraform",
        "source": str(templates),
        "signature": _compute_signature(templates),
    }
    (target / ".template-metadata.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )

    env = os.environ.copy()
    if fake_tools:
        fake_bin = tmp_path / "bin"
        fake_bin.mkdir()
        for tool in fake_tools:
            _write_executable(fake_bin / tool, "#!/usr/bin/env bash\nexit 0\n")
        env["PATH"] = f"{fake_bin}:{env['PATH']}"

    args = [
        "bash",
        "scripts/doctor-devcontainer.sh",
        "--target",
        str(target),
        "--templates",
        str(tmp_path / "devcontainers"),
    ]
    if strict:
        args.append("--strict")

    return subprocess.run(
        args,
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_doctor_passes_with_matching_metadata_and_fake_tooling(tmp_path: Path):
    proc = _run_doctor(tmp_path, fake_tools=("docker", "devcontainer"), strict=True)
    assert proc.returncode == 0, proc.stderr
    assert "[ok] template metadata matches" in proc.stdout
    assert "[ok] target matches template" in proc.stdout


def test_doctor_fails_when_metadata_is_missing(tmp_path: Path):
    templates = tmp_path / "devcontainers" / "ansible"
    templates.mkdir(parents=True)
    (templates / "devcontainer.json").write_text(
        '{"name":"ansible"}\n', encoding="utf-8"
    )

    target = tmp_path / ".devcontainer"
    target.mkdir()
    (target / "devcontainer.json").write_text('{"name":"ansible"}\n', encoding="utf-8")

    proc = subprocess.run(
        [
            "bash",
            "scripts/doctor-devcontainer.sh",
            "--target",
            str(target),
            "--templates",
            str(tmp_path / "devcontainers"),
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 1
    assert "template metadata check failed" in proc.stderr


def test_doctor_strict_fails_when_required_tooling_is_missing(tmp_path: Path):
    proc = _run_doctor(tmp_path, strict=True)
    assert proc.returncode == 1
    assert (
        "neither docker nor podman is available" in proc.stderr
        or "devcontainer not found" in proc.stderr
    )


def test_doctor_accepts_podman_as_container_runtime(tmp_path: Path):
    proc = _run_doctor(tmp_path, strict=True, fake_tools=("podman", "devcontainer"))
    assert proc.returncode == 0, proc.stderr
    assert (
        "[ok] podman available" in proc.stdout or "[ok] docker available" in proc.stdout
    )
