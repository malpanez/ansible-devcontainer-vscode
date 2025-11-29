# Ansible DevContainer

A production-ready Ansible development container with hardened defaults, multiple runtime profiles, and integrated tooling.

## Features

- **Python 3.12** with `uv` package manager for fast, reproducible installs
- **Ansible** with ansible-lint, molecule, and testing tools pre-installed
- **Pre-commit hooks** automatically configured
- **VS Code extensions** for Ansible, Python, YAML, and Docker
- **Hardened security defaults** (opt-in for insecure modes)
- **Multiple runtime profiles** (docker-socket, dind, insecure)

## Quick Start

### Default Profile (docker-socket)

The default configuration uses your host's Docker daemon via socket mounting:

```bash
# 1. Open this repository in VS Code
# 2. Run: "Dev Containers: Reopen in Container"
# 3. Select: devcontainers/ansible/devcontainer.json
```

This is the **recommended** profile for most use cases.

## Runtime Profiles

### 1. docker-socket (Default) ✅ Recommended

**File:** `devcontainer.json`

**When to use:**
- Standard development
- You have Docker Desktop or Docker Engine running on the host
- You want to share the host's Docker daemon

**Characteristics:**
- Mounts `/var/run/docker.sock` from host
- No Docker-in-Docker overhead
- Fast and lightweight
- Shared Docker images/containers with host

**Select in VS Code:**
```json
// .devcontainer/devcontainer.json
{
  "extends": "../devcontainers/ansible/devcontainer.json"
}
```

---

### 2. dind (Docker-in-Docker)

**File:** `devcontainer.dind.json`

**When to use:**
- Running in environments without Docker socket access (CI, remote hosts)
- You need complete isolation from host Docker
- Testing Docker-related Ansible modules in isolation

**Characteristics:**
- Uses `ghcr.io/devcontainers/features/docker-in-docker:2`
- Runs `--privileged` (required for dind)
- Independent Docker daemon inside container
- No Docker socket mount

**Select in VS Code:**
```json
// .devcontainer/devcontainer.json
{
  "extends": "../devcontainers/ansible/devcontainer.dind.json"
}
```

---

### 3. insecure (Labs/Testing Only) ⚠️

**File:** `devcontainer.insecure.json`

**When to use:**
- Lab environments only
- Testing against hosts with unknown SSH keys
- Environments where DNS override is needed

**Characteristics:**
- Sets `ANSIBLE_HOST_KEY_CHECKING=false` ⚠️
- Uses custom DNS (`1.1.1.1`, `1.0.0.1`) ⚠️
- **NOT for production use**

**Select in VS Code:**
```json
// .devcontainer/devcontainer.json
{
  "extends": "../devcontainers/ansible/devcontainer.insecure.json"
}
```

> **⚠️ Security Warning:** The insecure profile disables SSH host key checking and overrides DNS.
> Only use in isolated lab/testing environments. Never use against production systems.

## What Gets Installed

### System Packages
- `git` (via apt, not feature - simpler and faster)
- `openssh-client`, `rsync` (for Ansible connectivity)
- `curl`, `ca-certificates`, `unzip` (for downloads)
- Build tools: `build-essential`, `libffi-dev`, `libssl-dev`, etc.

### Python Packages (via uv)
- `ansible` + `ansible-core`
- `ansible-lint`
- `molecule` + `molecule-plugins[docker]`
- `ansible-navigator`
- Testing: `pytest`, `pytest-ansible`, `pytest-testinfra`
- See `requirements-ansible.txt` for full list

### VS Code Extensions
- `redhat.ansible` - Ansible language support
- `redhat.vscode-yaml` - YAML support
- `ms-python.python` + `ms-python.vscode-pylance` - Python
- `charliermarsh.ruff` - Python linting/formatting
- `ms-azuretools.vscode-docker` - Docker support
- And more...

## Configuration

### Ansible Settings

The devcontainer configures Ansible extension with optimal defaults:

```json
{
  "ansible.ansible.path": "/usr/local/bin/ansible",
  "ansible.ansible.useFullyQualifiedCollectionNames": true,
  "ansible.python.interpreterPath": "/usr/local/bin/python",
  "ansible.validation.lint.path": "/usr/local/bin/ansible-lint"
}
```

### Environment Variables

All profiles set:
- `ANSIBLE_FORCE_COLOR=true` - Colored output
- `UV_CACHE_DIR=/home/vscode/.cache/uv` - uv package cache
- `ANSIBLE_GALAXY_CACHE_DIR=/home/vscode/.ansible/galaxy_cache` - Collection cache
- `PRE_COMMIT_HOME=/workspace/.cache/pre-commit` - Pre-commit cache
- `ANSIBLE_LOCAL_TEMP=/workspace/.cache/ansible/tmp` - Ansible temp directory

**Only insecure profile adds:**
- `ANSIBLE_HOST_KEY_CHECKING=false` ⚠️

### Post-Create Command

On container creation, the following runs automatically:

```bash
mkdir -p /workspace/.cache/pre-commit /workspace/.cache/ansible/tmp && \
ensure-precommit && \
(test -f requirements.yml && ansible-galaxy collection install -r requirements.yml || \
 echo 'No requirements.yml found, skipping collection install')
```

This is **idempotent** and safe to run multiple times.

## Hardened Security Defaults

### Sudoers Configuration

The `vscode` user can only run these commands with `sudo` without password:

```
/usr/bin/uv
/usr/bin/uvx
/usr/local/bin/ansible-galaxy
```

**Not allowed:** `apt-get`, `pip`, other system commands

**Rationale:** Forces all package installations to happen during container build, not at runtime. This makes the environment reproducible and auditable.

### SSH Host Key Checking

**Default profiles** (docker-socket, dind):
- `ANSIBLE_HOST_KEY_CHECKING` is **NOT set**
- Ansible will use its default behavior (strict host key checking)

**Insecure profile only:**
- `ANSIBLE_HOST_KEY_CHECKING=false` ⚠️
- Use only in lab environments

### DNS Configuration

**Default profiles:**
- Use system DNS (respects VPN/corporate networks)

**Insecure profile only:**
- Forces `--dns=1.1.1.1` and `--dns=1.0.0.1` ⚠️
- May break VPN/corporate network access

## Reproducibility

### Pinned UV Version

The Dockerfile uses a pinned version of `uv`:

```dockerfile
ARG UV_VERSION="0.5.11"
RUN curl -fsSL https://astral.sh/uv/${UV_VERSION}/install.sh | sh
```

### Base Image Pinning (Optional)

You can pin the base image to a specific digest for full reproducibility:

```dockerfile
# In devcontainers/ansible/Dockerfile
ARG BASE_IMAGE=python:3.12-slim-bookworm@sha256:...
```

To get the current digest:
```bash
docker pull python:3.12-slim-bookworm
docker inspect python:3.12-slim-bookworm | jq -r '.[0].RepoDigests[0]'
```

### Locked Dependencies

All Python dependencies are locked with hashes in `requirements-ansible.txt`:

```txt
ansible==9.13.0 \
    --hash=sha256:b389a97d1e85c2b2ad6ace9e94f410111f69cc5aa3845c930c873b34c0ddd6e2
```

## Project Structure

```
devcontainers/ansible/
├── Dockerfile                    # Multi-arch Ansible image
├── devcontainer.json             # Default profile (docker-socket)
├── devcontainer.dind.json        # Docker-in-Docker profile
├── devcontainer.insecure.json    # Insecure lab profile
└── README.md                     # This file
```

## Troubleshooting

### Ansible Galaxy Collections Fail to Install

**Symptom:** `postCreateCommand` fails with "requirements.yml not found"

**Solution:** This is expected if your repository doesn't have Ansible collections. The command is designed to be idempotent and will skip collection installation gracefully.

### Docker Command Not Found (dind profile)

**Symptom:** Docker commands fail in dind profile

**Solution:** Wait for the container to fully start. The Docker-in-Docker feature takes a few seconds to initialize the Docker daemon.

### SSH Host Key Verification Failed

**Symptom:** Ansible fails with "Host key verification failed"

**Solutions:**
1. **Recommended:** Add the target host to `~/.ssh/known_hosts` manually first
2. **For labs only:** Use the `devcontainer.insecure.json` profile

### VPN/Corporate Network Issues

**Symptom:** Cannot resolve internal hostnames or access internal resources

**Solution:** Use the default profile (docker-socket or dind), NOT the insecure profile. The default profiles respect system DNS and VPN settings.

## Advanced Usage

### Using with .devcontainer Directory

Create a `.devcontainer/devcontainer.json` in your repository root:

```json
{
  "name": "My Ansible Project",
  "dockerComposeFile": "../devcontainers/ansible/devcontainer.json"
}
```

Or extend with custom settings:

```json
{
  "extends": "../devcontainers/ansible/devcontainer.json",
  "customizations": {
    "vscode": {
      "settings": {
        "ansible.validation.lint.arguments": "--profile production"
      }
    }
  }
}
```

### Adding Custom Environment Variables

```json
{
  "extends": "../devcontainers/ansible/devcontainer.dind.json",
  "remoteEnv": {
    "ANSIBLE_INVENTORY": "${containerWorkspaceFolder}/inventory/hosts.yml",
    "ANSIBLE_VAULT_PASSWORD_FILE": "${containerWorkspaceFolder}/.vault-pass"
  }
}
```

## Migration Guide

### From Old Configuration

If migrating from the previous configuration:

**Old (mixed dind + socket):**
```json
{
  "features": {
    "ghcr.io/devcontainers/features/docker-in-docker:2": {},
    "ghcr.io/devcontainers/features/git:1": {}
  },
  "mounts": [
    "source=/var/run/docker.sock,target=/var/run/docker.sock,type=bind"
  ],
  "runArgs": ["--init", "--dns=1.1.1.1"],
  "remoteEnv": {
    "ANSIBLE_HOST_KEY_CHECKING": "false"
  }
}
```

**New (choose one):**

For most users (docker-socket):
```json
{
  "extends": "../devcontainers/ansible/devcontainer.json"
}
```

For isolated Docker (dind):
```json
{
  "extends": "../devcontainers/ansible/devcontainer.dind.json"
}
```

For lab environments (insecure):
```json
{
  "extends": "../devcontainers/ansible/devcontainer.insecure.json"
}
```

## Contributing

When making changes to this devcontainer:

1. **Test all profiles** - Ensure docker-socket, dind, and insecure all work
2. **Update this README** - Document any new features or changes
3. **Keep dependencies locked** - Regenerate `requirements-ansible.txt` with `uv export`
4. **Maintain security defaults** - Don't weaken the hardened configuration without good reason

## License

MIT - See repository LICENSE file
