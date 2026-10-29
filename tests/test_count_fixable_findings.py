import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "count-fixable-findings.sh"

IMAGE = "devcontainer-base"
BOTH = "linux/amd64,linux/arm64"
INHERITED = (
    "GITHUB_OUTPUT",
    "GITHUB_STEP_SUMMARY",
    "IMAGE",
    "PLATFORMS",
    "SARIF_AMD64",
    "SARIF_ARM64",
)


def _sarif(tmp_path: Path, name: str, *results: tuple[str, str]) -> str:
    path = tmp_path / f"{name}.sarif"
    document = {
        "version": "2.1.0",
        "runs": [
            {
                "tool": {"driver": {"name": "Grype"}},
                "results": [
                    {"ruleId": rule_id, "level": level, "message": {"text": rule_id}}
                    for rule_id, level in results
                ],
            }
        ],
    }
    path.write_text(json.dumps(document), encoding="utf-8")
    return str(path)


def _run(
    tmp_path: Path, github: bool = True, **env: str
) -> subprocess.CompletedProcess[str]:
    base = {key: value for key, value in os.environ.items() if key not in INHERITED}
    if github:
        base["GITHUB_OUTPUT"] = str(tmp_path / "output")
        base["GITHUB_STEP_SUMMARY"] = str(tmp_path / "summary")
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=tmp_path,
        env={**base, "IMAGE": IMAGE, **env},
        capture_output=True,
        text=True,
        check=False,
    )


def _output(tmp_path: Path) -> list[str]:
    path = tmp_path / "output"
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def _summary(tmp_path: Path) -> str:
    path = tmp_path / "summary"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _warnings(stdout: str) -> list[str]:
    return [line for line in stdout.splitlines() if line.startswith("::warning::")]


def test_count_fixable_findings_both_platforms_clean_writes_zero(
    tmp_path: Path,
) -> None:
    proc = _run(
        tmp_path,
        PLATFORMS=BOTH,
        SARIF_AMD64=_sarif(tmp_path, "amd64"),
        SARIF_ARM64=_sarif(tmp_path, "arm64"),
    )

    assert proc.returncode == 0, proc.stderr
    assert _output(tmp_path) == ["count=0"]
    assert _summary(tmp_path) == ""
    assert _warnings(proc.stdout) == []
    assert f"{IMAGE} (linux/amd64): 0" in proc.stdout
    assert f"{IMAGE} (linux/arm64): 0" in proc.stdout


def test_count_fixable_findings_arm64_only_findings_counts_and_lists_them(
    tmp_path: Path,
) -> None:
    proc = _run(
        tmp_path,
        PLATFORMS=BOTH,
        SARIF_AMD64=_sarif(tmp_path, "amd64"),
        SARIF_ARM64=_sarif(
            tmp_path,
            "arm64",
            ("CVE-2026-0001", "error"),
            ("CVE-2026-0001", "error"),
            ("GHSA-aaaa-bbbb-cccc", "error"),
        ),
    )

    assert proc.returncode == 0, proc.stderr
    assert _output(tmp_path) == ["count=3"]
    summary = _summary(tmp_path)
    assert summary.splitlines()[0] == (
        f"### {IMAGE}: 3 fixable high/critical finding(s), not tagged"
    )
    assert "**linux/arm64** (3)" in summary
    assert "linux/amd64" not in summary
    assert summary.count("- CVE-2026-0001\n") == 1
    assert "- GHSA-aaaa-bbbb-cccc\n" in summary
    assert f"{IMAGE} (linux/amd64): 0" in proc.stdout
    assert f"{IMAGE} (linux/arm64): 3" in proc.stdout


def test_count_fixable_findings_findings_on_both_platforms_are_summed(
    tmp_path: Path,
) -> None:
    proc = _run(
        tmp_path,
        PLATFORMS=BOTH,
        SARIF_AMD64=_sarif(tmp_path, "amd64", ("CVE-2026-0002", "error")),
        SARIF_ARM64=_sarif(tmp_path, "arm64", ("CVE-2026-0003", "error")),
    )

    assert proc.returncode == 0, proc.stderr
    assert _output(tmp_path) == ["count=2"]
    summary = _summary(tmp_path)
    assert "**linux/amd64** (1)\n\n- CVE-2026-0002\n" in summary
    assert "**linux/arm64** (1)\n\n- CVE-2026-0003\n" in summary


def test_count_fixable_findings_warning_level_results_are_not_counted(
    tmp_path: Path,
) -> None:
    proc = _run(
        tmp_path,
        PLATFORMS=BOTH,
        SARIF_AMD64=_sarif(
            tmp_path,
            "amd64",
            ("CVE-2026-0004", "warning"),
            ("CVE-2026-0005", "note"),
        ),
        SARIF_ARM64=_sarif(tmp_path, "arm64", ("CVE-2026-0006", "warning")),
    )

    assert proc.returncode == 0, proc.stderr
    assert _output(tmp_path) == ["count=0"]
    assert _summary(tmp_path) == ""


def test_count_fixable_findings_arm64_sarif_path_empty_leaves_count_empty(
    tmp_path: Path,
) -> None:
    proc = _run(
        tmp_path,
        PLATFORMS=BOTH,
        SARIF_AMD64=_sarif(tmp_path, "amd64"),
        SARIF_ARM64="",
    )

    assert proc.returncode == 0, proc.stderr
    assert _output(tmp_path) == ["count="]
    warnings = _warnings(proc.stdout)
    assert len(warnings) == 1
    assert "linux/arm64" in warnings[0]
    assert "no SARIF path" in warnings[0]


def test_count_fixable_findings_arm64_sarif_missing_leaves_count_empty(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "gone.sarif"
    proc = _run(
        tmp_path,
        PLATFORMS=BOTH,
        SARIF_AMD64=_sarif(tmp_path, "amd64"),
        SARIF_ARM64=str(missing),
    )

    assert proc.returncode == 0, proc.stderr
    assert _output(tmp_path) == ["count="]
    warnings = _warnings(proc.stdout)
    assert len(warnings) == 1
    assert "linux/arm64" in warnings[0]
    assert f"{missing} does not exist" in warnings[0]


@pytest.mark.parametrize(
    "contents",
    ["", "not json", '{"runs": [', "{}", '{"runs": []}', '{"runs": [{}]}'],
    ids=["empty", "text", "truncated", "no-runs-key", "no-runs", "no-results"],
)
def test_count_fixable_findings_unreadable_sarif_leaves_count_empty(
    tmp_path: Path, contents: str
) -> None:
    broken = tmp_path / "broken.sarif"
    broken.write_text(contents, encoding="utf-8")
    proc = _run(
        tmp_path,
        PLATFORMS=BOTH,
        SARIF_AMD64=str(broken),
        SARIF_ARM64=_sarif(tmp_path, "arm64"),
    )

    assert proc.returncode == 0, proc.stderr
    assert _output(tmp_path) == ["count="]
    warnings = _warnings(proc.stdout)
    assert len(warnings) == 1
    assert "linux/amd64" in warnings[0]
    assert "not a readable Grype report" in warnings[0]


def test_count_fixable_findings_unjudged_platform_still_lists_judged_findings(
    tmp_path: Path,
) -> None:
    proc = _run(
        tmp_path,
        PLATFORMS=BOTH,
        SARIF_AMD64=_sarif(tmp_path, "amd64", ("CVE-2026-0007", "error")),
        SARIF_ARM64="",
    )

    assert proc.returncode == 0, proc.stderr
    assert _output(tmp_path) == ["count="]
    summary = _summary(tmp_path)
    assert "- CVE-2026-0007\n" in summary
    assert "Not judged: linux/arm64" in summary


@pytest.mark.parametrize("arm64", ["unset", "empty", "stale"])
def test_count_fixable_findings_amd64_only_platforms_ignore_arm64_sarif(
    tmp_path: Path, arm64: str
) -> None:
    env = {"PLATFORMS": "linux/amd64", "SARIF_AMD64": _sarif(tmp_path, "amd64")}
    if arm64 == "empty":
        env["SARIF_ARM64"] = ""
    elif arm64 == "stale":
        env["SARIF_ARM64"] = _sarif(tmp_path, "arm64", ("CVE-2026-0008", "error"))
    proc = _run(tmp_path, **env)

    assert proc.returncode == 0, proc.stderr
    assert _output(tmp_path) == ["count=0"]
    assert _warnings(proc.stdout) == []
    assert "linux/arm64" not in proc.stdout


def test_count_fixable_findings_spaced_and_repeated_platforms_are_judged_once(
    tmp_path: Path,
) -> None:
    proc = _run(
        tmp_path,
        PLATFORMS=" linux/amd64 , linux/arm64,linux/amd64",
        SARIF_AMD64=_sarif(tmp_path, "amd64", ("CVE-2026-0009", "error")),
        SARIF_ARM64=_sarif(tmp_path, "arm64"),
    )

    assert proc.returncode == 0, proc.stderr
    assert _output(tmp_path) == ["count=1"]
    assert proc.stdout.count(f"{IMAGE} (linux/amd64):") == 1


def test_count_fixable_findings_outside_github_prints_count(tmp_path: Path) -> None:
    proc = _run(
        tmp_path,
        github=False,
        PLATFORMS=BOTH,
        SARIF_AMD64=_sarif(tmp_path, "amd64"),
        SARIF_ARM64=_sarif(tmp_path, "arm64", ("CVE-2026-0010", "error")),
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines()[-1] == "count=1"
    assert f"### {IMAGE}: 1 fixable high/critical finding(s), not tagged" in (
        proc.stdout
    )


@pytest.mark.parametrize(
    "platforms",
    ["linux/s390x", "linux/amd64,linux/arm/v7", "linux/arm64/v8", "amd64"],
)
def test_count_fixable_findings_unknown_platform_exits_non_zero(
    tmp_path: Path, platforms: str
) -> None:
    proc = _run(
        tmp_path,
        PLATFORMS=platforms,
        SARIF_AMD64=_sarif(tmp_path, "amd64"),
        SARIF_ARM64=_sarif(tmp_path, "arm64"),
    )

    assert proc.returncode != 0
    assert "unsupported platform" in proc.stderr
    assert _output(tmp_path) == []


@pytest.mark.parametrize("platforms", ["", " ", ","])
def test_count_fixable_findings_empty_platforms_exits_non_zero(
    tmp_path: Path, platforms: str
) -> None:
    proc = _run(
        tmp_path,
        PLATFORMS=platforms,
        SARIF_AMD64=_sarif(tmp_path, "amd64"),
        SARIF_ARM64=_sarif(tmp_path, "arm64"),
    )

    assert proc.returncode != 0
    assert "PLATFORMS is empty" in proc.stderr
    assert _output(tmp_path) == []


def test_count_fixable_findings_empty_image_exits_non_zero(tmp_path: Path) -> None:
    proc = _run(
        tmp_path,
        IMAGE="",
        PLATFORMS=BOTH,
        SARIF_AMD64=_sarif(tmp_path, "amd64"),
        SARIF_ARM64=_sarif(tmp_path, "arm64"),
    )

    assert proc.returncode != 0
    assert "IMAGE is empty" in proc.stderr
    assert _output(tmp_path) == []
