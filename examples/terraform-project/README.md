# Terraform Project Example

This is a template for using malpanez devcontainers with your Terraform projects.

## 🤖 For AI Assistants / LLMs

**Want to use an LLM to set this up?** Copy the full prompt from [PROMPT_FOR_LLM.md](PROMPT_FOR_LLM.md) and paste it into Claude, ChatGPT, or any AI assistant.

The prompt includes:
- Complete setup instructions
- Explanation of pre-commit hooks (fmt, validate, tflint, trivy, terraform-docs)
- SOPS + age secret management guide
- TFLint customization for different cloud providers
- Why these containers are production-ready
- Comparison with official Terraform image
- How features work (pull vs build)

## ⚡ Performance Note

This template uses **direct pull** (no build) for maximum speed (~30 seconds).

**Why?** git, github-cli, and aws-cli are already in the base image, so we don't need DevContainer features that would trigger a rebuild (2-5 minutes).

**If you need additional tools** (Azure CLI, GCP CLI, Docker-in-Docker), see [DEVCONTAINER_FEATURES_EXPLAINED.md](../DEVCONTAINER_FEATURES_EXPLAINED.md) for how to add features.

**Example** (add to devcontainer.json for Azure):
```json
"features": {
  "ghcr.io/devcontainers/features/azure-cli:1": {}
}
```

**Alternative**: Use `devcontainer-fast.json` (identical to default, kept for reference).

## Quick Start

1. **Copy `.devcontainer/` to your project**:
   ```bash
   cp -r .devcontainer /path/to/your/terraform-project/
   ```

2. **Copy pre-commit config**:
   ```bash
   cp .pre-commit-config.yaml /path/to/your/terraform-project/
   cp .tflint.hcl /path/to/your/terraform-project/
   cp .terraform-docs.yml /path/to/your/terraform-project/
   ```

3. **Open in VS Code**:
   ```bash
   code /path/to/your/terraform-project
   # Click "Reopen in Container" when prompted
   ```

4. **Start developing**:
   ```bash
   # Pre-commit hooks are already installed
   # Edit your terraform files
   vim main.tf

   # Commit (pre-commit runs automatically)
   git add main.tf
   git commit -m "feat: add security group module"

   # Pre-commit will run:
   # - terraform fmt
   # - terraform validate
   # - terraform-docs (updates README)
   # - tflint
   # - trivy security scan
   # - gitleaks secret detection
   ```

## Features Enabled

- ✅ Terraform 1.14.0
- ✅ Terragrunt 0.93.11
- ✅ TFLint 0.60.0
- ✅ Trivy (security scanner)
- ✅ SOPS + age (secret management)
- ✅ AWS CLI configured
- ✅ Pre-commit hooks (auto-runs before commit)
- ✅ VS Code Terraform extension
- ✅ AWS/SSH credentials mounted (read-only)

## Pre-commit Checks

On every commit, these run automatically:
1. terraform fmt (auto-format)
2. terraform validate
3. terraform-docs (auto-updates README)
4. tflint (linting)
5. trivy (security scan for CRITICAL/HIGH)
6. gitleaks (secret detection)

## Development Workflow

```bash
# 1. Initialize
terraform init

# 2. Develop your module
vim main.tf

# 3. Plan
terraform plan

# 4. Commit (checks run automatically)
git commit -am "feat: add new resource"

# 5. If checks fail, fix and commit again
# terraform validate will show errors
# tflint will show warnings
# trivy will show security issues
```

## Security with SOPS

Encrypt sensitive files:

```bash
# Generate age key (first time only)
age-keygen -o key.txt

# Set SOPS to use age
export SOPS_AGE_KEY_FILE=key.txt

# Encrypt a file
sops --encrypt --age $(age-keygen -y key.txt) secrets.yaml > secrets.enc.yaml

# Decrypt when needed
sops --decrypt secrets.enc.yaml
```

## Customization

Edit `.devcontainer/devcontainer.json` to:
- Add Azure CLI: `"ghcr.io/devcontainers/features/azure-cli:1": {}`
- Add GCP CLI: `"ghcr.io/devcontainers/features/gcp-cli:1": {}`
- Mount more credentials
- Add more VS Code extensions

## Troubleshooting

**Pre-commit hooks not running?**
```bash
pre-commit install --install-hooks
```

**Want to run checks manually?**
```bash
pre-commit run --all-files
```

**Trivy scan too slow?**
```bash
# Skip trivy in pre-commit
SKIP=terraform_trivy git commit -m "message"
```

**Need to bypass checks (emergency only)?**
```bash
git commit --no-verify -m "emergency fix"
```

## TFLint Configuration

Customize `.tflint.hcl` for your cloud provider:

- AWS: Already configured
- Azure: Add `plugin "azurerm" { enabled = true }`
- GCP: Add `plugin "google" { enabled = true }`
