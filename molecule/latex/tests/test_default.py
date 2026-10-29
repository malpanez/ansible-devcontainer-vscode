import json
import re


def _load_json(host, path):
    data = host.file(path)
    assert data.exists, f"Expected {path} to exist"
    return json.loads(data.content_string)


def test_latex_devcontainer_opens_published_image(host):
    payload = _load_json(host, "/workspace/.devcontainer/devcontainer.json")
    assert "build" not in payload
    assert re.fullmatch(
        r"ghcr\.io/[^/]+/devcontainer-latex:v[0-9]+\.[0-9]+\.[0-9]+@sha256:[0-9a-f]{64}",
        payload.get("image", ""),
    )


def test_latex_devcontainer_build_variant_config(host):
    payload = _load_json(host, "/workspace/.devcontainer/local-build/devcontainer.json")
    build = payload.get("build", {})
    assert build.get("dockerfile") == "../Dockerfile"
    assert build.get("context") == "${localWorkspaceFolder}"


def test_template_metadata_records_stack(host):
    metadata = _load_json(host, "/workspace/.devcontainer/.template-metadata.json")
    assert metadata.get("stack") == "latex"
    assert metadata.get("source", "").endswith("/devcontainers/latex")
    assert metadata.get("signature")
