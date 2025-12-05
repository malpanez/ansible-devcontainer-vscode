# DevContainer Integration Prompts

**Production-Ready DevContainers** - Copy-paste instructions for integrating malpanez devcontainers into your projects.

---

## 🎯 Quick Copy Commands

### For Ansible Collections

```bash
# One-line setup
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/ansible-collection/.devcontainer/devcontainer.json -o .devcontainer/devcontainer.json --create-dirs && \
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/ansible-collection/.pre-commit-config.yaml -o .pre-commit-config.yaml && \
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/ansible-collection/.yamllint.yml -o .yamllint.yml && \
echo "✅ DevContainer configured! Open in VS Code: code ."
```

### For Terraform Projects

```bash
# One-line setup
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.devcontainer/devcontainer.json -o .devcontainer/devcontainer.json --create-dirs && \
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.pre-commit-config.yaml -o .pre-commit-config.yaml && \
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.tflint.hcl -o .tflint.hcl && \
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.terraform-docs.yml -o .terraform-docs.yml && \
echo "✅ DevContainer configured! Open in VS Code: code ."
```

---

## 📝 Prompt for AI Assistants (Ansible)

```
I want to use production-ready devcontainers from malpanez/ansible-devcontainer-vscode for my Ansible collection/playbook project.

**Goal**: Set up development environment with:
- ✅ Ansible 9.14.0 + Python 3.12.12 + uv (10-100x faster than pip)
- ✅ Pre-commit hooks (ansible-lint, yamllint, gitleaks) - auto-configured
- ✅ VS Code extensions (Ansible, YAML, Jinja2, GitLens) - pre-configured
- ✅ Consistent environment across team
- ✅ Zero manual setup

**Why these containers are production-ready**:
- OpenSSF Scorecard: 6.1/10
- Pinned dependencies (SHA256)
- Automated updates (Renovate bot)
- Security scanning built-in
- 90% maintenance automated
- Multi-arch support (amd64/arm64)

**Setup instructions**:

```bash
# Option 1: One-line setup (recommended)
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/ansible-collection/.devcontainer/devcontainer.json -o .devcontainer/devcontainer.json --create-dirs && \
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/ansible-collection/.pre-commit-config.yaml -o .pre-commit-config.yaml && \
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/ansible-collection/.yamllint.yml -o .yamllint.yml

# Option 2: Manual download
mkdir -p .devcontainer
curl -L https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/ansible-collection/.devcontainer/devcontainer.json -o .devcontainer/devcontainer.json
curl -L https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/ansible-collection/.pre-commit-config.yaml -o .pre-commit-config.yaml
curl -L https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/ansible-collection/.yamllint.yml -o .yamllint.yml

# Open in VS Code
code .
# Click "Reopen in Container" when prompted
```

**What happens automatically**:
1. VS Code downloads `ghcr.io/malpanez/devcontainer-ansible:latest`
2. Container starts with Ansible 9.14.0 + Python 3.12.12
3. Pre-commit hooks install automatically
4. VS Code extensions configure automatically
5. SSH keys mount (read-only)
6. Ready to develop!

**Pre-commit hooks (run before EVERY commit)**:
- ✅ ansible-lint (with --fix) - validates tasks, auto-fixes issues
- ✅ yamllint - validates YAML syntax and style
- ✅ gitleaks - detects secrets/credentials
- ✅ check-yaml - ensures YAML parses correctly
- ✅ detect-private-key - prevents SSH key leaks
- ✅ trailing-whitespace - auto-fixes
- ✅ end-of-file-fixer - auto-fixes

**Development workflow**:
```bash
# Edit your role/plugin
vim roles/security/tasks/main.yml

# Test (if molecule configured)
molecule test

# Commit - pre-commit runs automatically
git add roles/security/
git commit -m "feat: add CIS compliance role"

# Pre-commit output:
# ansible-lint........................................Passed
# yamllint............................................Passed
# gitleaks............................................Passed
# ✅ All checks passed - commit succeeds!

# Push
git push
```

**Bypass pre-commit (emergencies only)**:
```bash
git commit --no-verify -m "emergency hotfix"
```

**Manual check**:
```bash
pre-commit run --all-files
```

**Documentation**:
- Full guide: https://github.com/malpanez/ansible-devcontainer-vscode/blob/main/INTEGRATION_GUIDE.md
- Examples: https://github.com/malpanez/ansible-devcontainer-vscode/tree/main/examples
- Maintenance: https://github.com/malpanez/ansible-devcontainer-vscode/blob/main/MAINTENANCE.md

Please guide me through:
1. Verifying the setup worked correctly
2. Testing pre-commit hooks
3. Understanding what each hook does
4. Customizing for my specific project needs
```

---

## 📝 Prompt for AI Assistants (Terraform)

```
I want to use production-ready devcontainers from malpanez/ansible-devcontainer-vscode for my Terraform/Terragrunt project.

**Goal**: Set up development environment with:
- ✅ Terraform 1.14.0 + Terragrunt 0.93.11 + TFLint 0.60.0
- ✅ Pre-commit hooks (terraform fmt, validate, tflint, trivy, terraform-docs) - auto-configured
- ✅ VS Code extensions (Terraform, GitLens) - pre-configured
- ✅ Security scanning (Trivy, gitleaks) - built-in
- ✅ Secret management (SOPS + age) - included
- ✅ AWS CLI - pre-installed
- ✅ Consistent environment across team
- ✅ Zero manual setup

**Why these containers are production-ready**:
- OpenSSF Scorecard: 6.1/10
- Pinned dependencies (SHA256)
- Automated updates (Renovate bot)
- Security scanning built-in
- 90% maintenance automated
- Multi-arch support (amd64/arm64)

**Setup instructions**:

```bash
# Option 1: One-line setup (recommended)
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.devcontainer/devcontainer.json -o .devcontainer/devcontainer.json --create-dirs && \
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.pre-commit-config.yaml -o .pre-commit-config.yaml && \
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.tflint.hcl -o .tflint.hcl && \
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.terraform-docs.yml -o .terraform-docs.yml

# Option 2: Manual download
mkdir -p .devcontainer
curl -L https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.devcontainer/devcontainer.json -o .devcontainer/devcontainer.json
curl -L https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.pre-commit-config.yaml -o .pre-commit-config.yaml
curl -L https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.tflint.hcl -o .tflint.hcl
curl -L https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.terraform-docs.yml -o .terraform-docs.yml

# Open in VS Code
code .
# Click "Reopen in Container" when prompted
```

**What happens automatically**:
1. VS Code downloads `ghcr.io/malpanez/devcontainer-terraform:latest`
2. Container starts with Terraform 1.14.0 + Terragrunt 0.93.11
3. AWS credentials mount (read-only from ~/.aws)
4. SSH keys mount (read-only from ~/.ssh)
5. Pre-commit hooks install automatically
6. `terraform init` runs automatically
7. VS Code extensions configure automatically
8. Ready to develop!

**Pre-commit hooks (run before EVERY commit)**:
- ✅ terraform fmt - auto-formats code
- ✅ terraform validate - validates HCL syntax
- ✅ terraform-docs - auto-updates README.md
- ✅ tflint - AWS best practices linting
- ✅ trivy - security scan (CRITICAL/HIGH only)
- ✅ gitleaks - detects secrets/credentials
- ✅ check-yaml - validates YAML syntax
- ✅ detect-private-key - prevents SSH key leaks
- ✅ trailing-whitespace - auto-fixes
- ✅ end-of-file-fixer - auto-fixes

**Development workflow**:
```bash
# Initialize (already done automatically)
terraform init

# Edit module
vim main.tf

# Plan
terraform plan

# Commit - pre-commit runs automatically
git add main.tf
git commit -m "feat: add VPC security group"

# Pre-commit output:
# Terraform fmt.......................................Passed
# Terraform validate..................................Passed
# Terraform docs......................................Passed
# Terraform validate with tflint......................Passed
# Terraform validate with trivy.......................Passed
# Detect secrets......................................Passed
# ✅ All checks passed - commit succeeds!

# Push
git push
```

**terraform-docs auto-updates README.md**:
Add this to your README.md:
```markdown
<!-- BEGIN_TF_DOCS -->
<!-- terraform-docs will insert documentation here automatically -->
<!-- END_TF_DOCS -->
```

**Secret management with SOPS**:
```bash
# Generate age key (first time)
age-keygen -o ~/.age/key.txt

# Encrypt sensitive file
export SOPS_AGE_KEY_FILE=~/.age/key.txt
sops --encrypt --age $(age-keygen -y ~/.age/key.txt) terraform.tfvars > terraform.tfvars.enc

# Edit encrypted file
sops terraform.tfvars.enc

# Decrypt for use
sops --decrypt terraform.tfvars.enc > terraform.tfvars
```

**TFLint configuration**:
Default: AWS ruleset
For Azure: Add to `.tflint.hcl`:
```hcl
plugin "azurerm" {
  enabled = true
  version = "0.30.0"
  source  = "github.com/terraform-linters/tflint-ruleset-azurerm"
}
```

**Bypass pre-commit (emergencies only)**:
```bash
# Skip all checks
git commit --no-verify -m "emergency hotfix"

# Skip trivy only (if slow)
SKIP=terraform_trivy git commit -m "feat: add module"
```

**Manual check**:
```bash
pre-commit run --all-files
```

**Documentation**:
- Full guide: https://github.com/malpanez/ansible-devcontainer-vscode/blob/main/INTEGRATION_GUIDE.md
- Examples: https://github.com/malpanez/ansible-devcontainer-vscode/tree/main/examples
- Maintenance: https://github.com/malpanez/ansible-devcontainer-vscode/blob/main/MAINTENANCE.md

Please guide me through:
1. Verifying the setup worked correctly
2. Testing pre-commit hooks
3. Understanding terraform-docs auto-generation
4. Using SOPS for secret encryption
5. Customizing TFLint for my cloud provider
6. Optimizing Trivy performance
```

---

## 🎓 For Team Onboarding

### Ansible Team Onboarding Message

```
Welcome to the team! 👋

We use **production-ready devcontainers** for consistent development environments.

**Setup (2 minutes)**:

1. Install Docker Desktop + VS Code
2. Clone the repository
3. Run setup:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/ansible-collection/.devcontainer/devcontainer.json -o .devcontainer/devcontainer.json --create-dirs && \
   curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/ansible-collection/.pre-commit-config.yaml -o .pre-commit-config.yaml && \
   curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/ansible-collection/.yamllint.yml -o .yamllint.yml
   ```
4. Open in VS Code: `code .`
5. Click "Reopen in Container"
6. Start coding!

**What you get**:
- ✅ Ansible 9.14.0 + Python 3.12.12
- ✅ Pre-commit hooks (ansible-lint, yamllint, gitleaks)
- ✅ VS Code extensions configured
- ✅ Same environment as entire team

**Pre-commit hooks run automatically** before every commit:
- ansible-lint validates your playbooks/roles
- yamllint checks YAML formatting
- gitleaks prevents credential leaks

**Your first commit**:
```bash
vim roles/example/tasks/main.yml
git add roles/example/
git commit -m "feat: my first change"
# Pre-commit runs automatically!
```

**Need help?** Check:
- [Integration Guide](https://github.com/malpanez/ansible-devcontainer-vscode/blob/main/INTEGRATION_GUIDE.md)
- [Examples](https://github.com/malpanez/ansible-devcontainer-vscode/tree/main/examples)
- Ask the team in Slack/Discord
```

### Terraform Team Onboarding Message

```
Welcome to the team! 👋

We use **production-ready devcontainers** for consistent Terraform development.

**Setup (2 minutes)**:

1. Install Docker Desktop + VS Code
2. Clone the repository
3. Run setup:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.devcontainer/devcontainer.json -o .devcontainer/devcontainer.json --create-dirs && \
   curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.pre-commit-config.yaml -o .pre-commit-config.yaml && \
   curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.tflint.hcl -o .tflint.hcl && \
   curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.terraform-docs.yml -o .terraform-docs.yml
   ```
4. Open in VS Code: `code .`
5. Click "Reopen in Container"
6. Start coding!

**What you get**:
- ✅ Terraform 1.14.0 + Terragrunt 0.93.11 + TFLint 0.60.0
- ✅ Pre-commit hooks (fmt, validate, tflint, trivy, terraform-docs)
- ✅ VS Code Terraform extension
- ✅ AWS CLI configured
- ✅ SOPS + age for secrets
- ✅ Same environment as entire team

**Pre-commit hooks run automatically** before every commit:
- terraform fmt auto-formats
- terraform validate checks syntax
- terraform-docs updates README.md
- tflint enforces best practices
- trivy scans for security issues

**Your first commit**:
```bash
vim main.tf
git add main.tf
git commit -m "feat: my first module"
# Pre-commit runs automatically!
```

**Need help?** Check:
- [Integration Guide](https://github.com/malpanez/ansible-devcontainer-vscode/blob/main/INTEGRATION_GUIDE.md)
- [Examples](https://github.com/malpanez/ansible-devcontainer-vscode/tree/main/examples)
- Ask the team in Slack/Discord
```

---

## 🔧 Troubleshooting Prompts

### "Pre-commit hooks not running"

```bash
# Reinstall hooks
pre-commit install --install-hooks

# Test manually
pre-commit run --all-files

# Update hooks
pre-commit autoupdate
```

### "Container won't start"

```bash
# Pull latest image
docker pull ghcr.io/malpanez/devcontainer-ansible:latest
# or
docker pull ghcr.io/malpanez/devcontainer-terraform:latest

# Rebuild container
# VS Code: Ctrl+Shift+P → "Dev Containers: Rebuild Container"
```

### "Slow performance"

```bash
# Increase Docker resources
# Docker Desktop → Settings → Resources → Memory: 8GB, CPU: 4 cores

# Clean up
docker system prune -a --volumes
```

---

## 📊 Production-Ready Metrics

**OpenSSF Scorecard**: 6.1/10
- ✅ Vulnerabilities: 10/10
- ✅ Security-Policy: 10/10
- ✅ Dependency-Update-Tool: 10/10
- ✅ CI-Tests: 10/10
- ✅ Binary-Artifacts: 10/10
- ✅ License: 10/10
- ✅ Packaging: 10/10

**Automation Coverage**: 90%
- ✅ Dependency updates (Renovate)
- ✅ Security alerts (weekly cleanup)
- ✅ Quality checks (pre-commit + CI)
- ✅ Branch sync (main→develop)

**Maintenance Schedule**:
- Daily: 0 min (automated)
- Weekly: 5 min (review automation)
- Monthly: 15 min (health check)
- Quarterly: 2 hours (comprehensive review)

---

## 📚 Additional Resources

- **Integration Guide**: [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)
- **Maintenance Guide**: [MAINTENANCE.md](MAINTENANCE.md)
- **Examples**: [examples/](examples/)
- **Security Review**: [SECURITY_REVIEW.md](SECURITY_REVIEW.md)
- **OpenSSF Progress**: [OSSF_SCORECARD_PROGRESS.md](OSSF_SCORECARD_PROGRESS.md)

---

**Container Images**:
- Ansible: `ghcr.io/malpanez/devcontainer-ansible:latest`
- Terraform: `ghcr.io/malpanez/devcontainer-terraform:latest`

**Repository**: https://github.com/malpanez/ansible-devcontainer-vscode
