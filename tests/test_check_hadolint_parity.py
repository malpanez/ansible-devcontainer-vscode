import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check-hadolint-parity.sh"

FILES = {
    "ci": ("HADOLINT_CI_WORKFLOW", "ci.yml"),
    "makefile": ("HADOLINT_MAKEFILE", "Makefile"),
    "pre_commit": ("HADOLINT_PRE_COMMIT_CONFIG", "pre-commit-config.yaml"),
}


def _workflow(version: str | None) -> str:
    pin = (
        ""
        if version is None
        else (
            "  # renovate: datasource=docker depName=hadolint/hadolint\n"
            f'  HADOLINT_VERSION: "{version}"\n'
        )
    )
    return (
        "---\n"
        "env:\n"
        '  UV_VERSION: "0.13.0"\n'
        f"{pin}"
        "jobs:\n"
        "  lint:\n"
        "    steps:\n"
        '      - run: docker run --rm -i "hadolint/hadolint:${HADOLINT_VERSION}" < f\n'
    )


def _makefile(version: str | None) -> str:
    image = "hadolint/hadolint" if version is None else f"hadolint/hadolint:{version}"
    return f'validate-docker:\n\tdocker run --rm -i {image} < "$$f" || exit 1\n'


def _pre_commit(version: str | None) -> str:
    hadolint = (
        ""
        if version is None
        else (
            "  - repo: https://github.com/AleksaC/hadolint-py\n"
            f"    rev: {version}\n"
            "    hooks:\n"
            "      - id: hadolint\n"
        )
    )
    return (
        "repos:\n"
        "  - repo: https://github.com/shellcheck-py/shellcheck-py\n"
        "    rev: v0.10.0.1\n"
        "    hooks:\n"
        "      - id: shellcheck\n"
        f"{hadolint}"
        "  - repo: https://github.com/antonbabenko/pre-commit-terraform\n"
        "    rev: v1.96.2\n"
        "    hooks:\n"
        "      - id: terraform_fmt\n"
    )


RENDERERS = {
    "ci": _workflow,
    "makefile": _makefile,
    "pre_commit": _pre_commit,
}


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


def _write(tmp_path: Path, **versions: str | None) -> dict[str, str]:
    env: dict[str, str] = {}
    for key, (variable, name) in FILES.items():
        path = tmp_path / name
        path.write_text(RENDERERS[key](versions.get(key, "v2.15.1")), encoding="utf-8")
        env[variable] = str(path)
    return env


def _found(stdout: str) -> dict[str, str]:
    return dict(
        line.split(maxsplit=1)
        for line in stdout.splitlines()
        if not line.startswith("check-hadolint-parity:")
    )


def _errors(stderr: str) -> list[str]:
    return [line for line in stderr.splitlines() if line.startswith("::error ")]


def test_real_repository_pins_one_hadolint_version() -> None:
    proc = _run()

    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ""
    found = _found(proc.stdout)
    assert list(found) == [
        ".github/workflows/ci.yml",
        "Makefile",
        ".pre-commit-config.yaml",
    ]
    assert len(set(found.values())) == 1


def test_defaults_do_not_depend_on_the_working_directory(tmp_path: Path) -> None:
    assert _run(cwd=tmp_path).stdout == _run().stdout != ""


def test_equal_pins_pass_and_are_printed_per_file(tmp_path: Path) -> None:
    env = _write(tmp_path)
    proc = _run(env)

    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ""
    assert _found(proc.stdout) == {path: "2.15.1" for path in env.values()}
    assert proc.stdout.splitlines()[-1] == (
        "check-hadolint-parity: all 3 call sites pin hadolint 2.15.1"
    )


@pytest.mark.parametrize("differing", ["makefile", "pre_commit"])
def test_one_differing_pin_fails_and_names_only_that_file(
    tmp_path: Path, differing: str
) -> None:
    env = _write(tmp_path, **{differing: "v2.14.0"})
    proc = _run(env)
    variable, _ = FILES[differing]

    assert proc.returncode == 1
    errors = _errors(proc.stderr)
    assert len(errors) == 1
    assert f"::error file={env[variable]}::" in errors[0]
    assert "pins hadolint 2.14.0" in errors[0]
    assert f"({env['HADOLINT_CI_WORKFLOW']}) runs 2.15.1" in errors[0]
    assert _found(proc.stdout)[env[variable]] == "2.14.0"


def test_differing_gate_pin_fails_and_names_every_other_file(tmp_path: Path) -> None:
    env = _write(tmp_path, ci="v2.16.0")
    proc = _run(env)

    assert proc.returncode == 1
    errors = _errors(proc.stderr)
    assert len(errors) == 2
    for variable in (
        "HADOLINT_MAKEFILE",
        "HADOLINT_PRE_COMMIT_CONFIG",
    ):
        assert any(f"file={env[variable]}::" in error for error in errors)


@pytest.mark.parametrize("rev", ["v2.15.1.3", "2.15.1", '"v2.15.1"', "'v2.15.1.0'"])
def test_pre_commit_rev_equal_on_first_three_components_passes(
    tmp_path: Path, rev: str
) -> None:
    proc = _run(_write(tmp_path, pre_commit=rev))

    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ""


def test_four_component_pre_commit_rev_differing_on_patch_fails(
    tmp_path: Path,
) -> None:
    env = _write(tmp_path, pre_commit="v2.15.10.1")
    proc = _run(env)

    assert proc.returncode == 1
    assert f"file={env['HADOLINT_PRE_COMMIT_CONFIG']}::" in proc.stderr
    assert "pins hadolint 2.15.10" in proc.stderr


def test_docker_tag_variant_suffix_is_ignored(tmp_path: Path) -> None:
    proc = _run(_write(tmp_path, makefile="v2.15.1-alpine"))

    assert proc.returncode == 0, proc.stderr


@pytest.mark.parametrize("missing", ["ci", "makefile", "pre_commit"])
def test_missing_pin_fails_and_names_the_file(tmp_path: Path, missing: str) -> None:
    env = _write(tmp_path, **{missing: None})
    proc = _run(env)
    variable, _ = FILES[missing]

    assert proc.returncode == 1
    errors = _errors(proc.stderr)
    assert len(errors) == 1
    assert f"::error file={env[variable]}::" in errors[0]
    assert "no hadolint pin found" in errors[0]
    assert _found(proc.stdout)[env[variable]] == "<not found>"


@pytest.mark.parametrize("missing", ["ci", "makefile", "pre_commit"])
def test_missing_file_fails_and_names_the_file(tmp_path: Path, missing: str) -> None:
    env = _write(tmp_path)
    variable, _ = FILES[missing]
    Path(env[variable]).unlink()
    proc = _run(env)

    assert proc.returncode == 1
    assert f"::error file={env[variable]}::" in proc.stderr
    assert "no such file" in proc.stderr


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("ci", "latest"),
        ("ci", "${{ vars.HADOLINT_VERSION }}"),
        ("pre_commit", "main"),
        ("pre_commit", "v2.15"),
    ],
)
def test_unparseable_pin_fails_closed(tmp_path: Path, key: str, value: str) -> None:
    env = _write(tmp_path, **{key: value})
    proc = _run(env)
    variable, _ = FILES[key]

    assert proc.returncode == 1
    assert f"::error file={env[variable]}::" in proc.stderr
    assert "cannot read a hadolint version from" in proc.stderr


def test_literal_image_tag_in_a_workflow_must_match_its_variable(
    tmp_path: Path,
) -> None:
    env = _write(tmp_path)
    workflow = Path(env["HADOLINT_CI_WORKFLOW"])
    workflow.write_text(
        workflow.read_text(encoding="utf-8")
        + "      - run: docker run --rm -i hadolint/hadolint:v2.14.0 < g\n",
        encoding="utf-8",
    )
    proc = _run(env)

    assert proc.returncode == 1
    assert f"::error file={workflow}::" in proc.stderr
    assert "pins hadolint twice, at 2.15.1 and at 2.14.0" in proc.stderr


def test_commented_out_pins_are_ignored(tmp_path: Path) -> None:
    env = _write(tmp_path)
    for variable, comment in (
        ("HADOLINT_CI_WORKFLOW", "  # was hadolint/hadolint:v2.14.0\n"),
        ("HADOLINT_MAKEFILE", "# docker run hadolint/hadolint:v2.14.0\n"),
        (
            "HADOLINT_PRE_COMMIT_CONFIG",
            "  # - repo: https://github.com/AleksaC/hadolint-py\n  #   rev: v2.12.0.3\n",
        ),
    ):
        path = Path(env[variable])
        path.write_text(path.read_text(encoding="utf-8") + comment, encoding="utf-8")
    proc = _run(env)

    assert proc.returncode == 0, proc.stderr
