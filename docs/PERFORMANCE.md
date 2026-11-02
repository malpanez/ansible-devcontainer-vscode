# Performance Optimization Guide

**Last Updated**: 2026-11-01. Every figure below comes from CI on commit `e7c0c97` (v2.2.0) and says which run measured it. Nothing else measures performance here, so figures that earlier versions of this guide gave for ansible-playbook, Terraform plan, Go build, bind-mount I/O, pre-commit, workflow durations, cache hit rates, arm64 builds and VS Code open times were removed rather than left stale.

This guide documents what is measured, what is not, and optimization strategies for the ansible-devcontainer-vscode project.

---

## Table of Contents

- [What Is Measured](#what-is-measured)
- [Image Size](#image-size)
- [Build and Startup Time](#build-and-startup-time)
- [Optimization Strategies](#optimization-strategies)
- [Monitoring & Benchmarking](#monitoring--benchmarking)

---

## What Is Measured

`.github/workflows/benchmark.yml` runs on pull requests and pushes that touch `devcontainers/**` and the requirements exports, on `workflow_dispatch`, and weekly on Monday at 06:00 UTC. It measures:

| Job | What it times | Stacks |
|-----|---------------|--------|
| Container Startup Time | Wall time of `docker run --rm <image> echo Ready`, 3 iterations, averaged. The image is built in the job, with the `buildcache-publish` registry cache when one exists. | base, ansible, terraform |
| Build Time Benchmark | `docker buildx build` of the stack, once with `--no-cache` ("cold") and once with the registry cache as `--cache-from` ("warm"). | ansible, terraform |
| Resource Usage Benchmark | `docker stats` memory and CPU of an idle `sleep 30` container built from `.devcontainer/Dockerfile`. | the repository's own devcontainer |

Golang and LaTeX are not benchmarked. The jobs run on `ubuntu-latest`; in the run below that was the Ubuntu 26 runner image `20261025.179` with 15.61 GiB of memory. Numbers from a shared runner vary from run to run.

---

## Image Size

The `linux/amd64` images of v2.2.0 (commit `e7c0c97`). Uncompressed is `docker image inspect` `.Size` on the runner, from the size gate of `ci.yml` (run 41337212915), and for base, which that gate does not build, the sum of its layers' files from [the release notes](release-notes/v2.2.0.md#sizes). Compressed is what a pull downloads, from the publish report of `build-containers.yml` (run 41337212893). The limits are in [`.github/image-size-budgets.json`](../.github/image-size-budgets.json).

| Stack         | Uncompressed | Compressed (zstd) |
|---------------|--------------|-------------------|
| base          | 330.1 MiB    | 93.9 MiB          |
| ansible       | 436.0 MiB    | 119.0 MiB         |
| ansible-podman | 523.5 MiB   | 148.2 MiB         |
| ansible-aws   | 718.8 MiB    | 195.5 MiB         |
| terraform     | 668.7 MiB    | 187.6 MiB         |
| terraform-aws | 918.2 MiB    | 247.2 MiB         |
| golang        | 376.2 MiB    | 103.0 MiB         |
| latex         | 335.4 MiB    | 96.5 MiB          |

---

## Build and Startup Time

Measured by `benchmark.yml`, run 41337213035 on `main` (2026-11-01). CI measured these on a GitHub-hosted runner; they are not a statement about a developer machine.

| Stack     | Cold build (`--no-cache`) | Warm build (registry cache) | Startup (average of 3) | Startup, each iteration |
|-----------|---------------------------|-----------------------------|------------------------|-------------------------|
| base      | not measured              | not measured                | 448 ms                 | 879, 234, 231 ms        |
| ansible   | 44 s                      | 3 s                         | 677 ms                 | 1596, 215, 221 ms       |
| terraform | 43 s                      | 3 s                         | 1556 ms                | 4247, 181, 241 ms       |

**Notes**:
- Startup is `docker run --rm <image> echo Ready`: the time to start a container and exit, not the time for VS Code to open a dev container. The first iteration was the slowest in all three runs, which is most of the average.
- The warm build re-uses a registry cache, so it measures cache lookups, not a rebuild with changed inputs.
- The Resource Usage job writes its memory and CPU figures to the job summary only, so no figure from it is quoted here.

Nothing in CI times a `linux/arm64` build, a Golang or LaTeX build, a bind-mount workload, or the time VS Code takes to reopen a container.

---

## Optimization Strategies

### 1. Docker Layer Caching

**Before**:
```dockerfile
# Bad: Changes to code invalidate all subsequent layers
COPY . /workspace
RUN pip install -r requirements.txt
```

**After**:
```dockerfile
# Good: Dependencies cached separately from code
COPY requirements.txt /workspace/
RUN pip install -r /workspace/requirements.txt
COPY . /workspace
```

---

### 2. BuildKit Cache Mounts

**Before**:
```dockerfile
RUN apt-get update && apt-get install -y python3
```

**After**:
```dockerfile
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    apt-get update && apt-get install -y python3
```

---

### 3. Multi-Stage Builds

**Example** (Terraform stack):
```dockerfile
# Stage 1: Build tools
FROM debian:trixie-slim AS builder
RUN apt-get update && apt-get install -y wget unzip
RUN wget https://releases.hashicorp.com/terraform/1.9.6/terraform_1.9.6_linux_amd64.zip
RUN unzip terraform*.zip

# Stage 2: Runtime (smaller)
FROM debian:trixie-slim
COPY --from=builder /terraform /usr/local/bin/
```

---

### 4. Named Volumes for Caches

Bind mounts cross the host file system, which is slow on Docker Desktop and WSL2. Keep caches in named volumes, as the stack templates do:

**Before**:
```json
"mounts": [
  "source=${localWorkspaceFolder},target=/workspace,type=bind"
]
```

**After**:
```json
"mounts": [
  "source=${localWorkspaceFolder},target=/workspace,type=bind",
  "source=uv-cache,target=/home/vscode/.cache/uv,type=volume",
  "source=ansible-galaxy-cache,target=/home/vscode/.ansible,type=volume"
]
```

---

### 5. Parallel Builds

**GitHub Actions** (build all stacks in parallel):
```yaml
strategy:
  matrix:
    stack: [ansible, terraform, golang, latex]
  max-parallel: 4
```

---

### 6. Prebuilt Images

Pull the published images from GHCR instead of building: the templates under `devcontainers/` reference them, so opening a dev container is a pull, not a build.

---

### 7. Reduce Image Size

```dockerfile
# Remove apt cache
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Remove pip cache
RUN pip cache purge

# Remove unnecessary files
RUN find /usr/local -type d -name __pycache__ -exec rm -rf {} +
```

The size budgets above turn growth into a failing pull request instead of a surprise.

---

## Monitoring & Benchmarking

### Automated Benchmarking

`benchmark.yml` (see [What Is Measured](#what-is-measured)) uploads one JSON file per job as an artifact kept for 90 days (`benchmark-<stack>`, `benchmark-build-<stack>`). On pull requests its `Compare with Baseline` job prints the current figures in the job summary and comments them on the pull request. It compares against nothing stored and applies no threshold: a regression is noticed by reading the numbers, not by a failing check.

To read the latest figures from the command line:

```bash
gh run list --workflow benchmark.yml --branch main --limit 1
gh run download <run-id> --pattern 'benchmark-*'
```

### Local Benchmarking

```bash
# Benchmark container build
time docker build --no-cache -t devcontainer-ansible -f devcontainers/ansible/Dockerfile .

# Benchmark with cache
time docker build -t devcontainer-ansible -f devcontainers/ansible/Dockerfile .

# Benchmark startup
time docker run --rm devcontainer-ansible /bin/bash -c "echo ready"

# Profile with docker stats
docker stats --no-stream <container-id>
```

---

## Tools for Performance Analysis

### Docker BuildKit

```bash
# Enable detailed build output
export DOCKER_BUILDKIT=1
docker build --progress=plain .
```

### Docker Build Timing

```bash
# Use BuildKit's timing feature
docker buildx build --progress=plain --no-cache . 2>&1 | grep "DONE"
```

### Container Dive

```bash
# Analyze image layers
dive devcontainer-ansible:latest
```

### Hyperfine (Benchmarking)

```bash
# Benchmark with statistical analysis
hyperfine 'docker run --rm devcontainer-ansible /bin/bash -c "echo ready"'
```

---

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Container build architecture
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development workflow
- [VSCODE_WORKFLOW.md](VSCODE_WORKFLOW.md) - VS Code performance tips
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Performance issues

---

**Questions or performance issues?** File an issue with benchmarks and system details.
