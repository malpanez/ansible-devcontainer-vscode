import json
import pytest


def test_uv_installed(host):
    result = host.run("uv --version")
    assert result.rc == 0


def test_ansible_installed(host):
    result = host.run("ansible --version")
    assert result.rc == 0


@pytest.mark.parametrize("binary", ["ansible-lint", "yamllint"])
def test_linting_tools_available(host, binary):
    result = host.run(f"{binary} --version")
    assert result.rc == 0


def test_devcontainer_user_exists(host):
    user = host.user("vscode")
    assert user.exists


def test_devcontainer_template_applied(host):
    devcontainer_json = host.file("/workspace/.devcontainer/devcontainer.json")
    assert devcontainer_json.exists
    assert devcontainer_json.contains('"name": "Ansible DevOps Environment"')


def test_template_metadata_records_stack(host):
    metadata = host.file("/workspace/.devcontainer/.template-metadata.json")
    assert metadata.exists
    payload = json.loads(metadata.content_string)
    assert payload.get("stack") == "ansible"
    assert payload.get("signature")


def test_template_idempotency(host):
    status_file = host.file("/workspace/.devcontainer/.template-idempotent.json")
    assert status_file.exists
    payload = json.loads(status_file.content_string)
    assert payload["checksum_before"] == payload["checksum_after"]
    assert payload["mtime_before"] <= payload["mtime_after"]
