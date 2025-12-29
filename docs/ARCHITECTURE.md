# Architecture Documentation

This document provides visual architecture diagrams and explanations for the devcontainer infrastructure.

## Container Build Hierarchy

```mermaid
graph TD
    A[python:3.12-slim-bookworm] --> B[devcontainer-base]
    B --> C[devcontainer-ansible]
    B --> D[devcontainer-ansible-podman]

    E[debian:bookworm-slim] --> F[devcontainer-terraform]
    E --> G[devcontainer-latex]

    H[golang:1.23-alpine] --> I[devcontainer-golang]

    J[quay.io/containers/podman:v5.3.1] -.->|binaries copied| D

    style B fill:#e1f5ff
    style C fill:#fff4e1
    style D fill:#fff4e1
    style F fill:#e8f5e9
    style G fill:#fce4ec
    style I fill:#f3e5f5
```

### Build Strategy

- **Base Layer** (`devcontainer-base`): Shared Python 3.12 foundation with uv and pre-commit
  - Published as: `ghcr.io/malpanez/devcontainer-base:py312`
  - Platforms: `linux/amd64`, `linux/arm64`

- **Ansible Stacks**: Extend base with Ansible tooling
  - `devcontainer-ansible`: Standard Ansible environment
  - `devcontainer-ansible-podman`: Ansible + Podman for rootless container workflows

- **Standalone Stacks**: Independent base images
  - `devcontainer-terraform`: Debian-based with HashiCorp tools
  - `devcontainer-golang`: Alpine-based Go development
  - `devcontainer-latex`: Debian-based with Tectonic engine

## Python Dependency Management Flow

```mermaid
graph LR
    A[pyproject.toml] -->|uv lock| B[uv.lock]
    B -->|uv pip install --system .| C[Container Runtime]

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
3. **Install in container** with `uv pip install --system .` during build
4. **No manual requirements.txt** - uv handles dependency resolution automatically

### Migration from requirements.txt

**Before (PR #85 and earlier):**
```bash
# Manual dependency management
uv pip install -r requirements-ansible.txt
```

**After (PR #86+):**
```bash
# Automated dependency resolution
cd /tmp && uv pip install --system .
```

Benefits:
- Single source of truth (`pyproject.toml`)
- Automatic conflict resolution
- No manual lockfile maintenance
- Standard Python packaging format

## Pre-commit Architecture

```mermaid
graph TD
    A[Container Build] -->|Does NOT install| B[pre-commit]

    C[Developer opens container] --> D[ensure-precommit.sh]
    D -->|uv tool install pre-commit| E[pre-commit installed]
    D -->|copies template| F[.pre-commit-config.yaml]
    D -->|uvx pre-commit install| G[Git hooks active]

    H[CI Pipeline] -->|uvx pre-commit run --all-files| I[Validates PRs]

    style A fill:#e1f5ff
    style E fill:#e8f5e9
    style F fill:#fff3e0
    style G fill:#e8f5e9
    style I fill:#f3e5f5
```

### Lazy Loading Strategy

Pre-commit is **NOT** baked into container images. Instead:

1. **Template stored** at `/usr/local/share/devcontainer-skel/<stack>/.pre-commit-config.yaml`
2. **Script provided** at `/usr/local/bin/ensure-precommit`
3. **Installed on-demand** via `uv tool install pre-commit`
4. **Always fresh** - gets latest version when installed

Benefits:
- Smaller container images (~50MB saved)
- Always up-to-date pre-commit
- Fast installs via uv
- Consistent across all stacks

## CI/CD Pipeline Flow

```mermaid
graph TD
    A[Push to main/<br/>Create PR] --> B{Event Type}

    B -->|PR| C[CI Pipeline]
    B -->|Push to main| D[Build & Publish]
    B -->|Tag push| E[Release Pipeline]
    B -->|Schedule: Weekly| F[Security Refresh]

    C --> C1[Pre-commit Checks]
    C --> C2[Build Devcontainers]
    C --> C3[Run Tests]
    C --> C4[Security Scan]

    C1 & C2 & C3 & C4 --> C5{All Pass?}
    C5 -->|Yes| C6[Ready to Merge]
    C5 -->|No| C7[Block Merge]

    D --> D1[Build base image]
    D1 --> D2[Build ansible variants]
    D1 --> D3[Build other stacks]
    D2 & D3 --> D4[Push to GHCR<br/>:latest + :sha-xxxxx]

    E --> E1[Build all images]
    E1 --> E2[Generate SBOMs]
    E2 --> E3[Sign with cosign]
    E3 --> E4[Push to GHCR<br/>:latest + :v1.2.3]

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
- `terraform`
- `golang`
- `latex` (amd64 only)

### Image Tags

- **On PR**: Build only, no push
- **On push to main**: `:latest` + `:sha-<commit>`
- **On tag push**: `:latest` + `:<tag>` (e.g., `:v1.2.3`)
- **Weekly schedule**: Refreshes `:latest` with security updates

## Container Variant Comparison

```mermaid
graph LR
    A[ansible] -->|Use Case| B[Standard Ansible<br/>automation]
    C[ansible-podman] -->|Use Case| D[Ansible + Container<br/>Execution Environments]

    A -->|Size| E[~650 MB]
    C -->|Size| F[~780 MB<br/>+Podman binaries]

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
    A[Renovate Bot] -->|Weekly scan| B{New Version?}
    B -->|Yes| C[Create PR]
    B -->|No| D[Skip]

    C --> E[Update Dockerfile ARGs]
    C --> F[Update README badges]
    C --> G[Update version table]

    E & F & G --> H[CI Builds & Tests]
    H -->|Pass| I[Auto-merge enabled]
    H -->|Fail| J[Manual review]

    K[Security Advisory] -->|Critical CVE| L[Manual bump]
    L --> C

    style C fill:#e3f2fd
    style I fill:#e8f5e9
    style J fill:#fff3e0
```

### Current Versions (as of December 2025)

| Tool | Version | Update Strategy |
|------|---------|----------------|
| Python | 3.12.12 | Patch version pinned in base image |
| Go | 1.25 | Minor version pinned, patch auto-update |
| Terraform | 1.14.0 | Patch version pinned, manual minor updates |
| Terragrunt | 0.93.11 | Minor auto-update via Renovate |
| TFLint | 0.60.0 | Minor auto-update via Renovate |
| SOPS | 3.11.0 | Minor auto-update via Renovate |
| age | 1.2.1 | Minor auto-update via Renovate |
| Tectonic | 0.15.0 | Minor auto-update via Renovate |
| Ansible | 9.14.0 | Locked via pyproject.toml + uv.lock |
| uv | 0.9.13 | Pinned in base image |
| AWS CLI | v2 (latest) | Auto-update from official installer |
| github-cli (gh) | latest | Auto-update from apt repository |
| Podman | 5.7.0 | From official Podman image |

## Security Scanning Flow

```mermaid
graph LR
    A[Container Built] --> B[Trivy Scan]
    B --> C{Findings?}

    C -->|CRITICAL| D[Block Build]
    C -->|HIGH| E[Review .trivyignore]
    C -->|MEDIUM/LOW| F[Allow & Track]

    E -->|Documented exception| G[Allow with tracking]
    E -->|New CVE| H[Update tool version]

    H --> I[Vendor releases patch?]
    I -->|Yes| J[Bump version]
I -->|No| K[Document in .trivyignore<br/>with tracking URL]

    style D fill:#ffebee
    style F fill:#e8f5e9
    style G fill:#fff3e0
    style J fill:#e3f2fd
```

### Trivy Exception Policy

`.trivyignore` documents CVEs with:
- Affected tool and version
- CVE identifier
- Upstream tracking URL
- Justification for temporary exception
- Review date

**Example:**
```
# Terragrunt v0.93.11 - Waiting for upstream fix
# https://github.com/gruntwork-io/terragrunt/issues/XXXX
CVE-2024-XXXXX
```

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
    Dev->>UV: Test locally: 'uv pip install --system .'
    UV->>Dev: ✓ Dependencies resolved

    Dev->>CI: git push
    CI->>Lock: Read lockfile
    CI->>UV: uv pip install --system .
    UV->>CI: Build containers
    CI->>CI: Run tests
    CI->>Dev: ✓ All checks pass
```

## GHCR Publishing Strategy

```mermaid
graph TD
    A[build-base job] -->|Builds & pushes| B[devcontainer-base:py312]

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
- `ghcr.io/malpanez/devcontainer-base:py312`
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
| latex | ✅ | ❌ | Tectonic binaries currently amd64-only |

## Summary

This architecture provides:

1. **Layered container strategy** - Shared base for Python stacks, standalone for others
2. **Modern Python packaging** - pyproject.toml + uv for fast, reproducible builds
3. **Lazy-loaded tooling** - Pre-commit installed on-demand, not baked into images
4. **Security-first CI/CD** - Trivy scanning, provenance attestation, SBOM generation
5. **Multi-arch support** - amd64 + arm64 for all stacks (except latex)
6. **Automated maintenance** - Renovate for dependencies, weekly security refreshes

For implementation details, see:
- [README.md](../README.md) - General usage and setup
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development workflow
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues
