# Architecture Documentation

This document provides visual architecture diagrams and explanations for the devcontainer infrastructure.

## Container Build Hierarchy

```mermaid
graph TD
    A[python:3.14-slim-trixie] --> B[devcontainer-base]
    B --> C[devcontainer-ansible]
    C --> L[devcontainer-ansible-aws]

    K[python:3.14-slim-trixie] --> D[devcontainer-ansible-podman]

    E[debian:trixie-slim] --> F[devcontainer-terraform]
    F --> M[devcontainer-terraform-aws]
    E --> G[devcontainer-latex]

    H[golang:1.27-alpine] --> I[devcontainer-golang]

    style B fill:#e1f5ff
    style C fill:#fff4e1
    style D fill:#fff4e1
    style F fill:#e8f5e9
    style G fill:#fce4ec
    style L fill:#fff4e1
    style M fill:#e8f5e9
    style I fill:#f3e5f5
```

### Build Strategy

> Minor versions above are indicative. The exact digests are pinned in each
> `devcontainers/<stack>/Dockerfile`, which is the only source of truth --
> do not restate a patch version here, it will drift.

- **Base Layer** (`devcontainer-base`): Python foundation with uv and pre-commit
  - Published as `:main`, `:latest` and a Python stream tag derived from the
    image it is built FROM by `scripts/derive-python-tag.sh`. The tag is never
    typed by hand: it read `py313` for a long time while the image shipped
    Python 3.14.
  - Platforms: `linux/amd64`, `linux/arm64`
  - Runs as `vscode`, not root, like every stack built on it

- **Ansible Stacks**
  - `devcontainer-ansible`: built `FROM` `devcontainer-base` (a Dockerfile base, not a devcontainer `extends`)
  - `devcontainer-ansible-podman`: **does not** extend the base. It builds from
    `python:3.14-slim-trixie` and installs Podman from Debian, because the
    Debian build is ABI-coherent with the rest of the image. Copying binaries
    from `quay.io/containers/podman` was tried and never worked at runtime.
  - `devcontainer-ansible-aws`: `devcontainer-ansible` plus `amazon.aws`,
    `boto3`/`botocore` and AWS CLI v2. It is the `ansible-aws` stage of
    `devcontainers/ansible/Dockerfile`, built with `--target ansible-aws`.

- **Standalone Stacks**: Independent base images
  - `devcontainer-terraform`: Debian-based with HashiCorp tools
  - `devcontainer-terraform-aws`: `devcontainer-terraform` plus AWS CLI v2,
    the `terraform-aws` stage of `devcontainers/terraform/Dockerfile`
  - `devcontainer-golang`: Alpine-based Go development (musl). VS Code supports Alpine only as "Alpine Linux 64-bit x86 containers or WSL hosts" and warns that extensions may not work due to `glibc` dependencies in native code; it calls AArch64 "preview" (https://code.visualstudio.com/docs/remote/linux). The image is still published for arm64
  - `devcontainer-latex`: Debian-based with Tectonic engine

## Python Dependency Management Flow

```mermaid
graph LR
    A[pyproject.toml] -->|uv lock| B[uv.lock]
    B -->|uv export, hashed| R[requirements-*.txt]
    R -->|uv pip install --require-hashes| C[Container Runtime]

    D[Developer adds dependency] --> A
    E[Renovate] --> A

    F[ansible-playbook<br/>update-dependencies.yml] -->|automates| A

    style A fill:#e3f2fd
    style B fill:#fff3e0
    style C fill:#e8f5e9
```

### Workflow

1. **Define dependencies** in `pyproject.toml` with version constraints
2. **Lock versions** with `uv lock` (generates `uv.lock`)
3. **Export** the lock to hashed `requirements-*.txt` (`uv export`); these are generated, never edited by hand
4. **Install in the image** with `uv pip install --system --require-hashes -r requirements-ansible.txt` during build

### requirements files

`requirements-ansible.txt`, `requirements-aws.txt`, `requirements-devcontainer-tools.txt` and `requirements.txt` are generated from `uv.lock` with `uv export` (hashed). The Dockerfiles install them with `--require-hashes`, so a build installs what the lock says and nothing else. Do not edit them by hand: change `pyproject.toml`, run `uv lock`, and regenerate.

## Pre-commit Architecture

```mermaid
graph TD
    L[uv.lock] -->|uv export, hashed| R[requirements-*.txt]
    R -->|--require-hashes at build| A[Container image]
    A --> E[pre-commit + yamllint, pinned]

    C[Developer opens container] --> D[ensure-precommit.sh]
    D -->|copies template| F[.pre-commit-config.yaml]
    D -->|image's pre-commit install| G[Git hooks active]

    H[CI Pipeline] -->|uvx pre-commit run --all-files| I[Validates PRs]

    style A fill:#e1f5ff
    style E fill:#e8f5e9
    style F fill:#fff3e0
    style G fill:#e8f5e9
    style I fill:#f3e5f5
```

### Pinned at build time

Pre-commit and yamllint are baked into every image, at the versions `uv.lock` pins:

1. **Installed from the lock**: the ansible images from `requirements-ansible.txt`; base, terraform, golang and latex from `requirements-devcontainer-tools.txt` (the `devcontainer-tools` dependency group). Both are `uv export` output with a hash for every package, installed with `--require-hashes --only-binary :all:`.
2. **Their own interpreter where the image has none**: terraform, golang and latex install them into a root-owned venv at `/opt/devcontainer-tools`, on a uv-managed CPython pinned to the base image's version (uv verifies its sha256), and link only `pre-commit` and `yamllint` into `/usr/local/bin`.
3. **Template stored** at `/usr/local/share/devcontainer-skel/<stack>/.pre-commit-config.yaml`
4. **Script provided** at `/usr/local/bin/ensure-precommit`: copies the template and installs the git hook. It installs nothing; without pre-commit on `PATH` it fails, because the image is broken.

Benefits:
- The same pre-commit in every image as in the lock, bumped by Renovate's lock maintenance
- Scanned with the image, instead of downloaded unpinned on every container create
- Nothing to download when the container starts

## CI/CD Pipeline Flow

```mermaid
graph TD
    A[Push to main/<br/>Create PR] --> B{Event Type}

    B -->|PR| C[CI Pipeline]
    B -->|Push to main| D[Build & Publish]
    B -->|Tag push| E[Release Pipeline]
    B -->|Schedule: Daily| F[Security Refresh]

    C --> C1[Pre-commit Checks]
    C --> C2[Build Devcontainers]
    C --> C3[Run Tests]
    C --> C4[Grype Scan]

    C1 & C2 & C3 & C4 --> C5{All Pass?}
    C5 -->|Yes| C6[Ready to Merge]
    C5 -->|No| C7[Block Merge]

    D --> D1[Build base image]
    D1 --> D2[Build ansible variants]
    D1 --> D3[Build other stacks]
    D2 & D3 --> D4[Push to GHCR<br/>:latest + :sha-xxxxx]

    E --> E1[Wait until build-containers<br/>is idle on main]
    E1 --> E2[Pick gated digests<br/>:sha-xxxxx or :main]
    E2 --> E3[Verify cosign signature<br/>re-scan with Grype]
    E3 --> E4[Tag digests on GHCR<br/>:v1.2.3 + signed SBOMs]

    F --> F1[apt full-upgrade]
    F1 --> F2[Rebuild images]
    F2 --> F4[Push to GHCR]

    style C6 fill:#e8f5e9
    style C7 fill:#ffebee
    style D4 fill:#e3f2fd
    style E4 fill:#f3e5f5
```

### Build Matrix

The `build-containers.yml` workflow builds:

**build-base job:**
- `devcontainer-base` (always first)

**build-all job matrix:**
- `ansible` (main Dockerfile)
- `ansible` (Dockerfile.podman variant → `ansible-podman`)
- `ansible` (`ansible-aws` target → `ansible-aws`, on the same-run base)
- `terraform`
- `terraform` (`terraform-aws` target → `terraform-aws`)
- `golang`
- `latex` (amd64 only)

### Image Tags

- **On PR**: Build only, no push
- **On push to main** (and the daily run): `:latest`, `:main` and `:sha-<commit>` (the base also gets the derived `py<major><minor>` tag)
- **On tag push**: `:<tag>` only (e.g., `:v1.2.3`; `:py<major><minor>-<tag>` for the base), added to the digest build-containers already gated and signed -- a release rebuilds nothing and never moves `:latest`
- **Daily schedule** (`0 3 * * *`, uncached): Refreshes `:latest` and `:main` with security updates, only for images that pass the scan gate

## Container Variant Comparison

```mermaid
graph LR
    A[ansible] -->|Use Case| B[Standard Ansible<br/>automation]
    C[ansible-podman] -->|Use Case| D[Ansible + Container<br/>Execution Environments]

    A -->|Size| E[436 MiB]
    C -->|Size| F[518 MiB<br/>+Podman]

    A -->|Capabilities| G[Ansible playbooks<br/>Molecule tests<br/>Collections]
    C -->|Capabilities| H[Everything in ansible<br/>+ Podman rootless<br/>+ ansible-navigator<br/>+ ansible-builder]

    style B fill:#e3f2fd
    style D fill:#fff3e0
    style E fill:#e8f5e9
    style F fill:#fff3e0
```

### When to Use Each

**devcontainer-ansible (standard):**
- Traditional Ansible playbook development
- Molecule testing with Docker
- Collection development
- Lighter weight

**devcontainer-ansible-podman:**
- Building Ansible Execution Environments
- Rootless container workflows
- Testing EEs with ansible-navigator
- Working with container-based automation

## Tool Version Strategy

```mermaid
graph TD
    A[Renovate Bot] -->|Weekly scan, Mondays| B{New Version?}
    B -->|Yes| C[Create PR]
    B -->|No| D[Skip]

    C --> E[Update Dockerfile ARGs]

    E --> H[CI Builds & Tests]
    H -->|Pass| I[Auto-merge enabled]
    H -->|Fail| J[Manual review]

    K[Security Advisory] -->|Critical CVE| L[Manual bump]
    L --> C

    style C fill:#e3f2fd
    style I fill:#e8f5e9
    style J fill:#fff3e0
```

### Where each version lives

Versions are not restated here: a copy rots. Read them at the source.

| Tool | Source of truth | Update strategy |
|------|-----------------|-----------------|
| Python (images) | `FROM python:` in `devcontainers/base/Dockerfile` and `Dockerfile.podman`; `TOOLS_PYTHON_VERSION` where the image has no Python | Renovate, held at 3.14 patches |
| Go | `FROM golang:` in `devcontainers/golang/Dockerfile` | Renovate |
| Terraform, Terragrunt, TFLint, SOPS, age | `ARG *_VERSION` in `devcontainers/terraform/Dockerfile`, each download checksum-verified | Renovate |
| Tectonic | `ARG TECTONIC_VERSION` and the per-architecture sha256 in `devcontainers/latex/Dockerfile` | Renovate |
| ansible-core and the rest of the Python stack | `uv.lock` (exported to `requirements-ansible.txt`) | Renovate lock maintenance |
| uv | `ARG UV_VERSION` in the Dockerfiles | Renovate |
| AWS CLI | v2, `-aws` images only; pinned with its sha256 in `devcontainers/scripts/install-aws-cli.sh` | Renovate |
| GitHub CLI (`gh`) | Not pinned: the latest from GitHub's apt repository at build time | Rebuilt daily |
| Podman | Debian 13's `podman` package, installed in `Dockerfile.podman` | Daily rebuild |

## Security Scanning Flow

```mermaid
graph LR
    A[Image built] --> B[Pushed untagged, by digest]
    B --> C[Grype scan, every platform]
    C --> D{Fixable high/critical?}

    D -->|Yes| E[No tags, no signature: run goes red]
    D -->|No| F[Attest, sign with cosign, tag]

    F --> G[release.yml re-scans at release]
    G --> H[scan-release-images.yml rescans the newest release nightly]

    style E fill:#ffebee
    style F fill:#e8f5e9
```

### Exception Policy

`.grype.yaml` holds the exceptions, each with its reason. Third-party Go binaries (terraform, terragrunt, tflint, sops, age, gh, podman) are ignored only for the Go stdlib and `golang.org/x` modules embedded in them, scoped by package and binary location; the golang image's own toolchain is deliberately not covered. A CVE that needs an exception gets a single-CVE entry, never a blanket rule (see the AWS CLI's bundled CPython there).

## Workflow: Adding a New Dependency

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant PY as pyproject.toml
    participant UV as uv
    participant Lock as uv.lock
    participant CI as GitHub Actions

    Dev->>PY: Add package to dependencies
    Dev->>UV: Run 'uv lock'
    UV->>Lock: Generate lockfile
    Dev->>UV: Export hashed requirements-*.txt
    UV->>Dev: ✓ Dependencies resolved

    Dev->>CI: git push
    CI->>Lock: Read lockfile
    CI->>UV: uv pip install --require-hashes -r requirements-*.txt
    UV->>CI: Build containers
    CI->>CI: Run tests
    CI->>Dev: ✓ All checks pass
```

## GHCR Publishing Strategy

```mermaid
graph TD
    A[build-base job] -->|Builds & pushes| B[devcontainer-base: derived py tag]

    B -->|needs: build-base| C[build-all matrix]

    C --> D[ansible:latest]
    C --> E[ansible-podman:latest]
    C --> F[terraform:latest]
    C --> G[golang:latest]
    C --> H[latex:latest]

    I[Build Provenance] -->|Attested| D & E & F & G & H
    J[SBOM] -->|Generated| D & E & F & G & H

    style B fill:#e1f5ff
    style D fill:#fff4e1
    style E fill:#fff4e1
    style F fill:#e8f5e9
    style G fill:#f3e5f5
    style H fill:#fce4ec
```

### Image Naming Convention

```
ghcr.io/malpanez/devcontainer-<stack>[variant]:<tag>
```

Examples:
- `ghcr.io/malpanez/devcontainer-base:<derived py tag>` (see scripts/derive-python-tag.sh)
- `ghcr.io/malpanez/devcontainer-ansible:latest`
- `ghcr.io/malpanez/devcontainer-ansible-podman:latest`
- `ghcr.io/malpanez/devcontainer-terraform:sha-5575e8d`
- `ghcr.io/malpanez/devcontainer-golang:v1.2.3`

## Stack Selection Flow

```mermaid
graph TD
    A[Clone Repository] --> B{Which stack?}

    B -->|Ansible automation| C[./scripts/use-devcontainer.sh ansible]
    B -->|Terraform/IaC| D[./scripts/use-devcontainer.sh terraform]
    B -->|Go development| E[./scripts/use-devcontainer.sh golang]
    B -->|LaTeX documents| F[./scripts/use-devcontainer.sh latex]

    C --> G[Copies devcontainers/ansible/<br/>to .devcontainer/]
    D --> H[Copies devcontainers/terraform/<br/>to .devcontainer/]
    E --> I[Copies devcontainers/golang/<br/>to .devcontainer/]
    F --> J[Copies devcontainers/latex/<br/>to .devcontainer/]

    G & H & I & J --> K[code .]
    K --> L[Reopen in Container]
    L --> M[VS Code pulls GHCR image]
    M --> N[ensure-precommit runs]
    N --> O[Ready to develop]

    style C fill:#fff4e1
    style D fill:#e8f5e9
    style E fill:#f3e5f5
    style F fill:#fce4ec
    style O fill:#e8f5e9
```

## Multi-Architecture Build

```mermaid
graph LR
    A[GitHub Actions Runner] --> B[docker buildx]

    B --> C[Build amd64]
    B --> D[Build arm64]

    C --> E[amd64 layer]
    D --> F[arm64 layer]

    E & F --> G[Multi-arch manifest]
    G --> H[GHCR Registry]

    I[User pulls image] --> H
    H -->|Selects correct arch| J[Platform-specific layer]

    style C fill:#e3f2fd
    style D fill:#e3f2fd
    style G fill:#e8f5e9
```

### Platform Support

| Stack | amd64 | arm64 | Notes |
|-------|-------|-------|-------|
| base | ✅ | ✅ | |
| ansible | ✅ | ✅ | |
| ansible-podman | ✅ | ✅ | |
| terraform | ✅ | ✅ | |
| golang | ✅ | ✅ | |
| latex | ✅ | ❌ | The Dockerfile pins an aarch64 Tectonic too, but `build-containers.yml` builds and publishes latex for `linux/amd64` only |
| ansible-aws, terraform-aws | ✅ | ✅ | Stages of the ansible and terraform Dockerfiles |

## Summary

This architecture provides:

1. **Layered container strategy** - Shared base for Python stacks, standalone for others
2. **Modern Python packaging** - pyproject.toml + uv for fast, reproducible builds
3. **Baked-in tooling** - pre-commit and yamllint ship in every image at the versions `uv.lock` pins; nothing is installed when the container starts
4. **Security-first CI/CD** - Grype scan gate before any tag, cosign signatures, provenance attestation, SBOM generation
5. **Multi-arch support** - amd64 + arm64 for all stacks (except latex)
6. **Automated maintenance** - Renovate for dependencies, daily security refreshes

For implementation details, see:
- [README.md](../README.md) - General usage and setup
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development workflow
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues
