import os
import re
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "derive-toolchain-versions.sh"

BASE_OK = (
    "# syntax=docker/dockerfile:1.27\nFROM python:3.14.7-slim-bookworm@sha256:abc\n"
)
GOLANG_OK = (
    "# syntax=docker/dockerfile:1.27\nFROM golang:1.27.1-alpine3.23@sha256:def\n"
)
TERRAFORM_OK = (
    "ARG DEBIAN_VERSION=bookworm-slim\n"
    "ARG TERRAFORM_VERSION=1.16.4\n"
    "FROM debian:${DEBIAN_VERSION} AS fetch\n"
    "ARG TERRAFORM_VERSION TFLINT_VERSION\n"
)


def _run(
    env: dict[str, str] | None = None, cwd: Path = REPO_ROOT
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=cwd,
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        check=False,
    )


def _write(
    tmp_path: Path, base: str | None, golang: str | None, terraform: str | None
) -> dict[str, str]:
    env: dict[str, str] = {}
    for variable, name, content in (
        ("BASE_DOCKERFILE", "base.Dockerfile", base),
        ("GOLANG_DOCKERFILE", "golang.Dockerfile", golang),
        ("TERRAFORM_DOCKERFILE", "terraform.Dockerfile", terraform),
    ):
        path = tmp_path / name
        if content is not None:
            path.write_text(content, encoding="utf-8")
        env[variable] = str(path)
    return env


def _parse(stdout: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in stdout.splitlines())


def test_real_dockerfiles_yield_the_versions_they_ship():
    proc = _run()

    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ""
    assert [line.split("=", 1)[0] for line in proc.stdout.splitlines()] == [
        "python_version",
        "go_version",
        "terraform_version",
    ]

    versions = _parse(proc.stdout)
    assert re.fullmatch(r"\d+\.\d+", versions["python_version"])
    assert re.fullmatch(r"\d+\.\d+", versions["go_version"])
    assert re.fullmatch(r"\d+\.\d+\.\d+", versions["terraform_version"])

    base = (REPO_ROOT / "devcontainers/base/Dockerfile").read_text(encoding="utf-8")
    golang = (REPO_ROOT / "devcontainers/golang/Dockerfile").read_text(encoding="utf-8")
    terraform = (REPO_ROOT / "devcontainers/terraform/Dockerfile").read_text(
        encoding="utf-8"
    )
    assert re.search(
        rf"^FROM python:{re.escape(versions['python_version'])}(?:[.\-@]|$)",
        base,
        re.MULTILINE,
    )
    assert re.search(
        rf"^FROM golang:{re.escape(versions['go_version'])}(?:[.\-@]|$)",
        golang,
        re.MULTILINE,
    )
    assert f"\nARG TERRAFORM_VERSION={versions['terraform_version']}\n" in terraform


def test_defaults_do_not_depend_on_the_working_directory(tmp_path: Path):
    assert _run(cwd=tmp_path).stdout == _run().stdout != ""


def test_known_inputs_yield_exact_output(tmp_path: Path):
    proc = _run(_write(tmp_path, BASE_OK, GOLANG_OK, TERRAFORM_OK))

    assert proc.returncode == 0, proc.stderr
    assert (
        proc.stdout
        == "python_version=3.14\ngo_version=1.27\nterraform_version=1.16.4\n"
    )


def test_minor_only_tags_are_accepted(tmp_path: Path):
    env = _write(
        tmp_path,
        "FROM python:3.15-slim-trixie\n",
        "FROM golang:1.28-alpine3.24\n",
        TERRAFORM_OK,
    )
    proc = _run(env)

    assert proc.returncode == 0, proc.stderr
    assert _parse(proc.stdout)["python_version"] == "3.15"
    assert _parse(proc.stdout)["go_version"] == "1.28"


@pytest.mark.parametrize(
    ("base", "golang", "terraform", "missing"),
    [
        (None, GOLANG_OK, TERRAFORM_OK, "base.Dockerfile"),
        (BASE_OK, None, TERRAFORM_OK, "golang.Dockerfile"),
        (BASE_OK, GOLANG_OK, None, "terraform.Dockerfile"),
    ],
)
def test_missing_file_fails_without_output(
    tmp_path: Path,
    base: str | None,
    golang: str | None,
    terraform: str | None,
    missing: str,
):
    proc = _run(_write(tmp_path, base, golang, terraform))

    assert proc.returncode == 1
    assert proc.stdout == ""
    assert (
        f"derive-toolchain-versions: no such file: {tmp_path / missing}" in proc.stderr
    )


@pytest.mark.parametrize(
    ("base", "golang", "terraform", "expected"),
    [
        (
            "FROM python:slim-bookworm\n",
            GOLANG_OK,
            TERRAFORM_OK,
            "FROM python:<major>.<minor>",
        ),
        (
            "FROM debian:bookworm-slim\n",
            GOLANG_OK,
            TERRAFORM_OK,
            "FROM python:<major>.<minor>",
        ),
        (BASE_OK, "FROM golang:alpine\n", TERRAFORM_OK, "FROM golang:<major>.<minor>"),
        (
            BASE_OK,
            GOLANG_OK,
            "ARG TFLINT_VERSION=0.64.0\n",
            "ARG TERRAFORM_VERSION=<major>.<minor>.<patch>",
        ),
        (
            BASE_OK,
            GOLANG_OK,
            "ARG TERRAFORM_VERSION\n",
            "ARG TERRAFORM_VERSION=<major>.<minor>.<patch>",
        ),
        (
            BASE_OK,
            GOLANG_OK,
            "ARG TERRAFORM_VERSION=1.16\n",
            "ARG TERRAFORM_VERSION=<major>.<minor>.<patch>",
        ),
        (
            BASE_OK,
            GOLANG_OK,
            "ARG TERRAFORM_VERSION=latest\n",
            "ARG TERRAFORM_VERSION=<major>.<minor>.<patch>",
        ),
    ],
)
def test_unparseable_value_fails_without_output(
    tmp_path: Path, base: str, golang: str, terraform: str, expected: str
):
    proc = _run(_write(tmp_path, base, golang, terraform))

    assert proc.returncode == 1
    assert proc.stdout == ""
    assert f'derive-toolchain-versions: no "{expected}" line in' in proc.stderr
