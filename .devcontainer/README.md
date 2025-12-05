# Devcontainer Configuration

This directory contains the VS Code DevContainer configuration for the ansible-devcontainer-vscode project.

## Quick Start with GitHub Codespaces

Launch a fully configured development environment in your browser with one click:

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/malpanez/ansible-devcontainer-vscode)

**What you get**:
- ✅ Pre-built development environment (30-60 seconds to ready)
- ✅ All tools pre-installed (Ansible, Terraform, Python, etc.)
- ✅ VS Code in browser with all extensions
- ✅ No local setup required
- ✅ Works on any device with a browser

## Available Stacks

This project supports multiple development stacks. The `devcontainer.json` in this directory determines which stack is active.

| Stack     | Best For                          | Image Size | Startup Time |
|-----------|-----------------------------------|------------|--------------|
| Ansible   | Configuration management, automation | 650 MB     | ~8s          |
| Terraform | Infrastructure as Code            | 240 MB     | ~4s          |
| Golang    | Go development                    | 210 MB     | ~3s          |
| LaTeX     | Document preparation              | 320 MB     | ~5s          |

## Switching Stacks

### Method 1: Using Scripts

```bash
# From inside the workspace
./scripts/use-devcontainer.sh terraform
# Then: Cmd/Ctrl + Shift + P → "Dev Containers: Rebuild Container"
```

### Method 2: Using VS Code Tasks

1. Press `Cmd/Ctrl + Shift + P`
2. Type "Tasks: Run Task"
3. Select "Switch Devcontainer: Terraform" (or any other stack)
4. Rebuild the container when prompted

### Method 3: Using Makefile

```bash
make switch-terraform  # or ansible, golang, latex
# Then rebuild the container
```

## Configuration Details

The `devcontainer.json` file configures:

- **Base Image**: Pulled from GHCR (`ghcr.io/malpanez/devcontainer-*`)
- **Extensions**: Language-specific VS Code extensions
- **Settings**: Editor configuration, formatters, linters
- **Mounts**: Docker socket, cache volumes
- **Environment**: Variables for tools (Terraform, Ansible, etc.)
- **Post-create**: Automatic setup (pre-commit hooks, permissions)

## Features

### 🚀 Performance Optimizations

- **Named volumes** for caches (uv, pre-commit) → 3-5x faster rebuilds
- **Layer caching** → 60-80% faster when only code changes
- **GHCR prebuilt images** → 10x faster first-open (45s vs 5min)

### 🔧 Developer Experience

- **Auto-open files**: README and Quickstart guide
- **Port forwarding**: Automatic with labels (8080, 3000)
- **Pre-installed tools**: All dependencies ready to use
- **Git integration**: Hooks, LFS, credential helper

### 🔐 Security

- **Non-root user**: Runs as `vscode` user
- **Isolated networks**: DNS configured (Cloudflare 1.1.1.1)
- **Docker-in-Docker**: Isolated container builds

## Codespaces-Specific Configuration

When running in GitHub Codespaces, additional features are available:

- **Automatic file opening**: README.md and docs/QUICKSTART.md
- **Port labels**: Clear identification of forwarded ports
- **Secrets**: Access to GitHub secrets via environment variables
- **Faster startup**: Prebuilt images from GHCR

## Customization

### Add Your Own Extensions

Edit `devcontainer.json`:

```json
"customizations": {
  "vscode": {
    "extensions": [
      "existing.extension",
      "your.new.extension"
    ]
  }
}
```

### Add Environment Variables

```json
"containerEnv": {
  "MY_VAR": "value"
}
```

### Mount Additional Volumes

```json
"mounts": [
  "source=my-cache,target=/home/vscode/.cache/mycache,type=volume"
]
```

## Troubleshooting

### Container Won't Start

1. Check Docker is running: `docker ps`
2. Check image exists: `docker images | grep devcontainer`
3. Rebuild: Cmd/Ctrl + Shift + P → "Dev Containers: Rebuild Container"

### Slow Performance

- ✅ Use prebuilt images from GHCR (not local builds)
- ✅ Ensure Docker has enough resources (4GB+ RAM, 2+ CPUs)
- ✅ On Windows: Use WSL2, not Hyper-V backend

### Tools Not Found

1. Check you're in the correct stack (Ansible vs Terraform, etc.)
2. Run post-create command manually:
   ```bash
   sudo mkdir -p /home/vscode/.cache/pre-commit /workspace/.cache
   sudo chown -R vscode:vscode /home/vscode/.cache /workspace/.cache
   pre-commit install --install-hooks
   ```

## Performance Benchmarks

See [docs/PERFORMANCE.md](../docs/PERFORMANCE.md) for detailed benchmarks and optimization strategies.

| Scenario                  | Time    |
|---------------------------|---------|
| First open (GHCR image)   | ~45s    |
| First open (local build)  | 3-5min  |
| Reopen (no rebuild)       | ~15s    |
| Rebuild (with cache)      | 2-4min  |

## Documentation

- [QUICKSTART.md](../docs/QUICKSTART.md) - Getting started guide
- [VSCODE_WORKFLOW.md](../docs/VSCODE_WORKFLOW.md) - VS Code tasks and workflows
- [PERFORMANCE.md](../docs/PERFORMANCE.md) - Performance optimization
- [TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md) - Common issues

## Related Links

- [VS Code DevContainers Docs](https://code.visualstudio.com/docs/devcontainers/containers)
- [GitHub Codespaces Docs](https://docs.github.com/en/codespaces)
- [Our Published Images (GHCR)](https://github.com/malpanez?tab=packages&repo_name=ansible-devcontainer-vscode)

---

**Questions?** See the main [README.md](../README.md) or file an issue.
