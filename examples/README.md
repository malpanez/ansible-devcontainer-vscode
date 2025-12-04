# DevContainer Integration Examples

Ready-to-use templates for integrating malpanez devcontainers into your projects.

---

## Available Templates

### 1. [Ansible Collection](ansible-collection/)

**Best for**: Ansible collections, roles, playbooks

**What's included**:
- Pre-configured devcontainer.json
- Pre-commit hooks (ansible-lint, yamllint, gitleaks)
- VS Code extensions (Ansible, YAML, Jinja)
- Example .yamllint.yml configuration

**Copy to your project**:
```bash
cp -r examples/ansible-collection/.devcontainer /path/to/your/collection/
cp examples/ansible-collection/.pre-commit-config.yaml /path/to/your/collection/
cp examples/ansible-collection/.yamllint.yml /path/to/your/collection/
```

### 2. [Terraform Project](terraform-project/)

**Best for**: Terraform modules, Terragrunt projects, infrastructure provisioning

**What's included**:
- Pre-configured devcontainer.json
- Pre-commit hooks (terraform fmt, validate, tflint, trivy)
- TFLint configuration (.tflint.hcl)
- terraform-docs configuration (.terraform-docs.yml)
- AWS CLI integration

**Copy to your project**:
```bash
cp -r examples/terraform-project/.devcontainer /path/to/your/module/
cp examples/terraform-project/.pre-commit-config.yaml /path/to/your/module/
cp examples/terraform-project/.tflint.hcl /path/to/your/module/
cp examples/terraform-project/.terraform-docs.yml /path/to/your/module/
```

### 3. Mixed IaC Project (Coming Soon)

**Best for**: Projects using both Ansible + Terraform

---

## Quick Start

1. **Choose your template** above
2. **Copy files** to your project
3. **Open in VS Code**:
   ```bash
   code /path/to/your/project
   # VS Code will prompt "Reopen in Container" → Click it
   ```
4. **Start coding** - pre-commit hooks are auto-configured!

---

## What You Get

### Automatic Quality Checks

Every template includes pre-commit hooks that run **before every commit**:

**Ansible**:
- ✅ ansible-lint (with auto-fix)
- ✅ yamllint
- ✅ YAML syntax validation
- ✅ Secret detection
- ✅ Formatting fixes

**Terraform**:
- ✅ terraform fmt (auto-format)
- ✅ terraform validate
- ✅ terraform-docs (auto-updates README)
- ✅ tflint
- ✅ trivy security scan
- ✅ Secret detection

### VS Code Integration

**Ansible**:
- Syntax highlighting
- IntelliSense for modules
- Jinja2 template support
- YAML validation
- GitLens

**Terraform**:
- Terraform language server
- Auto-completion
- Format on save
- Syntax validation
- Resource navigation

### Credential Management

All templates mount your credentials **read-only**:
- SSH keys (`~/.ssh`)
- AWS credentials (`~/.aws`) - Terraform only
- No credentials stored in container

---

## Customization

### Add More VS Code Extensions

Edit `.devcontainer/devcontainer.json`:

```json
{
  "customizations": {
    "vscode": {
      "extensions": [
        "your-extension-id-here"
      ]
    }
  }
}
```

### Mount Additional Directories

```json
{
  "mounts": [
    "source=${localEnv:HOME}/.kube,target=/home/vscode/.kube,type=bind,readonly"
  ]
}
```

### Add Docker Features

```json
{
  "features": {
    "ghcr.io/devcontainers/features/docker-in-docker:2": {},
    "ghcr.io/devcontainers/features/kubectl-helm-minikube:1": {}
  }
}
```

### Environment Variables

```json
{
  "containerEnv": {
    "ANSIBLE_CONFIG": "${containerWorkspaceFolder}/ansible.cfg",
    "TF_LOG": "INFO"
  }
}
```

---

## Workflow Example

### Ansible Collection Development

```bash
# 1. Copy template
cp -r examples/ansible-collection/.devcontainer ./

# 2. Open in VS Code (reopens in container)
code .

# 3. Develop your role
vim roles/security/tasks/main.yml

# 4. Test locally
molecule test

# 5. Commit (pre-commit runs automatically)
git add roles/security/
git commit -m "feat: add CIS benchmarks"

# Pre-commit output:
# Check Yaml..........................................Passed
# ansible-lint........................................Passed
# yamllint............................................Passed
# Detect Private Key..................................Passed

# 6. Push
git push
```

### Terraform Module Development

```bash
# 1. Copy template
cp -r examples/terraform-project/.devcontainer ./

# 2. Open in VS Code (reopens in container)
code .

# 3. Initialize
terraform init

# 4. Develop module
vim main.tf

# 5. Plan
terraform plan

# 6. Commit (pre-commit runs automatically)
git add main.tf
git commit -m "feat: add security group module"

# Pre-commit output:
# Terraform fmt.......................................Passed
# Terraform validate..................................Passed
# Terraform docs......................................Passed
# Terraform validate with tflint......................Passed
# Terraform validate with trivy.......................Passed

# 7. Push
git push
```

---

## Troubleshooting

### Pre-commit Hooks Not Running

```bash
# Reinstall hooks
pre-commit install --install-hooks

# Test manually
pre-commit run --all-files
```

### Container Build Fails

```bash
# Pull latest image
docker pull ghcr.io/malpanez/devcontainer-ansible:latest
docker pull ghcr.io/malpanez/devcontainer-terraform:latest

# Rebuild container
# VS Code: Command Palette → "Rebuild Container"
```

### Slow Performance

```bash
# Increase Docker resources
# Docker Desktop → Settings → Resources → Memory/CPU

# Clear cache
docker system prune -a
```

### Want to Bypass Pre-commit (Emergency Only)

```bash
git commit --no-verify -m "emergency fix"
```

---

## Advanced Examples

### CI/CD Integration

Use these containers in GitHub Actions:

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
```

### Terraform with Multiple Cloud Providers

Add Azure and GCP features:

```json
{
  "features": {
    "ghcr.io/devcontainers/features/azure-cli:1": {},
    "ghcr.io/devcontainers/features/gcp-cli:1": {}
  }
}
```

---

## Need Help?

- **Documentation**: [INTEGRATION_GUIDE.md](../INTEGRATION_GUIDE.md)
- **Issues**: https://github.com/malpanez/ansible-devcontainer-vscode/issues
- **Discussions**: https://github.com/malpanez/ansible-devcontainer-vscode/discussions

---

## Why These Templates?

**Superior to official containers**:
- ✅ Latest stable tool versions
- ✅ 10-100x faster package installs (uv vs pip)
- ✅ Pre-commit configured out-of-the-box
- ✅ Security scanning built-in
- ✅ Multi-arch support (amd64/arm64)
- ✅ Actively maintained
- ✅ OpenSSF Scorecard: 6.1/10

**Start now**: Copy a template → Open in VS Code → Start coding!
