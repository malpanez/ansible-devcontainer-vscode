import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check-image-size.py"
REPO_BUDGETS = REPO_ROOT / ".github" / "image-size-budgets.json"
PUBLISHED_IMAGES = {
    "base",
    "ansible",
    "ansible-podman",
    "ansible-aws",
    "terraform",
    "terraform-aws",
    "golang",
    "latex",
}

MIB = 1024 * 1024
NAME = "ansible"
UNCOMPRESSED_MIB = 470
COMPRESSED_MIB = 130
IMAGE = "devcontainer-ansible:ci"
REPOSITORY = "ghcr.io/example/devcontainer-ansible"

# docker info --format '{{json .DriverStatus}}' as GitHub's ubuntu-24.04 runner
# (Docker 28.0.4, overlay2) and a Docker 29 engine on the containerd image
# store answer it.
CLASSIC_STORE = (
    '[["Backing Filesystem","extfs"],["Supports d_type","true"],'
    '["Using metacopy","false"],["Native Overlay Diff","false"],'
    '["userxattr","false"]]\n'
)
CONTAINERD_STORE = '[["driver-type","io.containerd.snapshotter.v1"]]\n'

FAKE_DOCKER = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "${FAKE_DOCKER}/calls.log"
ref="${!#}"
key="${ref//[\\/:@]/_}"
case "$1" in
  info)
    if [[ -f "${FAKE_DOCKER}/info.down" ]]; then
      echo "Cannot connect to the Docker daemon at unix:///var/run/docker.sock" >&2
      exit 1
    fi
    cat "${FAKE_DOCKER}/info.json"
    exit 0
    ;;
  image)
    if [[ -f "${FAKE_DOCKER}/image_${key}" ]]; then
      cat "${FAKE_DOCKER}/image_${key}"
      exit 0
    fi
    echo "Error response from daemon: No such image: ${ref}" >&2
    exit 1
    ;;
  buildx)
    if [[ -f "${FAKE_DOCKER}/${key}.down" ]]; then
      echo "ERROR: ${ref}: dial tcp: i/o timeout" >&2
      exit 1
    fi
    if [[ -f "${FAKE_DOCKER}/${key}.flaky" ]]; then
      rm -f "${FAKE_DOCKER}/${key}.flaky"
      echo "ERROR: ${ref}: dial tcp: i/o timeout" >&2
      exit 1
    fi
    if [[ -f "${FAKE_DOCKER}/${key}" ]]; then
      cat "${FAKE_DOCKER}/${key}"
      exit 0
    fi
    echo "ERROR: ${ref}: not found" >&2
    exit 1
    ;;
esac
echo "unexpected docker call: $*" >&2
exit 64
"""


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_image_size", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_module()


def _key(ref: str) -> str:
    return ref.replace("/", "_").replace(":", "_").replace("@", "_")


def _digest(raw: bytes) -> str:
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _image_manifest(config_size: int, *layer_sizes: int) -> bytes:
    document = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "config": {
            "mediaType": "application/vnd.oci.image.config.v1+json",
            "digest": "sha256:" + "c" * 64,
            "size": config_size,
        },
        "layers": [
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+zstd",
                "digest": "sha256:" + f"{index:x}" * 64,
                "size": size,
            }
            for index, size in enumerate(layer_sizes, start=1)
        ],
    }
    return json.dumps(document, indent=2).encode()


def _index(*platforms: tuple[bytes, str]) -> bytes:
    manifests: list[dict[str, object]] = [
        {
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "digest": _digest(raw),
            "size": len(raw),
            "platform": {"architecture": arch, "os": "linux"},
        }
        for raw, arch in platforms
    ]
    # The provenance attestation buildx lists beside each platform.
    manifests.append(
        {
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "digest": "sha256:" + "e" * 64,
            "size": 1112,
            "annotations": {"vnd.docker.reference.type": "attestation-manifest"},
            "platform": {"architecture": "unknown", "os": "unknown"},
        }
    )
    document = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.index.v1+json",
        "manifests": manifests,
    }
    return json.dumps(document, indent=2).encode()


def _budgets(path: Path, images: object) -> Path:
    path.write_text(
        json.dumps({"_doc": "test budgets", "images": images}, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def budgets(tmp_path: Path) -> Path:
    return _budgets(
        tmp_path / "budgets.json",
        {
            NAME: {
                "max_uncompressed_mib": UNCOMPRESSED_MIB,
                "max_compressed_mib": COMPRESSED_MIB,
                "reason": "test",
            }
        },
    )


@pytest.fixture
def docker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    state = tmp_path / "docker"
    state.mkdir()
    (state / "info.json").write_text(CLASSIC_STORE, encoding="utf-8")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    executable = fake_bin / "docker"
    executable.write_text(FAKE_DOCKER, encoding="utf-8")
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{fake_bin}:{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_DOCKER", str(state))
    monkeypatch.setattr(MODULE, "REGISTRY_RETRY_DELAY_SECONDS", 0.0)
    return state


@pytest.fixture
def summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(path))
    return path


def _local_image(docker: Path, size: int, image: str = IMAGE) -> None:
    (docker / f"image_{_key(image)}").write_text(f"{size}\n", encoding="utf-8")


def _publish(docker: Path, entries: dict[str, bytes]) -> None:
    for ref, raw in entries.items():
        (docker / _key(ref)).write_bytes(raw)


def _calls(docker: Path) -> list[str]:
    log = docker / "calls.log"
    if not log.exists():
        return []
    return log.read_text(encoding="utf-8").splitlines()


def _local(budgets: Path, name: str = NAME, image: str = IMAGE) -> int:
    return MODULE.main(
        ["local", "--image", image, "--name", name, "--budgets", str(budgets)]
    )


def _registry(budgets: Path, ref: str, *extra: str, name: str = NAME) -> int:
    return MODULE.main(
        ["registry", "--ref", ref, "--name", name, "--budgets", str(budgets), *extra]
    )


AMD64 = _image_manifest(2_000, 60 * MIB, 40 * MIB)
ARM64 = _image_manifest(2_000, 70 * MIB, 50 * MIB)
AMD64_SIZE = 2_000 + 100 * MIB
MULTI_ARCH = _index((AMD64, "amd64"), (ARM64, "arm64"))
AMD64_ONLY = _index((AMD64, "amd64"))


def _published_index(docker: Path, index: bytes = MULTI_ARCH) -> str:
    ref = f"{REPOSITORY}@{_digest(index)}"
    _publish(
        docker,
        {
            ref: index,
            f"{REPOSITORY}@{_digest(AMD64)}": AMD64,
            f"{REPOSITORY}@{_digest(ARM64)}": ARM64,
        },
    )
    return ref


@pytest.mark.parametrize(
    "size",
    [UNCOMPRESSED_MIB * MIB - 1, UNCOMPRESSED_MIB * MIB],
    ids=["under", "at"],
)
def test_local_within_budget_passes_and_writes_a_summary_table(
    docker: Path,
    budgets: Path,
    summary: Path,
    size: int,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _local_image(docker, size)

    assert _local(budgets) == 0

    table = summary.read_text(encoding="utf-8")
    assert "| Image | Name | Metric | Size | Budget | Headroom | Verdict |" in table
    assert f"| `{IMAGE}` | `{NAME}` | uncompressed, docker image inspect" in table
    assert "| 470.0 MiB | 470 MiB | 0.0% | within budget |" in table
    assert "::error::" not in capsys.readouterr().err


def test_local_over_budget_fails_with_an_error(
    docker: Path,
    budgets: Path,
    summary: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _local_image(docker, 517 * MIB)

    assert _local(budgets) == 1

    assert "| 517.0 MiB | 470 MiB | -10.0% | over budget |" in summary.read_text(
        encoding="utf-8"
    )
    err = capsys.readouterr().err
    assert f"::error::{IMAGE} is 517.0 MiB uncompressed, 47.0 MiB over" in err
    assert "raise max_uncompressed_mib in a reviewed change" in err


def test_local_headroom_is_the_share_of_the_budget_left(
    docker: Path, budgets: Path, summary: Path
) -> None:
    _local_image(docker, 423 * MIB)

    assert _local(budgets) == 0
    assert "| 423.0 MiB | 470 MiB | 10.0% | within budget |" in summary.read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize(
    ("size", "over"),
    [
        (COMPRESSED_MIB * MIB - 1, False),
        (COMPRESSED_MIB * MIB, False),
        (COMPRESSED_MIB * MIB + 1, True),
    ],
    ids=["under", "at", "over"],
)
def test_registry_never_fails_on_size_and_warns_when_over(
    docker: Path,
    budgets: Path,
    summary: Path,
    size: int,
    over: bool,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = _image_manifest(1_000, size - 1_000)
    ref = f"{REPOSITORY}@{_digest(manifest)}"
    _publish(docker, {ref: manifest})

    assert _registry(budgets, ref) == 0

    err = capsys.readouterr().err
    assert ("::warning::" in err) is over
    assert "::error::" not in err
    verdict = "over budget" if over else "within budget"
    assert f"| {verdict} |" in summary.read_text(encoding="utf-8")


def test_registry_measures_the_amd64_manifest_of_a_multi_arch_index(
    docker: Path,
    budgets: Path,
    summary: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ref = _published_index(docker)

    assert _registry(budgets, ref) == 0

    out = capsys.readouterr().out
    assert f"({AMD64_SIZE} bytes)" in out
    table = summary.read_text(encoding="utf-8")
    assert (
        f"| `{REPOSITORY}@{_digest(AMD64)}` | `{NAME}` | compressed, linux/amd64"
        in (table)
    )
    assert all(_digest(ARM64) not in call for call in _calls(docker))


def test_registry_platform_option_selects_another_manifest(
    docker: Path, budgets: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ref = _published_index(docker)

    assert _registry(budgets, ref, "--platform", "linux/arm64") == 0

    assert f"({2_000 + 120 * MIB} bytes)" in capsys.readouterr().out


def test_registry_single_platform_index_resolves_its_manifest(
    docker: Path, budgets: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ref = _published_index(docker, AMD64_ONLY)

    assert _registry(budgets, ref) == 0

    assert f"({AMD64_SIZE} bytes)" in capsys.readouterr().out


def test_registry_index_without_the_platform_exits_2(
    docker: Path, budgets: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ref = _published_index(docker, AMD64_ONLY)

    assert _registry(budgets, ref, "--platform", "linux/arm64") == 2

    assert "holds no linux/arm64 manifest" in capsys.readouterr().err


def test_registry_single_manifest_ref_is_summed_as_it_is(
    docker: Path, budgets: Path, summary: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ref = f"{REPOSITORY}@{_digest(AMD64)}"
    _publish(docker, {ref: AMD64})

    assert _registry(budgets, ref) == 0

    assert f"({AMD64_SIZE} bytes)" in capsys.readouterr().out
    assert "compressed, single-platform manifest" in summary.read_text(encoding="utf-8")


def test_registry_bytes_that_do_not_hash_to_the_digest_exit_2(
    docker: Path, budgets: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ref = _published_index(docker)
    _publish(docker, {f"{REPOSITORY}@{_digest(AMD64)}": ARM64})

    assert _registry(budgets, ref) == 2

    assert f"the registry served {_digest(ARM64)}" in capsys.readouterr().err


@pytest.mark.parametrize(
    "size", ["1024", -1, True, None], ids=["string", "negative", "bool", "null"]
)
def test_registry_manifest_with_an_unusable_size_exits_2(
    docker: Path, budgets: Path, size: object
) -> None:
    document = json.loads(AMD64)
    document["layers"][0]["size"] = size
    manifest = json.dumps(document).encode()
    ref = f"{REPOSITORY}@{_digest(manifest)}"
    _publish(docker, {ref: manifest})

    assert _registry(budgets, ref) == 2


@pytest.mark.parametrize(
    ("ref", "extra"),
    [
        (f"{REPOSITORY}:v2.0.0", ()),
        (f"{REPOSITORY}@sha256:short", ()),
        (f"{REPOSITORY}@{_digest(AMD64)}", ("--platform", "amd64")),
    ],
    ids=["tag", "short-digest", "platform"],
)
def test_registry_usage_errors_exit_2_before_asking_the_registry(
    docker: Path, budgets: Path, ref: str, extra: tuple[str, ...]
) -> None:
    assert _registry(budgets, ref, *extra) == 2
    assert _calls(docker) == []


def test_registry_that_stays_down_exits_2_after_every_attempt(
    docker: Path, budgets: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ref = _published_index(docker)
    (docker / f"{_key(ref)}.down").touch()

    assert _registry(budgets, ref) == 2

    assert _calls(docker).count(f"buildx imagetools inspect --raw {ref}") == (
        MODULE.REGISTRY_ATTEMPTS
    )
    assert "i/o timeout" in capsys.readouterr().err


def test_registry_transient_failure_is_retried(docker: Path, budgets: Path) -> None:
    ref = _published_index(docker)
    (docker / f"{_key(ref)}.flaky").touch()

    assert _registry(budgets, ref) == 0
    assert _calls(docker).count(f"buildx imagetools inspect --raw {ref}") == 2


def test_registry_missing_reference_is_not_retried(docker: Path, budgets: Path) -> None:
    ref = f"{REPOSITORY}@{_digest(AMD64)}"

    assert _registry(budgets, ref) == 2
    assert _calls(docker) == [f"buildx imagetools inspect --raw {ref}"]


@pytest.mark.parametrize("mode", ["local", "registry"])
def test_unknown_name_exits_2_without_asking_docker(
    docker: Path, budgets: Path, mode: str, capsys: pytest.CaptureFixture[str]
) -> None:
    if mode == "local":
        code = _local(budgets, name="ansible-gcp")
    else:
        code = _registry(budgets, f"{REPOSITORY}@{_digest(AMD64)}", name="ansible-gcp")

    assert code == 2
    assert "has no budget for 'ansible-gcp'" in capsys.readouterr().err
    assert _calls(docker) == []


def _entry(**overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "max_uncompressed_mib": UNCOMPRESSED_MIB,
        "max_compressed_mib": COMPRESSED_MIB,
        "reason": "test",
    }
    entry.update(overrides)
    return entry


@pytest.mark.parametrize(
    "content",
    [
        "{not json",
        "[]",
        json.dumps({"_doc": "no images"}),
        json.dumps({"images": {}}),
        json.dumps({"images": {NAME: [470, 130]}}),
        json.dumps({"images": {NAME: _entry(max_uncompressed_mib=0)}}),
        json.dumps({"images": {NAME: _entry(max_compressed_mib=-5)}}),
        json.dumps({"images": {NAME: _entry(max_compressed_mib=130.5)}}),
        json.dumps({"images": {NAME: _entry(max_uncompressed_mib="470")}}),
        json.dumps({"images": {NAME: _entry(max_uncompressed_mib=True)}}),
        json.dumps({"images": {NAME: _entry(reason=" ")}}),
        json.dumps({"images": {NAME: _entry(max_uncompresed_mib=470)}}),
        json.dumps(
            {
                "images": {
                    NAME: _entry(),
                    "golang": {"max_uncompressed_mib": 410, "reason": "no compressed"},
                }
            }
        ),
    ],
    ids=[
        "not-json",
        "not-an-object",
        "no-images",
        "empty-images",
        "entry-not-an-object",
        "zero",
        "negative",
        "float",
        "string",
        "bool",
        "blank-reason",
        "misspelt-key",
        "another-entry-broken",
    ],
)
@pytest.mark.parametrize("mode", ["local", "registry"])
def test_ill_formed_budgets_file_exits_2(
    docker: Path,
    tmp_path: Path,
    content: str,
    mode: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "budgets.json"
    path.write_text(content, encoding="utf-8")
    _local_image(docker, 1)

    if mode == "local":
        code = _local(path)
    else:
        code = _registry(path, f"{REPOSITORY}@{_digest(AMD64)}")

    assert code == 2
    err = capsys.readouterr().err
    assert "::error::check-image-size:" in err
    assert str(path) in err
    assert _calls(docker) == []


def test_unreadable_budgets_file_exits_2(
    docker: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _local(tmp_path / "missing.json") == 2
    assert "cannot read the budgets file" in capsys.readouterr().err


def test_image_docker_does_not_have_exits_2(
    docker: Path, budgets: Path, summary: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _local(budgets) == 2

    assert "No such image" in capsys.readouterr().err
    assert not summary.exists()


def test_size_that_is_not_a_byte_count_exits_2(
    docker: Path, budgets: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (docker / f"image_{_key(IMAGE)}").write_text("<no value>\n", encoding="utf-8")

    assert _local(budgets) == 2
    assert "not a byte count" in capsys.readouterr().err


def test_docker_daemon_that_does_not_answer_exits_2(
    docker: Path, budgets: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _local_image(docker, 1)
    (docker / "info.down").touch()

    assert _local(budgets) == 2
    assert "docker info failed" in capsys.readouterr().err


def test_docker_missing_from_path_exits_2(
    tmp_path: Path,
    budgets: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))

    assert _local(budgets) == 2
    assert "cannot run docker" in capsys.readouterr().err


def test_containerd_image_store_exits_2_before_measuring(
    docker: Path, budgets: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (docker / "info.json").write_text(CONTAINERD_STORE, encoding="utf-8")
    _local_image(docker, 1)

    assert _local(budgets) == 2

    assert "containerd image store" in capsys.readouterr().err
    assert all(not call.startswith("image ") for call in _calls(docker))


def test_no_summary_is_written_when_github_step_summary_is_unset(
    docker: Path,
    budgets: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    _local_image(docker, MIB)

    assert _local(budgets) == 0
    assert "within budget" in capsys.readouterr().out
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "bin",
        "budgets.json",
        "docker",
    ]


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.pop("GITHUB_STEP_SUMMARY", None)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_command_line_exit_codes(docker: Path, budgets: Path) -> None:
    _local_image(docker, (UNCOMPRESSED_MIB + 1) * MIB)
    local = ("local", "--image", IMAGE, "--budgets", str(budgets))

    over = _cli(*local, "--name", NAME)
    unknown = _cli(*local, "--name", "ansible-gcp")
    usage = _cli("local", "--name", NAME)

    assert (over.returncode, unknown.returncode, usage.returncode) == (1, 2, 2)
    assert "::error::" in over.stderr


def test_repository_budgets_file_covers_exactly_the_published_images() -> None:
    document = json.loads(REPO_BUDGETS.read_text(encoding="utf-8"))
    budgets = MODULE.load_budgets(REPO_BUDGETS)

    assert isinstance(document.get("_doc"), str) and document["_doc"].strip()
    assert set(document["images"]) == PUBLISHED_IMAGES
    assert set(budgets) == PUBLISHED_IMAGES
    for name, budget in budgets.items():
        for value in (budget.max_uncompressed_mib, budget.max_compressed_mib):
            assert isinstance(value, int) and not isinstance(value, bool), name
            assert value > 0, name
        assert budget.max_compressed_mib < budget.max_uncompressed_mib, name
        assert budget.reason.strip(), name
