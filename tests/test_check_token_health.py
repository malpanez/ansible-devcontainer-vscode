import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
FAKE_TOKEN = "not-a-real-token-0123456789"
NOW = 1_791_200_000
DAY = 86_400


def _expiry(days: float, fmt: str = "%Y-%m-%d %H:%M:%S UTC") -> str:
    moment = datetime.fromtimestamp(NOW + int(days * DAY), tz=timezone.utc)
    return moment.strftime(fmt)


def _headers(*lines: str, eol: str = "\n") -> str:
    return eol.join(("HTTP/2 200", *lines, "", ""))


def _run(
    tmp_path: Path,
    *,
    status: int = 200,
    headers: str = "",
    token: str | None = FAKE_TOKEN,
    warn_days: str | None = None,
) -> subprocess.CompletedProcess:
    headers_file = tmp_path / "headers.txt"
    headers_file.write_bytes(headers.encode("utf-8"))

    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"BOT_TOKEN", "WARN_DAYS"}
    }
    if token is not None:
        env["BOT_TOKEN"] = token
    if warn_days is not None:
        env["WARN_DAYS"] = warn_days

    proc = subprocess.run(
        [
            "bash",
            "scripts/check-token-health.sh",
            "--headers",
            str(headers_file),
            "--status",
            str(status),
            "--now",
            str(NOW),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if token:
        assert token not in proc.stdout
        assert token not in proc.stderr
    return proc


def _annotations(proc: subprocess.CompletedProcess) -> list[str]:
    return proc.stdout.splitlines()


@pytest.mark.parametrize("token", [None, ""])
def test_missing_secret_is_an_error(tmp_path: Path, token: str | None):
    proc = _run(tmp_path, token=token, headers=_headers())
    assert proc.returncode == 1
    assert len(_annotations(proc)) == 1
    assert proc.stdout.startswith("::error::BOT_TOKEN is empty")


def test_token_with_embedded_newline_is_an_error(tmp_path: Path):
    proc = _run(tmp_path, token=f"{FAKE_TOKEN}\nX-Injected: 1", headers=_headers())
    assert proc.returncode == 1
    assert proc.stdout.startswith("::error::BOT_TOKEN contains whitespace")
    assert FAKE_TOKEN not in proc.stdout
    assert FAKE_TOKEN not in proc.stderr


def test_rejected_token_points_at_the_runbook(tmp_path: Path):
    proc = _run(tmp_path, status=401, headers="HTTP/2 401\n\n")
    assert proc.returncode == 1
    assert len(_annotations(proc)) == 1
    assert proc.stdout.startswith(
        "::error::BOT_TOKEN was rejected by GitHub (HTTP 401)"
    )
    assert "docs/MAINTENANCE.md" in proc.stdout


def test_unexpected_status_is_an_error(tmp_path: Path):
    proc = _run(tmp_path, status=500, headers="HTTP/2 500\n\n")
    assert proc.returncode == 1
    assert len(_annotations(proc)) == 1
    assert proc.stdout.startswith("::error::Unexpected HTTP 500")


@pytest.mark.parametrize(
    ("granted", "missing"),
    [
        ("repo", "workflow"),
        ("workflow", "repo"),
        ("public_repo, repo:status, workflow", "repo"),
        ("", "repo workflow"),
    ],
)
def test_missing_scope_is_named(tmp_path: Path, granted: str, missing: str):
    proc = _run(
        tmp_path,
        headers=_headers(
            f"x-oauth-scopes: {granted}",
            f"github-authentication-token-expiration: {_expiry(60)}",
        ),
    )
    assert proc.returncode == 1
    assert proc.stdout.startswith(
        f"::error::BOT_TOKEN is missing required scope(s): {missing}."
    )


def test_expiring_in_three_days_is_an_error(tmp_path: Path):
    proc = _run(
        tmp_path,
        headers=_headers(
            "x-oauth-scopes: repo, workflow",
            f"github-authentication-token-expiration: {_expiry(3)}",
        ),
    )
    assert proc.returncode == 1
    assert len(_annotations(proc)) == 1
    assert proc.stdout.startswith("::error::BOT_TOKEN expires in 3 days (on ")
    assert _expiry(3, "%Y-%m-%d %H:%M UTC") in proc.stdout


def test_expiring_in_sixty_days_is_a_notice(tmp_path: Path):
    proc = _run(
        tmp_path,
        headers=_headers(
            "x-oauth-scopes: repo, workflow",
            f"github-authentication-token-expiration: {_expiry(60)}",
        ),
    )
    assert proc.returncode == 0, proc.stdout
    assert len(_annotations(proc)) == 1
    assert proc.stdout.startswith("::notice::BOT_TOKEN is accepted and expires on ")
    assert _expiry(60, "%Y-%m-%d %H:%M UTC") in proc.stdout
    assert "(60 days left)" in proc.stdout


@pytest.mark.parametrize(
    ("days", "returncode", "prefix"),
    [
        (14.5, 1, "::error::BOT_TOKEN expires in 14 days"),
        (15.5, 0, "::notice::BOT_TOKEN is accepted"),
    ],
)
def test_warn_days_boundary_is_inclusive(
    tmp_path: Path, days: float, returncode: int, prefix: str
):
    proc = _run(
        tmp_path,
        headers=_headers(f"github-authentication-token-expiration: {_expiry(days)}"),
    )
    assert proc.returncode == returncode, proc.stdout
    assert proc.stdout.startswith(prefix)


def test_warn_days_can_be_overridden(tmp_path: Path):
    proc = _run(
        tmp_path,
        warn_days="90",
        headers=_headers(f"github-authentication-token-expiration: {_expiry(60)}"),
    )
    assert proc.returncode == 1
    assert proc.stdout.startswith("::error::BOT_TOKEN expires in 60 days")


def test_no_expiry_header_is_a_notice(tmp_path: Path):
    proc = _run(tmp_path, headers=_headers("x-oauth-scopes: repo, workflow"))
    assert proc.returncode == 0, proc.stdout
    assert len(_annotations(proc)) == 1
    assert proc.stdout.startswith("::notice::BOT_TOKEN is accepted and has no expiry")


def test_token_without_scopes_header_skips_the_scope_check(tmp_path: Path):
    proc = _run(
        tmp_path,
        headers=_headers(f"github-authentication-token-expiration: {_expiry(60)}"),
    )
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.startswith("::notice::")


def test_expiry_with_utc_offset_is_parsed(tmp_path: Path):
    offset_expiry = _expiry(3 + 2 / 24, "%Y-%m-%d %H:%M:%S +0200")
    proc = _run(
        tmp_path,
        headers=_headers(f"github-authentication-token-expiration: {offset_expiry}"),
    )
    assert proc.returncode == 1
    assert proc.stdout.startswith("::error::BOT_TOKEN expires in 3 days (on ")
    assert _expiry(3, "%Y-%m-%d %H:%M UTC") in proc.stdout


def test_unparseable_expiry_is_an_error(tmp_path: Path):
    proc = _run(
        tmp_path,
        headers=_headers("github-authentication-token-expiration: not a date"),
    )
    assert proc.returncode == 1
    assert proc.stdout.startswith(
        "::error::BOT_TOKEN expiry header could not be parsed"
    )


@pytest.mark.parametrize(
    ("days", "returncode", "prefix"),
    [
        (3, 1, "::error::BOT_TOKEN expires in 3 days"),
        (60, 0, "::notice::BOT_TOKEN is accepted and expires on "),
    ],
)
def test_crlf_and_mixed_case_headers(
    tmp_path: Path, days: int, returncode: int, prefix: str
):
    proc = _run(
        tmp_path,
        headers=_headers(
            "X-OAuth-Scopes: repo, workflow",
            f"GitHub-Authentication-Token-Expiration: {_expiry(days)}",
            eol="\r\n",
        ),
    )
    assert proc.returncode == returncode, proc.stdout
    assert len(_annotations(proc)) == 1
    assert proc.stdout.startswith(prefix)
    assert "\r" not in proc.stdout


def test_crlf_and_mixed_case_scopes_are_checked(tmp_path: Path):
    proc = _run(
        tmp_path,
        headers=_headers("X-OAuth-Scopes: repo", eol="\r\n"),
    )
    assert proc.returncode == 1
    assert proc.stdout.startswith(
        "::error::BOT_TOKEN is missing required scope(s): workflow."
    )


def test_last_header_occurrence_wins(tmp_path: Path):
    two_responses = "HTTP/2 502\nx-oauth-scopes: \n\n" + _headers(
        "x-oauth-scopes: repo, workflow"
    )
    proc = _run(tmp_path, headers=two_responses)
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.startswith("::notice::")


def test_headers_and_status_must_come_together(tmp_path: Path):
    headers_file = tmp_path / "headers.txt"
    headers_file.write_text(_headers(), encoding="utf-8")
    proc = subprocess.run(
        ["bash", "scripts/check-token-health.sh", "--headers", str(headers_file)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "BOT_TOKEN": FAKE_TOKEN},
    )
    assert proc.returncode == 2
    assert "--headers and --status must be given together." in proc.stderr
    assert FAKE_TOKEN not in proc.stdout
    assert FAKE_TOKEN not in proc.stderr
