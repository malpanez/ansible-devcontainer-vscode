import json


def _load_json(host, path):
    data = host.file(path)
    assert data.exists, f"Expected {path} to exist"
    return json.loads(data.content_string)


def test_latex_devcontainer_build_config(host):
    payload = _load_json(host, "/workspace/.devcontainer/devcontainer.json")
    build = payload.get("build", {})
    assert build.get("dockerfile") == "Dockerfile"
    assert build.get("context") == "../.."


def test_template_metadata_records_stack(host):
    metadata = _load_json(host, "/workspace/.devcontainer/.template-metadata.json")
    assert metadata.get("stack") == "latex"
    assert metadata.get("source", "").endswith("/devcontainers/latex")
    assert metadata.get("signature")
