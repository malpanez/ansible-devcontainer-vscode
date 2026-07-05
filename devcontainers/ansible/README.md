# Ansible DevContainer

A production-ready Ansible development container with hardened defaults, multiple runtime profiles, and integrated tooling.

## Features

- **Python 3.12** with `uv` package manager for fast, reproducible installs
- **Ansible** with ansible-lint, molecule, and testing tools pre-installed
- **Pre-commit hooks** automatically configured
- **VS Code extensions** for Ansible, Python, YAML, and Docker
- **Hardened security defaults** (no sudo rules, docker socket only by opt-in)
- **Multiple runtime profiles** (default, docker-socket, dind, podman)
- **Podman + Execution Environments** support for modern Ansible workflows

## Quick Start

### Default Profile

The default configuration has no access to the host Docker daemon:

```bash
# 1. Open this repository in VS Code
# 2. Run: "Dev Containers: Reopen in Container"
# 3. Select: devcontainers/ansible/devcontainer.json
```

This is the **recommended** profile for most use cases. Pick the
docker-socket or dind profile only when you need to run containers
(e.g. molecule with the docker driver) from inside the devcontainer.

## Runtime Profiles

### 1. default ✅ Recommended

**File:** `devcontainer.json`

**When to use:**
- Standard development (playbooks, roles, linting, unit tests)
- You do not need to launch containers from inside the devcontainer

**Characteristics:**
- No Docker socket access — the container cannot control the host
- Fast and lightweight

**Select in VS Code:**
```json
// .devcontainer/devcontainer.json
{
  "extends": "../devcontainers/ansible/devcontainer.json"
}
```

---

### 1b. docker-socket ⚠️ Host-equivalent access

**File:** `devcontainer.docker-socket.json`

**When to use:**
- Running molecule with the docker driver inside the devcontainer
- You explicitly want to share the host's Docker daemon

**Characteristics:**
- Mounts `/var/run/docker.sock` from host
- **Grants root-equivalent control of the host Docker daemon** — treat
  it as trusted-workload-only
- No Docker-in-Docker overhead; shares images/containers with the host

**Select in VS Code:**
```json
// .devcontainer/devcontainer.json
{
  "extends": "../devcontainers/ansible/devcontainer.docker-socket.json"
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

### 3. podman (Podman + Execution Environments) 🚀 **Best for AAP/Collections**

**File:** `devcontainer.podman.json`

**When to use:**
- Creating Ansible collections, roles, or playbooks for Ansible Automation Platform (AAP)
- Testing with Execution Environments (the modern Ansible standard)
- Want Podman instead of Docker (e.g., security policies, rootless preference)
- Developing content that will run in containerized Ansible (ansible-navigator)

**Characteristics:**
- Uses **Podman** for container runtime (rootless by default)
- Includes **ansible-navigator** for running playbooks in Execution Environments
- Includes **ansible-builder** for creating custom Execution Environments
- Pre-configured with `creator-ee` (official minimal EE for content creators)
- No Docker socket dependency
- Rootless container execution (more secure)

**Select in VS Code:**
```json
// .devcontainer/devcontainer.json
{
  "extends": "../devcontainers/ansible/devcontainer.podman.json"
}
```

**Quick Start:**
```bash
# Run a playbook in an Execution Environment
ansible-navigator run playbook.yml --ee true --ce podman --mode stdout

# Build a custom Execution Environment
ansible-builder build -f execution-environment.yml -t my-ee:latest --container-runtime podman

# List Podman images
podman images

# Use VS Code tasks (Ctrl+Shift+P → "Tasks: Run Task")
```

**Why Podman + EE?**
- ✅ **AAP-compatible**: Matches Ansible Automation Platform's execution model
- ✅ **Isolated dependencies**: Each playbook can use different Python/collection versions
- ✅ **Reproducible**: EE images lock all dependencies
- ✅ **Portable**: Same EE runs in dev, CI, and production
- ✅ **Rootless**: More secure than traditional Docker
- ✅ **Future-proof**: This is the direction Ansible is heading

> **💡 Tip:** If you're creating collections or roles for AAP, start with the Podman profile.
> It ensures your content works the same way in AAP as in your dev environment.

---

## What Gets Installed

### System Packages
- `git`, `gh` (via apt, not features - simpler and faster)
- `openssh-client`, `rsync` (for Ansible connectivity)
- `curl`, `ca-certificates`, `unzip` (for downloads)
- `jq`, `yamllint`, `vim-tiny` (from the shared devcontainer-base)
- No compiler toolchain: Python packages install from wheels, and the
  one source build (onigurumacffi on arm64) happens in a builder stage

### Python Packages (via uv)
The image ships the runtime toolchain: `ansible` + `ansible-core`,
`ansible-lint`, `ansible-navigator`, `yamllint`, `pre-commit` (see
`requirements-ansible.txt` for the full pinned list).

Development/test tooling (molecule, pytest family, black/ruff/mypy,
ipython) lives in the `dev` dependency group — run `uv sync` in a
workspace with a pyproject to get it, or `uv sync --group aws` for
boto3/botocore.

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

### No sudo rules

The `vscode` user has **no passwordless sudo grants** — every package is
installed at image build time. To add tooling, extend the Dockerfile and
rebuild; for ad-hoc Python packages use user-scoped installs
(`uv tool install <pkg>` or a virtualenv), which need no root.

### SSH Host Key Checking

`ANSIBLE_HOST_KEY_CHECKING` is **not set** in any profile — Ansible uses
strict host key checking by default. For throwaway lab hosts, export
`ANSIBLE_HOST_KEY_CHECKING=false` in that shell session only.

### DNS Configuration

All profiles use system DNS (respects VPN/corporate networks). If you
need custom DNS, add `--dns` entries to `runArgs` in your local
`.devcontainer/devcontainer.json`.

## Reproducibility

### Pinned UV Version

The Dockerfile installs a pinned `uv` release as a direct binary
download (no pipe-to-shell) and verifies its published SHA-256 checksum:

```dockerfile
ARG UV_VERSION="0.9.13"
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
├── Dockerfile                     # Multi-arch Ansible image
├── Dockerfile.podman              # Podman + Execution Environments image
├── devcontainer.json              # Default profile (no docker socket)
├── devcontainer.docker-socket.json # Host Docker daemon profile (opt-in)
├── devcontainer.dind.json         # Docker-in-Docker profile
├── devcontainer.podman.json       # Podman profile
└── README.md                      # This file
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
2. **For throwaway lab hosts only:** export `ANSIBLE_HOST_KEY_CHECKING=false` in that shell session

### VPN/Corporate Network Issues

**Symptom:** Cannot resolve internal hostnames or access internal resources

**Solution:** All profiles respect system DNS and VPN settings; if you need custom DNS, add `--dns` entries to `runArgs` in your local `.devcontainer/devcontainer.json`.

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

For the host Docker daemon (docker-socket):
```json
{
  "extends": "../devcontainers/ansible/devcontainer.docker-socket.json"
}
```

For isolated Docker (dind):
```json
{
  "extends": "../devcontainers/ansible/devcontainer.dind.json"
}
```

For Podman + Execution Environments (AAP):
```json
{
  "extends": "../devcontainers/ansible/devcontainer.podman.json"
}
```

---

## Podman + Execution Environments Guide

### What are Execution Environments?

Execution Environments (EEs) are containerized Ansible runtimes that include:
- Ansible Core
- Ansible Collections
- Python dependencies
- System packages

They ensure consistent execution across development, CI, and production (AAP).

### Creating Your First EE

1. **Use the template** (already in your workspace after first container start):
```yaml
# execution-environment.yml
---
version: 3
images:
  base_image:
    name: quay.io/ansible/creator-ee:v0.18.0

dependencies:
  galaxy: requirements.yml
  # python: requirements.txt  # Uncomment if needed
```

2. **Build the EE**:
```bash
ansible-builder build -f execution-environment.yml -t my-custom-ee:latest --container-runtime podman
```

3. **Run a playbook with the EE**:
```bash
ansible-navigator run playbook.yml --ee true --ce podman --eei my-custom-ee:latest
```

### Using VS Code Tasks (Podman Profile)

The Podman profile includes pre-configured tasks:

1. **Press** `Ctrl+Shift+P` (or `Cmd+Shift+P` on macOS)
2. **Type**: `Tasks: Run Task`
3. **Choose**:
   - `Ansible: Lint Current File` - Lint the open playbook/role
   - `Ansible: Run Playbook with EE` - Execute in Execution Environment
   - `Ansible: Build Custom Execution Environment` - Build your EE
   - `Podman: List Images` - See available images
   - `Podman: Info` - Check Podman configuration

### Troubleshooting Podman

#### Issue: `podman info` fails with "permission denied"

**Cause:** cgroups v2 not available or user namespaces not configured

**Solution 1:** Check cgroups version
```bash
# Inside devcontainer
if [ -f /sys/fs/cgroup/cgroup.controllers ]; then
  echo "cgroups v2 ✓"
else
  echo "cgroups v1 - Podman may have issues"
fi
```

**Solution 2:** Enable `--privileged` mode (temporary workaround)

Edit `devcontainer.podman.json`:
```json
{
  "runArgs": [
    "--init",
    "--userns=keep-id",
    "--cgroupns=host",
    "--privileged"  // Add this line
  ]
}
```

> **Note:** `--privileged` is a workaround for hosts with limited rootless support.
> Most modern systems (Docker Desktop, Linux 5.x+) don't need it.

---

#### Issue: Storage driver errors (overlay vs fuse-overlayfs)

**Symptom:**
```
Error: 'overlay' is not supported over overlayfs
```

**Cause:** The devcontainer is running on an overlay filesystem

**Solution:** Storage is pre-configured to use `fuse-overlayfs`. If issues persist:

1. Check storage configuration:
```bash
cat ~/.config/containers/storage.conf
```

2. Should contain:
```ini
[storage]
driver = "overlay"

[storage.options.overlay]
mount_program = "/usr/bin/fuse-overlayfs"
```

3. If not, recreate the container (storage.conf is set during build)

---

#### Issue: "Cannot connect to Podman socket"

**Symptom:**
```
Error: unable to connect to Podman socket
```

**Cause:** Podman is configured for rootless but socket isn't started

**Solution:** The Podman profile uses rootless mode (no socket needed). If a tool requires a socket:

```bash
# Start Podman system service (inside devcontainer)
podman system service --time=0 unix:///tmp/podman.sock &
export DOCKER_HOST=unix:///tmp/podman.sock
```

---

#### Issue: EE image pull is slow or fails

**Symptom:**
```
Error pulling image: timeout
```

**Solutions:**

1. **Pre-pull manually**:
```bash
podman pull quay.io/ansible/creator-ee:v0.18.0
```

2. **Use a mirror** (if behind corporate proxy):

Edit `~/.config/containers/registries.conf`:
```toml
[[registry]]
location = "quay.io"
[[registry.mirror]]
location = "your-mirror.company.com"
```

3. **Check network**:
```bash
podman run --rm quay.io/podman/hello:latest
```

---

#### Issue: ansible-navigator can't find Podman

**Symptom:**
```
Error: container engine 'podman' not found
```

**Solution:** Verify environment variables:
```bash
echo $ANSIBLE_NAVIGATOR_CONTAINER_ENGINE  # Should be "podman"
echo $CONTAINER_ENGINE  # Should be "podman"

# If not set:
export ANSIBLE_NAVIGATOR_CONTAINER_ENGINE=podman
```

These are pre-configured in `devcontainer.podman.json` but can be overridden.

---

### Best Practices for EE Development

1. **Lock your dependencies**:
```yaml
# requirements.yml
collections:
  - name: community.general
    version: "9.5.0"  # Pin to specific version
```

2. **Test locally before building EE**:
```bash
# Install collections locally first
ansible-galaxy collection install -r requirements.yml

# Test playbook
ansible-playbook playbook.yml --check
```

3. **Use semantic versioning for custom EEs**:
```bash
ansible-builder build -f execution-environment.yml -t my-ee:1.0.0
ansible-builder build -f execution-environment.yml -t my-ee:latest
```

4. **Document your EE**:
Add comments in `execution-environment.yml` explaining why specific collections/packages are needed.

5. **Keep EEs small**:
Only include collections you actually use. Smaller EEs = faster pulls and builds.

---

## Contributing

When making changes to this devcontainer:

1. **Test all profiles** - Ensure default, docker-socket, dind, and podman all work
2. **Update this README** - Document any new features or changes
3. **Keep dependencies locked** - Regenerate `requirements-ansible.txt` with `uv export`
4. **Maintain security defaults** - Don't weaken the hardened configuration without good reason

## License

MIT - See repository LICENSE file
