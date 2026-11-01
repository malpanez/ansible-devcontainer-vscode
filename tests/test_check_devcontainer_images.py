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
SCRIPT = REPO_ROOT / "scripts" / "check-devcontainer-images.py"

REPOSITORY = "ghcr.io/example/devcontainer-terraform"
TAG = "v1.4.0"
AMD64 = "sha256:" + "a" * 64
ARM64 = "sha256:" + "b" * 64
ATTESTATION = "sha256:" + "c" * 64

FAKE_DOCKER = """#!/usr/bin/env bash
ref="${!#}"
printf '%s\\n' "${ref}" >> "${FAKE_REGISTRY}/calls.log"
key="${ref//[\\/:@]/_}"
if [[ -f "${FAKE_REGISTRY}/${key}.down" ]]; then
  echo "ERROR: ${ref}: dial tcp: i/o timeout" >&2
  exit 1
fi
if [[ -f "${FAKE_REGISTRY}/${key}.flaky" ]]; then
  rm -f "${FAKE_REGISTRY}/${key}.flaky"
  echo "ERROR: ${ref}: dial tcp: i/o timeout" >&2
  exit 1
fi
if [[ -f "${FAKE_REGISTRY}/${key}.flaky_not_found" ]]; then
  rm -f "${FAKE_REGISTRY}/${key}.flaky_not_found"
  echo "ERROR: ${ref}: not found" >&2
  exit 1
fi
if [[ -f "${FAKE_REGISTRY}/${key}" ]]; then
  cat "${FAKE_REGISTRY}/${key}"
  exit 0
fi
echo "ERROR: ${ref}: not found" >&2
exit 1
"""


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_devcontainer_images", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_module()


def _manifest(digest: str, os_name: str, arch: str) -> dict[str, object]:
    return {
        "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "digest": digest,
        "size": 1234,
        "platform": {"architecture": arch, "os": os_name},
    }


def _index(*platforms: tuple[str, str, str]) -> bytes:
    manifests = [_manifest(*platform) for platform in platforms]
    manifests.append(_manifest(ATTESTATION, "unknown", "unknown"))
    document = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.index.v1+json",
        "manifests": manifests,
    }
    return json.dumps(document, indent=2).encode()


MULTI_ARCH = _index((AMD64, "linux", "amd64"), (ARM64, "linux", "arm64"))
AMD64_ONLY = _index((AMD64, "linux", "amd64"))
PLATFORM_MANIFEST = json.dumps(
    {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "config": {"digest": "sha256:" + "d" * 64},
        "layers": [],
    }
).encode()


def _digest(raw: bytes) -> str:
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _config(image: str | None, **extra: object) -> dict[str, object]:
    config: dict[str, object] = {"name": "Terraform Dev Container"}
    if image is not None:
        config["image"] = image
    config.update(
        {
            "mounts": ["source=uv-cache,target=/home/vscode/.cache/uv,type=volume"],
            "postCreateCommand": ["/bin/bash", "-lc", "ensure-precommit"],
        }
    )
    config.update(extra)
    return config


def _build_config(**extra: object) -> dict[str, object]:
    config = _config(None)
    config["name"] = "Terraform Dev Container (local build)"
    config["build"] = {
        "dockerfile": "../Dockerfile",
        "context": "${localWorkspaceFolder}",
    }
    config.update(extra)
    return config


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _tree(tmp_path: Path, image: str) -> Path:
    root = tmp_path / "repo"
    for stack_dir in (root / "devcontainers" / "terraform", root / ".devcontainer"):
        _write(stack_dir / "devcontainer.json", _config(image))
        _write(stack_dir / "local-build" / "devcontainer.json", _build_config())
        (stack_dir / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    _write(
        root / "examples" / "terraform-project" / ".devcontainer" / "devcontainer.json",
        _config(image),
    )
    return root


def _registry(tmp_path: Path, entries: dict[str, bytes]) -> Path:
    registry = tmp_path / "registry"
    registry.mkdir(exist_ok=True)
    for ref, raw in entries.items():
        key = ref.replace("/", "_").replace(":", "_").replace("@", "_")
        (registry / key).write_bytes(raw)
    return registry


def _fake_docker(tmp_path: Path) -> Path:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(exist_ok=True)
    docker = fake_bin / "docker"
    docker.write_text(FAKE_DOCKER, encoding="utf-8")
    docker.chmod(docker.stat().st_mode | stat.S_IXUSR)
    return fake_bin


def _run(
    tmp_path: Path, root: Path, *args: str, registry: Path | None = None
) -> subprocess.CompletedProcess[str]:
    fake_bin = _fake_docker(tmp_path)
    env = {key: value for key, value in os.environ.items() if key != "FAKE_REGISTRY"}
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["FAKE_REGISTRY"] = str(registry or _registry(tmp_path, {}))
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _published(index: bytes, tag_index: bytes | None = None) -> dict[str, bytes]:
    return {
        f"{REPOSITORY}@{_digest(index)}": index,
        f"{REPOSITORY}@{AMD64}": PLATFORM_MANIFEST,
        f"{REPOSITORY}@{ARM64}": PLATFORM_MANIFEST,
        f"{REPOSITORY}:{TAG}": tag_index if tag_index is not None else index,
    }


def test_load_jsonc_strips_comments_and_trailing_commas_outside_strings() -> None:
    text = """{
      // line comment
      "url": "https://example.com/a,]",  /* block */
      "quote": "say \\"hi\\" // not a comment",
      "list": ["a", "b",],
    }"""

    assert MODULE.load_jsonc(text) == {
        "url": "https://example.com/a,]",
        "quote": 'say "hi" // not a comment',
        "list": ["a", "b"],
    }


def test_load_jsonc_unterminated_block_comment_raises() -> None:
    with pytest.raises(ValueError, match="unterminated block comment"):
        MODULE.load_jsonc('{"a": 1 /* open')


@pytest.mark.parametrize(
    "value",
    [
        f"{REPOSITORY}:{TAG}",
        f"{REPOSITORY}@{AMD64}",
        f"devcontainer-terraform:{TAG}@{AMD64}",
        f"{REPOSITORY}:{TAG}@sha256:short",
        None,
        42,
    ],
)
def test_parse_image_rejects_refs_without_registry_tag_and_digest(
    value: object,
) -> None:
    assert MODULE.parse_image(value) is None


def test_parse_image_splits_repository_tag_and_digest() -> None:
    image = MODULE.parse_image(f"{REPOSITORY}:{TAG}@{AMD64}")

    assert image == MODULE.PinnedImage(REPOSITORY, TAG, AMD64)
    assert image.ref == f"{REPOSITORY}:{TAG}@{AMD64}"


def test_repository_templates_and_examples_pass_offline(tmp_path: Path) -> None:
    proc = _run(tmp_path, REPO_ROOT, "--offline")

    assert proc.returncode == 0, proc.stderr
    assert "All dev container images check out (files)." in proc.stdout


def test_offline_valid_tree_passes_without_asking_the_registry(
    tmp_path: Path,
) -> None:
    root = _tree(tmp_path, f"{REPOSITORY}:{TAG}@{_digest(MULTI_ARCH)}")
    registry = _registry(tmp_path, {})

    proc = _run(tmp_path, root, "--offline", registry=registry)

    assert proc.returncode == 0, proc.stderr
    assert not (registry / "calls.log").exists()


def test_multi_arch_pin_that_resolves_passes(tmp_path: Path) -> None:
    root = _tree(tmp_path, f"{REPOSITORY}:{TAG}@{_digest(MULTI_ARCH)}")
    registry = _registry(tmp_path, _published(MULTI_ARCH))

    proc = _run(tmp_path, root, registry=registry)

    assert proc.returncode == 0, proc.stderr
    assert "[linux/amd64, linux/arm64]" in proc.stdout
    calls = (registry / "calls.log").read_text(encoding="utf-8").splitlines()
    assert sorted(calls) == sorted(_published(MULTI_ARCH))


def test_unpinned_image_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path, f"{REPOSITORY}:{TAG}")

    proc = _run(tmp_path, root, "--offline")

    assert proc.returncode == 1
    assert "devcontainers/terraform/devcontainer.json" in proc.stderr
    assert "<registry>/<repository>:<tag>@sha256:<digest>" in proc.stderr


@pytest.mark.parametrize(
    "tag", ["latest", "main", "sha-1234567", "py314-v1.4.0", "v1.4", "1.4.0"]
)
def test_pin_on_a_tag_other_than_a_release_version_fails(
    tmp_path: Path, tag: str
) -> None:
    root = _tree(tmp_path, f"{REPOSITORY}:{tag}@{_digest(MULTI_ARCH)}")

    proc = _run(tmp_path, root, "--offline")

    assert proc.returncode == 1
    assert (
        f'devcontainers/terraform/devcontainer.json: pins the tag "{tag}", not a'
        " release version tag v<major>.<minor>.<patch>" in proc.stderr
    )
    assert "cleanup-ghcr.yml deletes the digest" in proc.stderr


def test_pin_on_a_rolling_tag_is_not_sent_to_the_registry(tmp_path: Path) -> None:
    root = _tree(tmp_path, f"{REPOSITORY}:latest@{_digest(MULTI_ARCH)}")
    registry = _registry(tmp_path, _published(MULTI_ARCH))

    proc = _run(tmp_path, root, registry=registry)

    assert proc.returncode == 1
    assert 'pins the tag "latest"' in proc.stderr
    assert not (registry / "calls.log").exists()


def test_template_that_still_builds_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path, f"{REPOSITORY}:{TAG}@{_digest(MULTI_ARCH)}")
    _write(
        root / "devcontainers" / "terraform" / "devcontainer.json",
        _config(None, build={"dockerfile": "Dockerfile", "context": "../.."}),
    )

    proc = _run(tmp_path, root, "--offline")

    assert proc.returncode == 1
    assert 'still builds locally ("build")' in proc.stderr
    assert '"image" is null' in proc.stderr


def test_build_variant_with_relative_context_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path, f"{REPOSITORY}:{TAG}@{_digest(MULTI_ARCH)}")
    _write(
        root / ".devcontainer" / "local-build" / "devcontainer.json",
        _build_config(build={"dockerfile": "../Dockerfile", "context": "../.."}),
    )

    proc = _run(tmp_path, root, "--offline")

    assert proc.returncode == 1
    assert (
        '.devcontainer/local-build/devcontainer.json: build.context is "../.."'
        in proc.stderr
    )


def test_build_variant_drifting_from_image_variant_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path, f"{REPOSITORY}:{TAG}@{_digest(MULTI_ARCH)}")
    _write(
        root / "devcontainers" / "terraform" / "local-build" / "devcontainer.json",
        _build_config(postCreateCommand="true"),
    )

    proc = _run(tmp_path, root, "--offline")

    assert proc.returncode == 1
    assert (
        "differs from ../devcontainer.json in more than name/image/build" in proc.stderr
    )


def test_build_variant_with_image_or_missing_dockerfile_fails(tmp_path: Path) -> None:
    image = f"{REPOSITORY}:{TAG}@{_digest(MULTI_ARCH)}"
    root = _tree(tmp_path, image)
    _write(
        root / "devcontainers" / "terraform" / "local-build" / "devcontainer.json",
        _build_config(image=image),
    )
    (root / "devcontainers" / "terraform" / "Dockerfile").unlink()

    proc = _run(tmp_path, root, "--offline")

    assert proc.returncode == 1
    assert 'the build variant must not set "image"' in proc.stderr
    assert (
        'build.dockerfile "../Dockerfile" is not a file relative to it' in proc.stderr
    )


def test_template_directory_without_build_variant_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path, f"{REPOSITORY}:{TAG}@{_digest(MULTI_ARCH)}")
    (
        root / "devcontainers" / "terraform" / "local-build" / "devcontainer.json"
    ).unlink()

    proc = _run(tmp_path, root, "--offline")

    assert proc.returncode == 1
    assert (
        "devcontainers/terraform: has no local-build/devcontainer.json" in proc.stderr
    )


def test_build_variant_without_image_variant_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path, f"{REPOSITORY}:{TAG}@{_digest(MULTI_ARCH)}")
    (root / ".devcontainer" / "devcontainer.json").unlink()

    proc = _run(tmp_path, root, "--offline")

    assert proc.returncode == 1
    assert "has no ../devcontainer.json to build the same container as" in proc.stderr


def test_other_template_variant_that_still_builds_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path, f"{REPOSITORY}:{TAG}@{_digest(MULTI_ARCH)}")
    _write(
        root / "devcontainers" / "terraform" / "devcontainer.docker-socket.json",
        _config(None, build={"dockerfile": "Dockerfile", "context": "../.."}),
    )

    proc = _run(tmp_path, root, "--offline")

    assert proc.returncode == 1
    assert "devcontainer.docker-socket.json: still builds locally" in proc.stderr


def test_examples_need_no_build_variant(tmp_path: Path) -> None:
    root = _tree(tmp_path, f"{REPOSITORY}:{TAG}@{_digest(MULTI_ARCH)}")

    proc = _run(tmp_path, root, "--offline")

    assert proc.returncode == 0, proc.stderr
    assert "examples" not in proc.stderr


def test_unparsable_file_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path, f"{REPOSITORY}:{TAG}@{_digest(MULTI_ARCH)}")
    path = (
        root / "examples" / "terraform-project" / ".devcontainer" / "devcontainer.json"
    )
    path.write_text('{"image": ', encoding="utf-8")

    proc = _run(tmp_path, root, "--offline")

    assert proc.returncode == 1
    assert "devcontainer.json: cannot be parsed" in proc.stderr


def test_digest_that_does_not_resolve_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path, f"{REPOSITORY}:{TAG}@{_digest(MULTI_ARCH)}")

    proc = _run(tmp_path, root)

    assert proc.returncode == 1
    assert "the pinned digest does not resolve" in proc.stderr
    assert "not found" in proc.stderr


def test_single_platform_manifest_pin_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path, f"{REPOSITORY}:{TAG}@{_digest(PLATFORM_MANIFEST)}")
    registry = _registry(
        tmp_path,
        {
            f"{REPOSITORY}@{_digest(PLATFORM_MANIFEST)}": PLATFORM_MANIFEST,
            f"{REPOSITORY}:{TAG}": MULTI_ARCH,
        },
    )

    proc = _run(tmp_path, root, registry=registry)

    assert proc.returncode == 1
    assert "is a single-platform manifest" in proc.stderr
    assert "not a multi-arch index" in proc.stderr


def test_pin_that_its_version_tag_resolves_to_passes(tmp_path: Path) -> None:
    root = _tree(tmp_path, f"{REPOSITORY}:{TAG}@{_digest(AMD64_ONLY)}")
    registry = _registry(tmp_path, _published(AMD64_ONLY))

    proc = _run(tmp_path, root, registry=registry)

    assert proc.returncode == 0, proc.stderr
    assert f"ok {REPOSITORY}:{TAG}@{_digest(AMD64_ONLY)} [linux/amd64]" in proc.stdout


def test_version_tag_that_resolves_to_another_digest_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path, f"{REPOSITORY}:{TAG}@{_digest(AMD64_ONLY)}")
    registry = _registry(tmp_path, _published(AMD64_ONLY, tag_index=MULTI_ARCH))

    proc = _run(tmp_path, root, registry=registry)

    assert proc.returncode == 1
    assert (
        f"{REPOSITORY}:{TAG} resolves to {_digest(MULTI_ARCH)}, not the pinned digest"
        in proc.stderr
    )
    assert "the pin is wrong or the tag was moved" in proc.stderr


def test_unresolvable_digest_reports_what_its_tag_resolves_to(tmp_path: Path) -> None:
    pinned = "sha256:" + "e" * 64
    root = _tree(tmp_path, f"{REPOSITORY}:{TAG}@{pinned}")
    registry = _registry(tmp_path, _published(MULTI_ARCH))

    proc = _run(tmp_path, root, registry=registry)

    assert proc.returncode == 1
    assert "the pinned digest does not resolve" in proc.stderr
    assert f"resolves to {_digest(MULTI_ARCH)}, not the pinned digest" in proc.stderr


def test_platform_manifest_that_does_not_resolve_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path, f"{REPOSITORY}:{TAG}@{_digest(MULTI_ARCH)}")
    entries = _published(MULTI_ARCH)
    del entries[f"{REPOSITORY}@{ARM64}"]
    registry = _registry(tmp_path, entries)

    proc = _run(tmp_path, root, registry=registry)

    assert proc.returncode == 1
    assert f"the linux/arm64 manifest {ARM64} does not resolve" in proc.stderr


def test_registry_serving_other_bytes_for_the_digest_fails(tmp_path: Path) -> None:
    pinned = "sha256:" + "e" * 64
    root = _tree(tmp_path, f"{REPOSITORY}:{TAG}@{pinned}")
    entries = _published(MULTI_ARCH)
    entries[f"{REPOSITORY}@{pinned}"] = MULTI_ARCH
    registry = _registry(tmp_path, entries)

    proc = _run(tmp_path, root, registry=registry)

    assert proc.returncode == 1
    assert f"the registry served {_digest(MULTI_ARCH)} for this digest" in proc.stderr


def test_tag_that_does_not_resolve_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path, f"{REPOSITORY}:{TAG}@{_digest(MULTI_ARCH)}")
    entries = _published(MULTI_ARCH)
    del entries[f"{REPOSITORY}:{TAG}"]
    registry = _registry(tmp_path, entries)

    proc = _run(tmp_path, root, registry=registry)

    assert proc.returncode == 1
    assert f"the tag {TAG} does not resolve" in proc.stderr


def test_root_without_devcontainers_exits_2(tmp_path: Path) -> None:
    proc = _run(tmp_path, tmp_path, "--offline")

    assert proc.returncode == 2
    assert "has no devcontainers/ directory" in proc.stderr


def _registry_on_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entries: dict[str, bytes]
) -> Path:
    registry = _registry(tmp_path, entries)
    monkeypatch.setenv("PATH", f"{_fake_docker(tmp_path)}:{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_REGISTRY", str(registry))
    monkeypatch.setattr(MODULE, "REGISTRY_RETRY_DELAY_SECONDS", 0.0)
    monkeypatch.setattr(MODULE, "NOT_FOUND_RETRY_DELAY_SECONDS", 0.0)
    return registry


def _calls(registry: Path) -> list[str]:
    return (registry / "calls.log").read_text(encoding="utf-8").splitlines()


def test_transient_registry_failure_is_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = f"{REPOSITORY}:{TAG}"
    registry = _registry_on_path(tmp_path, monkeypatch, {ref: MULTI_ARCH})
    (registry / f"{ref.replace('/', '_').replace(':', '_')}.flaky").touch()

    assert MODULE.inspect_raw(ref) == MULTI_ARCH
    assert _calls(registry) == [ref, ref]


def test_not_found_that_the_next_request_does_not_repeat_is_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = f"{REPOSITORY}:{TAG}"
    registry = _registry_on_path(tmp_path, monkeypatch, {ref: MULTI_ARCH})
    (registry / f"{ref.replace('/', '_').replace(':', '_')}.flaky_not_found").touch()

    assert MODULE.inspect_raw(ref) == MULTI_ARCH
    assert _calls(registry) == [ref, ref]


def test_missing_reference_still_fails_after_a_bounded_number_of_attempts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = f"{REPOSITORY}:{TAG}"
    registry = _registry_on_path(tmp_path, monkeypatch, {})

    with pytest.raises(MODULE.RegistryError, match="not found"):
        MODULE.inspect_raw(ref)
    assert _calls(registry) == [ref] * MODULE.NOT_FOUND_ATTEMPTS


def test_registry_that_stays_down_fails_after_every_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = f"{REPOSITORY}:{TAG}"
    registry = _registry_on_path(tmp_path, monkeypatch, {ref: MULTI_ARCH})
    (registry / f"{ref.replace('/', '_').replace(':', '_')}.down").touch()

    with pytest.raises(MODULE.RegistryError, match="i/o timeout"):
        MODULE.inspect_raw(ref)
    assert _calls(registry) == [ref] * MODULE.REGISTRY_ATTEMPTS
