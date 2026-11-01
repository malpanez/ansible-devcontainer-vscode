# Ansible DevContainer

A production-ready Ansible development container with hardened defaults, multiple runtime profiles, and integrated tooling.

## Features

- **Python 3.14** with `uv` package manager for fast, reproducible installs
- **ansible-core** with ansible-lint, ansible-navigator and a small set of
  pinned collections (see [Ansible collections](#ansible-collections))
- **Pre-commit hooks** automatically configured
- **VS Code extensions** for Ansible, Python, YAML, and Docker
- **Hardened security defaults** (no sudo installed, docker socket only by opt-in)
- **Multiple runtime profiles** (default, docker-socket, dind, podman, aws)
- **Podman + Execution Environments** support for modern Ansible workflows

## Quick Start

### Default Profile

The default configuration has no access to the host Docker daemon:

```bash
# 1. Make ansible the active stack of this repository
./scripts/use-devcontainer.sh ansible
# 2. Open the repository in VS Code
# 3. Run: "Dev Containers: Reopen in Container"
```

This is the **recommended** profile for most use cases. Pick the
docker-socket or dind profile only when you need to run containers
(e.g. molecule with the docker driver) from inside the devcontainer.

## Runtime Profiles

A profile is a complete `devcontainer.json`, not a set of overrides: the
[dev container specification](https://containers.dev/implementors/json_reference/)
has no `extends` property, so one file cannot inherit from another. Tools look
for `.devcontainer/devcontainer.json`, `.devcontainer.json` or
`.devcontainer/<folder>/devcontainer.json`, and the Dev Containers CLI refuses
any other file name, so `devcontainer.dind.json` cannot be opened where it lies.

To use a profile, copy it into a folder of its own under `.devcontainer/`, as
each section below shows. **Reopen in Container** then asks which configuration
to open. Run `use-devcontainer.sh` first: it replaces all of `.devcontainer/`.
In a repository of your own, copy the profile to `.devcontainer/devcontainer.json`.

### 1. default ✅ Recommended

**File:** `devcontainer.json`

**When to use:**
- Standard development (playbooks, roles, linting, unit tests)
- You do not need to launch containers from inside the devcontainer

**Characteristics:**
- No Docker socket access — the container cannot control the host
- Fast and lightweight

**Select in VS Code:**
```bash
./scripts/use-devcontainer.sh ansible
```

---

### 1b. docker-socket ⚠️ Host-equivalent access

**File:** `devcontainer.docker-socket.json` (terraform has one too, in
`devcontainers/terraform/`)

**When to use:**
- Running molecule with the docker driver inside the devcontainer
- You explicitly want to share the host's Docker daemon

**Characteristics:**
- Uses `ghcr.io/devcontainers/features/docker-outside-of-docker:1`, which
  installs the `docker` CLI and mounts `/var/run/docker.sock` from the host
- **Grants root-equivalent access to the host.** Anything that runs in the
  container, a pre-commit hook or a Molecule scenario included, can start a
  privileged container that mounts the host's `/`. Treat it as
  trusted-workload-only
- `docker` commands act on the host's own containers, images and volumes, so a
  `docker system prune` here prunes the host
- Runs the container as root (`containerUser`): the feature gives `vscode`
  access to the socket from the container's entrypoint, and the images carry no
  `sudo` for it to use. Terminals, tasks and lifecycle commands still run as `vscode`
  (`remoteUser`)
- Paths in `docker run -v` are paths on the host, because the host's daemon
  reads them: `/workspace` does not exist there. Add
  `"LOCAL_WORKSPACE_FOLDER": "${localWorkspaceFolder}"` to `remoteEnv` and mount
  `${LOCAL_WORKSPACE_FOLDER}` instead
- `"moby": false` installs Docker CE from `download.docker.com`, because the
  feature refuses its default, Moby, on Debian trixie. The first open builds that
  on top of the image, which takes a couple of minutes and needs that host and
  `github.com`
- Expects the daemon's socket at `/var/run/docker.sock`. Rootless Docker keeps it
  elsewhere, so add a mount of it on `/var/run/docker-host.sock`, the path of the
  feature's `socketPath` option

**Select in VS Code:**
```bash
./scripts/use-devcontainer.sh ansible
mkdir -p .devcontainer/docker-socket
cp devcontainers/ansible/devcontainer.docker-socket.json .devcontainer/docker-socket/devcontainer.json
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
- Runs the container as root (`containerUser`): the feature starts the daemon
  from the container's entrypoint, and the images carry no `sudo` for it to use.
  Terminals, tasks and lifecycle commands still run as `vscode` (`remoteUser`)
- Independent Docker daemon inside container
- No Docker socket mount
- `"moby": false` installs Docker CE from `download.docker.com`, because the
  feature refuses its default, Moby, on Debian trixie. The first open builds that
  on top of the image and needs that host and `github.com`

**Select in VS Code:**
```bash
./scripts/use-devcontainer.sh ansible
mkdir -p .devcontainer/dind
cp devcontainers/ansible/devcontainer.dind.json .devcontainer/dind/devcontainer.json
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
```bash
./scripts/use-devcontainer.sh ansible
mkdir -p .devcontainer/podman
cp devcontainers/ansible/devcontainer.podman.json .devcontainer/podman/devcontainer.json
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

### 4. aws (AWS CLI, `amazon.aws`, `boto3`)

**File:** `devcontainer.aws.json`

**When to use:**
- Ansible content that talks to AWS

**Characteristics:**
- Opens `devcontainer-ansible-aws`; otherwise the same as the default profile
- **No `~/.aws` mount**: it starts on a machine without one, and the
  container cannot read or change the host's credentials
- Forwards `AWS_PROFILE`, `AWS_REGION` and `AWS_DEFAULT_REGION` only if they
  are set on the host (`"runArgs": ["--env", "AWS_PROFILE", ...]`; a
  `remoteEnv` entry with `${localEnv:...}` would pass an empty string, which
  the AWS CLI rejects)

**Logging in** happens inside the container: `aws configure`, or
`aws sso login --no-browser` and open the printed URL on the host. The login
is lost when the container is rebuilt.

**Using the host's `~/.aws` instead:** add this entry to `mounts` in your
copy of the profile:

```json
"source=${localEnv:HOME}/.aws,target=/home/vscode/.aws,type=bind,readonly"
```

With `readonly`, `aws sso login` cannot write its token cache; without it,
anything in the container can change the host's credentials. Either way the
container does not start if `~/.aws` does not exist on the host.

**Select in VS Code:**
```bash
./scripts/use-devcontainer.sh ansible
mkdir -p .devcontainer/aws
cp devcontainers/ansible/devcontainer.aws.json .devcontainer/aws/devcontainer.json
```

---

## What Gets Installed

### System Packages
- `git`, `gh` (via apt, not features - simpler and faster)
- `openssh-client`, `rsync` (for Ansible connectivity)
- `curl`, `ca-certificates`, `unzip` (for downloads)
- `jq`, `vim-tiny` (from the shared devcontainer-base); `yamllint` is a Python package, see below
- No compiler toolchain: Python packages install from wheels, and the
  one source build (onigurumacffi on arm64) happens in a builder stage

### Python Packages (via uv)
The image ships the runtime toolchain: `ansible-core`, `ansible-lint`,
`ansible-navigator`, `yamllint`, `pre-commit`, and the Python libraries
`community.docker` imports (`docker`, `requests`, `paramiko`). See
`requirements-ansible.txt` for the full pinned list.

Not the `ansible` package: since v2.0.0 the image no longer carries its 92
bundled collections, only the ones listed below.

Development/test tooling (molecule, pytest family, black/ruff/mypy,
ipython) lives in the `dev` dependency group — run `uv sync` in a
workspace with a pyproject to get it, or `uv sync --group aws` for
boto3/botocore.

### Ansible collections

| Collection | Why it is here |
|------------|----------------|
| `ansible.posix` | POSIX modules (`synchronize`, `mount`, `sysctl`, `authorized_key`, ...) |
| `community.general` | The general-purpose community modules and filters |
| `community.docker` | Docker modules, the Docker connection and inventory plugins |
| `community.library_inventory_filtering_v1` | Dependency of `community.docker` and `community.general` |

The exact versions are in [`collections.txt`](collections.txt), each with
the sha256 of its Galaxy artifact. The build downloads every artifact,
checks it against that hash and installs them all offline, so a bumped
version without its hash fails the build. Renovate bumps the versions and
the Renovate Post-Process workflow recomputes the hashes
(`scripts/refresh-collection-pins.py`).

They live in `/usr/local/lib/python3.*/site-packages/ansible_collections`,
where the `ansible` package used to put its bundle, so ansible-core finds
them whatever `collections_path` your `ansible.cfg` sets. Collections you
install yourself go to `~/.ansible/collections` (a named volume in these
profiles) and take precedence, so a project can pin a different version of
any of them.

Anything else, install it per project. Every profile does it on creation
from the workspace's `requirements.yml`:

```yaml
# requirements.yml
collections:
  - name: community.crypto
  - name: amazon.aws
```

or by hand: `ansible-galaxy collection install community.crypto`, or
`ansible-galaxy collection install -r requirements.yml` to pick up a change
without rebuilding.

Their Python requirements are separate: a collection such as `amazon.aws`
needs `boto3`. `/usr/local` belongs to root, so install it for the `vscode`
user with `python3 -m pip install --user boto3` (uv has no `--user` mode),
or into a project virtual environment.

### AWS: `devcontainer-ansible-aws`

For AWS work there is a variant with everything above plus:

- `amazon.aws`, pinned with its sha256 in
  [`collections-aws.txt`](collections-aws.txt) and installed like the
  collections above;
- `boto3` and `botocore`, at the versions and hashes of
  `requirements-aws.txt` (the lock's `aws` group);
- AWS CLI v2, pinned in `devcontainers/scripts/install-aws-cli.sh`.

It is the `ansible-aws` stage of this directory's `Dockerfile`
(`docker build --target ansible-aws -f devcontainers/ansible/Dockerfile .`),
published from v2.0.0 on as `ghcr.io/malpanez/devcontainer-ansible-aws`.
The `aws` profile below opens it.

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

### No sudo

The images do **not install `sudo`**, so the `vscode` user has no way to
escalate; every package is installed at image build time. To add tooling, extend the Dockerfile and
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

The shared `devcontainers/base/Dockerfile` installs a pinned `uv` release as
a direct binary download (no pipe-to-shell) and verifies its published
SHA-256 checksum. The version is the `ARG UV_VERSION` at the top of that
file, the single source of truth.

### Base Image Pinning (Optional)

You can pin the base image to a specific digest for full reproducibility:

```dockerfile
# In devcontainers/ansible/Dockerfile
ARG BASE_IMAGE=ghcr.io/malpanez/devcontainer-base:main@sha256:...
```

To get the current digest:
```bash
docker pull ghcr.io/malpanez/devcontainer-base:main
docker inspect ghcr.io/malpanez/devcontainer-base:main | jq -r '.[0].RepoDigests[0]'
```

### Locked Dependencies

All Python dependencies are locked with hashes in `requirements-ansible.txt`,
exported from `uv.lock`:

```txt
ansible-core==2.21.5 \
    --hash=sha256:08886f9f3e23d129aa98a01271c4a47833516e1cb7c737a246788cb474f41222 \
    --hash=sha256:65bb3148c58ebb843cd5074004c805f404f152114d98476dd823324616c9c6cb
```

The collections are pinned the same way, by version and sha256, in
`collections.txt`.

## Project Structure

```
devcontainers/ansible/
├── Dockerfile                     # Multi-arch Ansible image
├── Dockerfile.podman              # Podman + Execution Environments image
├── collections.txt                # Collections baked into both images (version + sha256)
├── install-collections.sh         # Verifies and installs collections.txt at build time
├── devcontainer.json              # Default profile (no docker socket)
├── devcontainer.docker-socket.json # Host Docker daemon profile (opt-in)
├── devcontainer.dind.json         # Docker-in-Docker profile
├── devcontainer.podman.json       # Podman profile
├── devcontainer.aws.json          # AWS profile (devcontainer-ansible-aws)
└── README.md                      # This file
```

## Troubleshooting

### Ansible Galaxy Collections Fail to Install

**Symptom:** `postCreateCommand` fails with "requirements.yml not found"

**Solution:** This is expected if your repository doesn't have Ansible collections. The command is designed to be idempotent and will skip collection installation gracefully.

### `couldn't resolve module/action` for a collection

**Symptom:** a playbook or ansible-lint fails with `couldn't resolve
module/action 'amazon.aws.ec2_instance'` (or any collection outside the
table in [Ansible collections](#ansible-collections)).

**Solution:** the image ships only those collections. Add the missing one to
your project's `requirements.yml` and run
`ansible-galaxy collection install -r requirements.yml`, or install it
directly with `ansible-galaxy collection install amazon.aws`. For
`amazon.aws`, `devcontainer-ansible-aws` ships it with `boto3` (see
[AWS](#aws-devcontainer-ansible-aws)).

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

Copy the profile you want to `.devcontainer/devcontainer.json` in your
repository root. There is no `extends` in the specification, so the copy stands
alone and later changes to the profile do not reach it:

```bash
mkdir -p .devcontainer
cp devcontainers/ansible/devcontainer.json .devcontainer/devcontainer.json
```

Then edit the copy, for example to add settings:

```json
{
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

Add them to `remoteEnv` in your copy of the profile:

```json
{
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

**New:** copy one profile, as in [Runtime Profiles](#runtime-profiles):

| For | Profile |
| --- | --- |
| Most users | `devcontainer.json` |
| The host Docker daemon | `devcontainer.docker-socket.json` |
| Isolated Docker | `devcontainer.dind.json` |
| Podman + Execution Environments (AAP) | `devcontainer.podman.json` |

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
