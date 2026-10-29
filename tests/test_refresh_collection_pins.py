import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "refresh-collection-pins.py"

OLD = "a" * 64
NEW = "b" * 64
HEADER = "# pinned collections\n# name version sha256\n\n"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("refresh_collection_pins", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_module()


def _write_list(root: Path, body: str, name: str = "collections.txt") -> Path:
    folder = root / "devcontainers" / "ansible"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(body)
    return path


def test_sync_hashes_rewrites_only_the_stale_hash(tmp_path: Path) -> None:
    path = _write_list(
        tmp_path,
        HEADER + f"ansible.posix 2.2.3 {OLD}\ncommunity.general 13.5.0 {NEW}\n",
    )
    calls: list[tuple[str, str]] = []

    def fetch(name: str, version: str) -> str:
        calls.append((name, version))
        return NEW

    assert MODULE.sync_hashes(tmp_path, fetch) == 0

    assert (
        path.read_text()
        == HEADER + f"ansible.posix 2.2.3 {NEW}\ncommunity.general 13.5.0 {NEW}\n"
    )
    assert calls == [("ansible.posix", "2.2.3"), ("community.general", "13.5.0")]


def test_sync_hashes_is_a_no_op_when_current(tmp_path: Path) -> None:
    body = HEADER + f"kubernetes.core 6.6.0 {NEW}\n"
    path = _write_list(tmp_path, body)
    before = path.stat().st_mtime_ns

    MODULE.sync_hashes(tmp_path, lambda _name, _version: NEW)

    assert path.read_text() == body
    assert path.stat().st_mtime_ns == before


def test_sync_hashes_covers_every_list(tmp_path: Path) -> None:
    main = _write_list(tmp_path, f"ansible.posix 2.2.2 {OLD}\n")
    extra = _write_list(tmp_path, f"amazon.aws 11.4.0 {OLD}\n", "collections-aws.txt")

    MODULE.sync_hashes(tmp_path, lambda _name, _version: NEW)

    assert main.read_text() == f"ansible.posix 2.2.2 {NEW}\n"
    assert extra.read_text() == f"amazon.aws 11.4.0 {NEW}\n"


def test_sync_hashes_rejects_a_malformed_line(tmp_path: Path) -> None:
    _write_list(tmp_path, "ansible.posix 2.2.2\n")

    with pytest.raises(RuntimeError, match="not '<namespace.name> <version> <sha256>'"):
        MODULE.sync_hashes(tmp_path, lambda _name, _version: NEW)


def test_sync_hashes_fails_without_lists(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="no collection lists"):
        MODULE.sync_hashes(tmp_path, lambda _name, _version: NEW)


def test_galaxy_sha256_rejects_an_artifact_galaxy_did_not_publish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detail = (
        b'{"artifact": {"sha256": "'
        + OLD.encode()
        + b'"}, "download_url": "https://example.invalid/a.tar.gz"}'
    )
    responses = {
        f"{MODULE.GALAXY_API}/index/ansible/posix/versions/2.2.2/": detail,
        "https://example.invalid/a.tar.gz": b"not the published artifact",
    }
    monkeypatch.setattr(MODULE, "http_get", lambda url: responses[url])

    with pytest.raises(RuntimeError, match="Galaxy publishes"):
        MODULE.galaxy_sha256("ansible.posix", "2.2.2")
