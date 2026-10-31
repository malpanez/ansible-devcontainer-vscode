# Using malpanez DevContainers in External Projects

**For**: Ansible Collections, Terraform Projects, and Infrastructure-as-Code

---

## Why Use These DevContainers?

Our devcontainers are superior to official images:

**✅ Production-Ready Tools**:
- Pinned, current tool versions (see `uv.lock`, the `ARG *_VERSION` lines in `devcontainers/*/Dockerfile` and `devcontainers/ansible/collections.txt` for the exact ones)
- Pre-configured security tools (SOPS, age; Trivy and gitleaks run as pre-commit hooks, not from the image)
- Optimized for infrastructure work

**✅ Security First**:
- Pinned dependencies by SHA256
- Pre-commit hooks configured
- Security scanning integrated
- OpenSSF Scorecard: 6.1/10

**✅ Performance Optimized**:
- Build caching enabled
- Multi-arch support (amd64/arm64)
- Minimal layers (faster builds)
- uv package manager (10-100x faster than pip)

**✅ Developer Experience**:
- VS Code extensions pre-configured
- Git workflow optimized
- Quality checks automated
- Consistent environment across team

---

## Quick Start

### For Ansible Projects (e.g., malpanez.security collection)

1. **Copy devcontainer configuration** to your project:

```bash
# In your ansible collection repository
mkdir -p .devcontainer
curl -o .devcontainer/devcontainer.json \
  https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/ansible-collection/.devcontainer/devcontainer.json
```

2. **Open in VS Code**:
```bash
code .
# VS Code will prompt: "Reopen in Container" → Click it
```

3. **Configure pre-commit** (auto-runs before commits):
```bash
# Already configured! Pre-commit hooks active:
# - ansible-lint
# - yamllint
# - Check for merge conflicts
# - Check for secrets
# - Trailing whitespace fixes
```

4. **Start working**:
```bash
# Test your collection
ansible-test sanity --docker default

# Run molecule tests
molecule test

# Lint automatically (runs on commit)
git commit -m "feat: add new role"
# Pre-commit runs automatically before commit
```

---

### For Terraform Projects

1. **Copy devcontainer configuration**:

```bash
mkdir -p .devcontainer
curl -o .devcontainer/devcontainer.json \
  https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.devcontainer/devcontainer.json
```

2. **Open in container** and start working:
```bash
# Initialize terraform
terraform init

# Plan (with pre-commit validation)
terraform plan

# Format check (auto-runs on commit)
terraform fmt

# Security scan (auto-runs on commit)
trivy config .
```

---

## Available DevContainers

### 1. Ansible Container (`ghcr.io/malpanez/devcontainer-ansible`)

**Best for**:
- Ansible collections
- Playbooks
- Roles development

**Tools included**:
- ansible-core (not the `ansible` package) with ansible-lint, yamllint, ansible-navigator and ansible-test
- `ansible.posix`, `community.general` and `community.docker` (see `devcontainers/ansible/collections.txt`); install any other collection from your `requirements.yml`
- Python + uv (versions in `uv.lock`)
- Pre-commit hooks
- `devcontainer-ansible-aws` adds `amazon.aws`, boto3 and AWS CLI v2

**VS Code Extensions**:
- Ansible (redhat.ansible)
- YAML (redhat.vscode-yaml)
- Jinja (samuelcolvin.jinjahtml)
- GitLens

### 2. Terraform Container (`ghcr.io/malpanez/devcontainer-terraform`)

**Best for**:
- Terraform modules
- Infrastructure provisioning
- Terragrunt projects

**Tools included**:
- Terraform, Terragrunt and TFLint (versions: `ARG *_VERSION` in `devcontainers/terraform/Dockerfile`)
- SOPS + age (secret management)
- Pre-commit hooks
- No `aws` command: `devcontainer-terraform-aws` adds AWS CLI v2

**VS Code Extensions**:
- HashiCorp Terraform
- TFLint
- Checkov

### 3. Combined (Ansible + Terraform)

**Best for**:
- Mixed infrastructure projects
- Configuration management + provisioning
- Full stack IaC

Use the terraform container - it includes both toolsets.

---

## Configuration Examples

Both examples pin the image to a release version tag plus that tag's index
digest (`<image>:vX.Y.Z@sha256:…`), as the templates in this repository do, so
the container opens on exactly the image that release shipped. Pin a version
tag, not `latest`: the nightly rebuild moves `latest` (and `main`) every day,
and the registry cleanup deletes the digest it leaves untagged two weeks later,
so a `latest@sha256:…` pin stops pulling. Version tags are never rebuilt, moved
or deleted. To follow new releases in your project, let Renovate's
`devcontainer` manager update `.devcontainer/devcontainer.json`; it moves the
tag and the digest together. In this repository Renovate bumps the templates,
`examples/` and the pins on this page after each release. To look a digest up
yourself, run
`docker buildx imagetools inspect ghcr.io/malpanez/devcontainer-<stack>:vX.Y.Z`
and take its `Digest:` line.

### Example 1: Ansible Collection (Recommended Configuration)

**.devcontainer/devcontainer.json**:
```json
{
  "name": "Ansible Development",
  "image": "ghcr.io/malpanez/devcontainer-ansible:v2.0.0@sha256:9c1cccfe57b8cd90523f3dd18c13bda794791cc907b7d31b7f20dfa399489959",
  "remoteUser": "vscode",

  "customizations": {
    "vscode": {
      "extensions": [
        "redhat.ansible",
        "redhat.vscode-yaml",
        "ms-python.python",
        "charliermarsh.ruff"
      ],
      "settings": {
        "ansible.python.interpreterPath": "/usr/local/bin/python",
        "ansible.validation.enabled": true,
        "ansible.validation.lint.enabled": true,
        "ansible.validation.lint.path": "/usr/local/bin/ansible-lint"
      }
    }
  },

  "postCreateCommand": "uvx pre-commit install --install-hooks && ansible-galaxy collection install -r requirements.yml || true",

  "workspaceFolder": "/workspace",
  "workspaceMount": "source=${localWorkspaceFolder},target=/workspace,type=bind"
}
```

**Pre-commit configuration** (.pre-commit-config.yaml):
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/ansible/ansible-lint
    rev: v24.12.3
    hooks:
      - id: ansible-lint
        args: [--fix]

  - repo: https://github.com/adrienverge/yamllint
    rev: v1.37.1
    hooks:
      - id: yamllint
        args: [-c, .yamllint.yml]
```

**Workflow**:
```bash
# 1. Open in VS Code (reopens in container)
code .

# 2. Install collection dependencies
ansible-galaxy collection install -r requirements.yml

# 3. Develop your role/plugin
vim roles/security_hardening/tasks/main.yml

# 4. Test locally
molecule test

# 5. Commit (pre-commit runs automatically)
git add roles/security_hardening/
git commit -m "feat(security): add CIS benchmarks compliance"
# → ansible-lint runs automatically
# → yamllint runs automatically
# → All checks pass → Commit succeeds

# 6. Push and create PR
git push origin feature/cis-benchmarks
gh pr create
```

---

### Example 2: Terraform Module

**.devcontainer/devcontainer.json**:
```json
{
  "name": "Terraform AWS Security Module",
  "image": "ghcr.io/malpanez/devcontainer-terraform:v2.0.0@sha256:2149339e017c5cbf5d80aecf796d7945c0ad85bd3fbc900c215b40ff32e6607f",

  "customizations": {
    "vscode": {
      "settings": {
        "terraform.languageServer.enable": true,
        "terraform.codelens.enabled": true
      },
      "extensions": [
        "hashicorp.terraform",
        "tfsec.tfsec",
        "checkov.checkov"
      ]
    }
  },

  // ~/.aws must exist on the host, or the container will not start.
  "mounts": [
    "source=${localEnv:HOME}/.aws,target=/home/vscode/.aws,type=bind,readonly",
    "source=${localEnv:HOME}/.ssh,target=/home/vscode/.ssh,type=bind,readonly"
  ],

  "postCreateCommand": "pre-commit install && terraform init",

  "remoteUser": "vscode"
}
```

**Pre-commit configuration** (.pre-commit-config.yaml):
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-merge-conflict

  - repo: https://github.com/antonbabenko/pre-commit-terraform
    rev: v1.102.0
    hooks:
      - id: terraform_fmt
      - id: terraform_validate
      - id: terraform_docs
      - id: terraform_tflint
      - id: terraform_trivy

  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.23.1
    hooks:
      - id: gitleaks
```

**Workflow**:
```bash
# 1. Open in container
code .

# 2. Initialize
terraform init

# 3. Develop module
vim main.tf

# 4. Validate and plan
terraform validate
terraform plan

# 5. Commit (pre-commit runs automatically)
git add main.tf
git commit -m "feat(aws): add security group hardening"
# → terraform fmt runs automatically
# → terraform validate runs automatically
# → tflint runs automatically
# → trivy security scan runs automatically
# → All checks pass → Commit succeeds

# 6. Push
git push
```

---

## Pre-commit Hooks Explained

### What Gets Checked Automatically

**Before EVERY commit**:
1. ✅ Formatting (terraform fmt, yamllint)
2. ✅ Linting (ansible-lint, tflint)
3. ✅ Security (trivy, gitleaks, detect-private-key)
4. ✅ Validation (terraform validate, yaml syntax)
5. ✅ Trailing whitespace, EOF newlines

**If checks fail**:
- Commit is blocked
- You see which checks failed
- Fix the issues and commit again

**Benefits**:
- Catch errors before pushing
- Maintain code quality
- Prevent security leaks
- Fast feedback loop

### Bypass Pre-commit (NOT recommended)

```bash
# Only for emergencies
git commit --no-verify -m "emergency fix"
```

---

## Features Comparison

| Feature | Official Ansible | Official Terraform | Our Containers |
|---------|-----------------|-------------------|----------------|
| Python Version | 3.11 | N/A | 3.12.12 (latest) |
| Package Manager | pip | N/A | uv (10-100x faster) |
| Pre-commit Configured | ❌ No | ❌ No | ✅ Yes |
| Security Tools | ❌ Basic | ❌ None | ✅ Trivy, SOPS, age |
| Multi-arch Support | ⚠️ Limited | ⚠️ Limited | ✅ amd64/arm64 |
| Build Cache | ❌ No | ❌ No | ✅ Yes (faster rebuilds) |
| OpenSSF Scorecard | N/A | N/A | ✅ 6.1/10 |
| Dependencies Pinned | ❌ No | ❌ No | ✅ Yes (SHA256) |
| Auto-updates | ❌ Manual | ❌ Manual | ✅ Renovate bot |
| Maintenance Docs | ❌ No | ❌ No | ✅ Yes |

---

## Advanced Configuration

### Mount SSH Keys

```json
{
  "mounts": [
    "source=${localEnv:HOME}/.ssh,target=/home/vscode/.ssh,type=bind,readonly"
  ]
}
```

### Mount AWS Credentials

Needs an image with the AWS CLI (`devcontainer-terraform-aws` or `devcontainer-ansible-aws`), and `~/.aws` must exist on the host or the container will not start. The `devcontainer.aws.json` templates mount nothing by default and log in inside the container instead.

```json
{
  "mounts": [
    "source=${localEnv:HOME}/.aws,target=/home/vscode/.aws,type=bind,readonly"
  ]
}
```

### Custom Environment Variables

```json
{
  "containerEnv": {
    "ANSIBLE_CONFIG": "${containerWorkspaceFolder}/ansible.cfg",
    "TF_LOG": "INFO"
  }
}
```

### Add Extra Features

```json
{
  "features": {
    "ghcr.io/devcontainers/features/docker-in-docker:2": { "moby": false },
    "ghcr.io/devcontainers/features/kubectl-helm-minikube:1": {}
  }
}
```

---

## Troubleshooting

### Container Won't Start

**Issue**: Container fails to build or start

**Solutions**:
1. Check Docker is running: `docker ps`
2. Pull latest image: `docker pull ghcr.io/malpanez/devcontainer-ansible:latest`
3. Rebuild container: VS Code → Command Palette → "Rebuild Container"
4. Check Docker logs: `docker logs <container-id>`

### Pre-commit Hooks Not Running

**Issue**: Commits don't trigger pre-commit checks

**Solutions**:
1. Install hooks: `pre-commit install`
2. Check installation: `pre-commit run --all-files`
3. Verify .pre-commit-config.yaml exists
4. Update hooks: `pre-commit autoupdate`

### Slow Performance

**Issue**: Container is slow to start or run commands

**Solutions**:
1. Increase Docker resources (Settings → Resources)
2. Use volumes instead of bind mounts
3. Disable unnecessary VS Code extensions
4. Prune Docker: `docker system prune -a`

---

## Templates

Ready-to-use templates available in `/examples`:

1. **Ansible Collection**: `examples/ansible-collection/`
2. **Terraform Module**: `examples/terraform-project/`
3. **Mixed IaC Project**: `examples/mixed-iac/`

Copy and customize for your project.

---

## CI/CD Integration

These containers work great in CI/CD:

### GitHub Actions

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    container:
      image: ghcr.io/malpanez/devcontainer-ansible:latest
    steps:
      - uses: actions/checkout@v4
      - run: pre-commit run --all-files
      - run: ansible-lint
      - run: molecule test
```

### GitLab CI

```yaml
lint:
  image: ghcr.io/malpanez/devcontainer-ansible:latest
  script:
    - pre-commit run --all-files
    - ansible-lint
    - molecule test
```

---

## Getting Help

**Documentation**:
- [MAINTENANCE.md](MAINTENANCE.md) - Maintenance procedures
- [SECURITY.md](SECURITY.md) - Security policies
- [README.md](README.md) - Container details

**Support**:
- Create issue: https://github.com/malpanez/ansible-devcontainer-vscode/issues
- Discussions: https://github.com/malpanez/ansible-devcontainer-vscode/discussions

**Image Registry**:
- Ansible: ghcr.io/malpanez/devcontainer-ansible:latest
- Terraform: ghcr.io/malpanez/devcontainer-terraform:latest
- All tags: https://github.com/malpanez/ansible-devcontainer-vscode/pkgs/container/devcontainer-ansible

---

## Summary: Why Switch?

**Before** (official containers):
- ❌ Outdated tool versions
- ❌ Slow package installs (pip)
- ❌ No pre-commit configured
- ❌ Manual security checks
- ❌ Inconsistent environments

**After** (malpanez containers):
- ✅ Latest stable tools
- ✅ Fast builds (uv, caching)
- ✅ Automated quality checks
- ✅ Security built-in
- ✅ Consistent, documented, maintained

**Start now**: Copy `.devcontainer/devcontainer.json` → Open in VS Code → Start coding!
