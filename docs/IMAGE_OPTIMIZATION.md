# Docker Image Optimization

This document explains the techniques applied to keep devcontainer images as small as possible while remaining fully functional.

## Results

| Stack     | Before    | After   | Savings |
| --------- | --------- | ------- | ------- |
| Ansible   | ~1,050 MB | ~650 MB | −38%    |
| Terraform | ~480 MB   | ~240 MB | −50%    |
| LaTeX     | ~420 MB   | ~280 MB | −33%    |
| Go        | ~210 MB   | ~210 MB | —       |

For context, Microsoft's equivalent devcontainer images range from 1.4–1.8 GB.

---

## Techniques Applied

### 1. Drop Build-Time Packages (Ansible: −400 MB)

The single largest saving. `uv` resolves [manylinux](https://peps.python.org/pep-0513/) binary wheels for all packages declared in `pyproject.toml` — including `ansible`, `cryptography`, `cffi`, `boto3`, and `paramiko`. This means **no C compiler is needed** inside the image.

Removed from the Ansible image:

```
build-essential   (~200 MB with deps)
libffi-dev
libssl-dev
libonig-dev
python3-dev
pkg-config
```

The comment in the Dockerfile explains the rationale so future maintainers don't re-add them:

```dockerfile
# build-essential / libffi-dev / libssl-dev / python3-dev are intentionally
# omitted: uv resolves manylinux binary wheels for all packages in
# pyproject.toml (ansible, cryptography, cffi, etc.) so no C compiler is
# needed at image build time, saving ~400 MB.
```

### 2. Pin `uv` with Native Installer (All images)

Installing `uv` via `pip install uv` drags in pip's overhead. The native curl installer downloads a single ~10 MB standalone Rust binary:

```dockerfile
# renovate: datasource=github-releases depName=astral-sh/uv
ARG UV_VERSION=0.9.13
RUN curl -fsSL "https://astral.sh/uv/${UV_VERSION}/install.sh" | sh
```

Benefits:

- Smaller layer (no pip wheel cache)
- Version pinned and tracked by Renovate
- Reproducible across rebuilds

### 3. Multi-Stage Build for Terraform

The `fetch` stage downloads all binaries (terraform, terragrunt, tflint, sops, age) on `$BUILDPLATFORM` and only copies the binaries into the final image. The `curl`, `unzip`, and APT cache never appear in the final layer:

```dockerfile
FROM --platform=$BUILDPLATFORM debian:bookworm-slim AS fetch
# ... download tools ...

FROM debian:bookworm-slim
COPY --from=fetch --link --chmod=0755 /tmp/bin/terraform /usr/local/bin/terraform
```

The `--link` flag allows Docker to reuse the COPY layer independently of the layers before it, improving cache performance.

### 4. Remove Unused Packages

- Terraform fetch stage: removed `xz-utils` — none of the downloads use `.tar.xz` format (terraform=`.zip`, terragrunt=binary, tflint=`.zip`, sops=binary, age=`.tar.gz`)
- LaTeX: `perl` is kept only because Tectonic's font processing requires it

### 5. APT Cache Mounts + Cleanup

All `apt-get` calls use BuildKit cache mounts so the package index is never committed to a layer, and cleanup is always in the same `RUN` to prevent layer bloat:

```dockerfile
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends ... \
    && apt-get autoremove -y --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
```

### 6. Trim Build Context with `.dockerignore`

Large directories that are never referenced inside a `COPY` instruction are excluded from the build context to reduce transfer time:

```
.git
.github/
.claude/
collections/
docs/
playbooks/
roles/
scripts/
tests/
**/.molecule
**/.pytest_cache
**/__pycache__
```

### 7. Hardened Sudoers

`NOPASSWD: ALL` was replaced with explicit binary allowlists. This is a security improvement, not a size one, but it follows the principle of minimal surface area:

```dockerfile
# Before (too permissive):
printf '%s ALL=(root) NOPASSWD: ALL\n'

# After (explicit allowlist):
printf '%s ALL=(root) NOPASSWD: /usr/local/bin/uv, /usr/local/bin/uvx\n'
```

### 8. Renovate Annotations for All Tool Versions

Every `ARG TOOL_VERSION=x.y.z` now has a `# renovate:` annotation so Renovate Bot automatically opens PRs when new versions are released:

```dockerfile
# renovate: datasource=github-releases depName=hashicorp/terraform
ARG TERRAFORM_VERSION=1.14.4
```

This eliminates version drift without manual tracking.

---

## What Was Not Applied

### Distroless / scratch Base

Distroless images remove the shell, package manager, and most system utilities. This would break:

- DevContainer lifecycle scripts that require `bash`
- `git`, `gh`, and SSH tools needed for daily development
- `sudo` for occasional package additions at runtime

The `debian:bookworm-slim` base is already minimal (~30 MB). Switching to distroless would save ~25 MB at the cost of making the container non-functional as a dev environment.

### Checksum Verification for Tectonic

The [tectonic](https://tectonic-typesetting.github.io) project does not publish SHA256 checksum files alongside its release assets. Checksum verification was not added for tectonic downloads. The binary is still fetched over HTTPS from the official GitHub releases endpoint.

All other tools with upstream checksum files (age, terraform, terragrunt, tflint, sops) either verify via HTTPS or have checksum support available.
