# Troubleshooting Guide

This guide helps you resolve common issues when using the devcontainer environments.

## Table of Contents

- [Container Build Issues](#container-build-issues)
- [GHCR Authentication](#ghcr-authentication)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Terraform Issues](#terraform-issues)
- [Network & Proxy Issues](#network--proxy-issues)
- [Performance Issues](#performance-issues)
- [Tool-Specific Issues](#tool-specific-issues)

---

## Container Build Issues

### Container won't build

**Symptoms**: `docker build` fails or hangs

**Solutions**:

1. **Clear Docker cache**:
   ```bash
   docker builder prune -af
   docker system prune -a --volumes
   ```

2. **Re-pull base images**:
   ```bash
   docker pull debian:bookworm-slim
   docker pull python:3.12-slim-bookworm
   docker pull golang:1.23-alpine
   ```

3. **Check network connectivity**:
   ```bash
   curl -I https://github.com
   curl -I https://pypi.org
   ```

4. **Verify Docker daemon**:
   ```bash
   docker info
   docker version
   ```

### "No space left on device"

**Solution**:
```bash
# Check disk usage
docker system df

# Clean up
docker system prune -a --volumes
docker builder prune -af

# Remove unused images
docker image prune -a
```

### Build fails with "permission denied"

**Solution** (Linux):
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, or:
newgrp docker
```

---

## GHCR Authentication

### Cannot pull images from ghcr.io

**Symptoms**: `Error response from daemon: unauthorized`

**Solutions**:

1. **Authenticate with GitHub token**:
   ```bash
   echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin
   ```

2. **Create Personal Access Token**:
   - Go to: https://github.com/settings/tokens
   - Generate new token (classic)
   - Select scopes: `read:packages`, `write:packages`, `delete:packages`
   - Save token and use it to login

3. **Check token permissions**:
   ```bash
   # Verify authentication
   docker pull ghcr.io/malpanez/devcontainer-ansible:latest
   ```

### Rate limiting

**Symptoms**: `You have reached your pull rate limit`

**Solution**:
```bash
# Authenticate to increase rate limit
docker login ghcr.io

# Or use a different registry mirror
```

---

## Pre-commit Hooks

### Hooks fail on first run

**Symptoms**: `[ERROR] Cowardly refusing to install hooks with `core.hooksPath` set.`

**Solutions**:

1. **Clean and reinstall hooks**:
   ```bash
   pre-commit clean
   pre-commit uninstall
   pre-commit install
   pre-commit install --install-hooks
   ```

2. **Run hooks manually**:
   ```bash
   pre-commit run --all-files
   ```

3. **Update hooks**:
   ```bash
   pre-commit autoupdate
   ```

### Ansible-lint errors

**Symptoms**: Ansible-lint fails with errors

**Solutions**:

1. **Check Ansible version**:
   ```bash
   ansible --version
   ansible-lint --version
   ```

2. **Use production profile**:
   ```bash
   ansible-lint --profile=production
   ```

3. **Skip specific rules** (in `.ansible-lint`):
   ```yaml
   skip_list:
     - name[casing]
     - yaml[line-length]
   ```

### Ruff formatting issues

**Solution**:
```bash
# Auto-fix issues
ruff check --fix .
ruff format .
```

---

## Terraform Issues

### Provider download fails

**Symptoms**: `Error: Failed to install provider`

**Solutions**:

1. **Check plugin cache**:
   ```bash
   ls -la ~/.terraform.d/plugin-cache
   export TF_PLUGIN_CACHE_DIR="${HOME}/.terraform.d/plugin-cache"
   ```

2. **Clear provider cache**:
   ```bash
   rm -rf .terraform/
   rm -rf ~/.terraform.d/plugin-cache/*
   terraform init -upgrade
   ```

3. **Use mirror** (corporate networks):
   ```hcl
   # .terraformrc
   provider_installation {
     network_mirror {
       url = "https://terraform-mirror.example.com/"
     }
   }
   ```

### Terraform version mismatch

**Symptoms**: `Required version constraints are not met`

**Solution**:
```bash
# Check current version
terraform version

# Verify devcontainer uses correct version
grep TERRAFORM_VERSION .github/versions.yml
```

### Terragrunt errors

**Solution**:
```bash
# Clear cache
rm -rf ~/.terragrunt-cache

# Run with debug
terragrunt plan --terragrunt-debug
```

---

## Network & Proxy Issues

### Behind corporate proxy

**Solution** (in `.devcontainer/devcontainer.json`):
```json
{
  "remoteEnv": {
    "HTTP_PROXY": "http://proxy.example.com:8080",
    "HTTPS_PROXY": "http://proxy.example.com:8080",
    "NO_PROXY": "localhost,127.0.0.1,.example.com"
  }
}
```

**Or in Docker daemon** (`/etc/docker/daemon.json`):
```json
{
  "proxies": {
    "default": {
      "httpProxy": "http://proxy.example.com:8080",
      "httpsProxy": "http://proxy.example.com:8080",
      "noProxy": "localhost,127.0.0.1"
    }
  }
}
```

### SSL certificate issues

**Solution**:
```bash
# Add custom CA certificate
export REQUESTS_CA_BUNDLE=/path/to/ca-bundle.crt
export SSL_CERT_FILE=/path/to/ca-bundle.crt
```

---

## Performance Issues

### Slow container builds

**Solutions**:

1. **Enable BuildKit**:
   ```bash
   export DOCKER_BUILDKIT=1
   export BUILDKIT_PROGRESS=plain
   ```

2. **Use cache mounts**:
   ```dockerfile
   RUN --mount=type=cache,target=/var/cache/apt \
       apt-get update && apt-get install -y ...
   ```

3. **Use registry cache**:
   ```bash
   docker buildx build \
     --cache-from type=registry,ref=ghcr.io/user/image:buildcache \
     --cache-to type=registry,ref=ghcr.io/user/image:buildcache,mode=max
   ```

### Slow devcontainer startup

**Solutions**:

1. **Use pre-built images from GHCR**:
   ```json
   {
     "image": "ghcr.io/malpanez/devcontainer-ansible:latest"
   }
   ```

2. **Optimize mounts**:
   ```json
   {
     "mounts": [
       "source=uv-cache,target=/home/vscode/.cache/uv,type=volume"
     ]
   }
   ```

3. **Reduce extensions**:
   - Only install necessary VS Code extensions

---

## Tool-Specific Issues

### LaTeX (Tectonic)

**Tectonic won't compile**:
```bash
# Clear cache
rm -rf ~/.cache/Tectonic

# Test compilation
tectonic --version
tectonic -X compile document.tex
```

### uv package manager

**uv install fails**:
```bash
# Clear cache
rm -rf ~/.cache/uv

# Reinstall
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify
uv --version
```

### Ansible collections

**Collections not found**:
```bash
# Install manually
ansible-galaxy collection install -r requirements.yml -p collections/

# Verify
ansible-galaxy collection list
```

---

## Getting Help

If none of these solutions work:

1. **Check logs**:
   ```bash
   # Docker logs
   docker logs <container_id>

   # VS Code devcontainer logs
   # Command Palette > "Dev Containers: Show Log"
   ```

2. **Open an issue**:
   - [GitHub Issues](https://github.com/malpanez/ansible-devcontainer-vscode/issues)
   - Include:
     - Error message
     - Steps to reproduce
     - Environment (OS, Docker version)
     - Relevant logs

3. **Check documentation**:
   - [README](../README.md)
   - [Corporate Network Guide](CORPORATE_NETWORK.md)
   - [DevContainer Debug](DEVCONTAINER_DEBUG.md)

---

## Quick Diagnostics

Run this diagnostic script:

```bash
#!/bin/bash
echo "=== Environment ==="
uname -a
docker --version
docker-compose --version

echo -e "\n=== Docker Info ==="
docker info | grep -E 'Server Version|Storage Driver|Docker Root Dir'

echo -e "\n=== Disk Usage ==="
df -h | grep -E 'Filesystem|/var/lib/docker|/$'

echo -e "\n=== Network ==="
curl -Is https://github.com | head -1
curl -Is https://pypi.org | head -1

echo -e "\n=== Containers ==="
docker ps -a

echo -e "\n=== Images ==="
docker images | head -10
```

Save as `diagnose.sh`, make executable, and run:
```bash
chmod +x diagnose.sh
./diagnose.sh
```
