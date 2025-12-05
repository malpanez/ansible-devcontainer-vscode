# Scripts Documentation

This directory contains automation scripts for managing devcontainer stacks, running tests, and maintaining the repository.

## Table of Contents

- [Overview](#overview)
- [Stack Management](#stack-management)
- [Testing Scripts](#testing-scripts)
- [Container Management](#container-management)
- [Python Utilities](#python-utilities)
- [Windows Bootstrap](#windows-bootstrap)
- [Scenarios](#scenarios)
- [Usage Examples](#usage-examples)

---

## Overview

All scripts are designed to be run from the repository root or directly via their paths. Shell scripts use `set -euo pipefail` for safety and support `--help` for usage information.

### Quick Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| [use-devcontainer.sh](#use-devcontainersh) | Switch between devcontainer stacks | `./scripts/use-devcontainer.sh ansible` |
| [run-smoke-tests.sh](#run-smoke-testssh) | Run Ansible smoke tests | `./scripts/run-smoke-tests.sh` |
| [run-terraform-tests.sh](#run-terraform-testssh) | Run Terraform validation tests | `./scripts/run-terraform-tests.sh` |
| [run-ansible-tests.sh](#run-ansible-testssh) | Run Ansible tests with Molecule | `./scripts/run-ansible-tests.sh` |
| [cleanup-merged-branches.sh](#cleanup-merged-branchessh) | Clean up merged Git branches | `./scripts/cleanup-merged-branches.sh --dry-run` |
| [smoke-devcontainer-image.sh](#smoke-devcontainer-imagesh) | Test devcontainer images | `./scripts/smoke-devcontainer-image.sh ansible` |
| [bootstrap-windows.ps1](#bootstrap-windowsps1) | Bootstrap Windows environment | `.\scripts\bootstrap-windows.ps1` |

---

## Stack Management

### use-devcontainer.sh

Switches between devcontainer stacks (Ansible, Terraform, Golang, LaTeX).

**Features:**
- Copies selected stack template to `.devcontainer/`
- Creates metadata file for tracking
- Optional cleanup with `--prune` flag
- Supports both Docker and Podman

**Usage:**
```bash
# Switch to Ansible stack (default)
./scripts/use-devcontainer.sh ansible

# Switch to Terraform stack
./scripts/use-devcontainer.sh terraform

# Switch with cleanup
./scripts/use-devcontainer.sh --prune golang

# Show help
./scripts/use-devcontainer.sh --help
```

**Options:**
- `-p, --prune`: Remove stopped containers and volumes
- `-h, --help`: Show usage information

**Available stacks:**
- `ansible` - Ansible automation stack (Python 3.12, uv, Ansible)
- `terraform` - Infrastructure as Code stack (Terraform, Terragrunt, TFLint)
- `golang` - Go development stack (Go 1.23, Alpine-based)
- `latex` - LaTeX document preparation (Tectonic, Perl)

**After switching:**
1. Reopen VS Code (`code .`)
2. Select "Dev Containers: Reopen in Container"
3. VS Code will rebuild with the new stack

---

### use-devcontainer.ps1

PowerShell version of the stack switcher for Windows users.

**Usage:**
```powershell
# Switch to Terraform stack
.\scripts\use-devcontainer.ps1 -Stack terraform

# Show help
.\scripts\use-devcontainer.ps1 -Help
```

---

## Testing Scripts

### run-smoke-tests.sh

Runs the Ansible environment smoke test playbook to verify toolchain installation.

**What it tests:**
- Python and uv availability
- Ansible installation and collections
- Git configuration
- SSH setup
- Docker/Podman availability

**Usage:**
```bash
# Run smoke tests
./scripts/run-smoke-tests.sh

# Run with extra verbosity
./scripts/run-smoke-tests.sh -vvv

# Check specific tags
./scripts/run-smoke-tests.sh --tags docker
```

**Exit codes:**
- `0` - All tests passed
- Non-zero - One or more tests failed

**Behind the scenes:**
Executes `ansible-playbook playbooks/test-environment.yml`

---

### run-terraform-tests.sh

Runs Terraform validation tests across all `.tf` files in the repository.

**What it tests:**
- `terraform fmt -check` (formatting)
- `terraform validate` (syntax and configuration)
- `terraform init` (provider initialization)

**Usage:**
```bash
# Run all Terraform tests
./scripts/run-terraform-tests.sh

# Run from specific directory
cd infrastructure/proxmox
../../scripts/run-terraform-tests.sh
```

**Directory scanning:**
- Automatically finds all directories with `*.tf` files
- Skips `.terraform/` cache directories
- Runs tests in parallel where possible

---

### run-ansible-tests.sh

Runs Ansible tests using Molecule for role testing.

**What it tests:**
- Role syntax validation
- Molecule scenarios (default, latex, etc.)
- Integration tests with Docker containers

**Usage:**
```bash
# Run default Molecule scenario
./scripts/run-ansible-tests.sh

# Run specific scenario
./scripts/run-ansible-tests.sh --scenario-name latex

# Debug mode
./scripts/run-ansible-tests.sh --debug
```

**Requirements:**
- Docker or Podman running
- Molecule installed (`pip install molecule molecule-plugins[docker]`)

**Environment variables:**
- `MOLECULE_DISTRO` - Test distribution (default: `debian12`)
- `MOLECULE_IMAGE` - Docker image to use

---

## Container Management

### smoke-devcontainer-image.sh

Tests devcontainer images for basic functionality.

**What it tests:**
- Container starts successfully
- Required tools are installed
- Shell is accessible
- User permissions are correct

**Usage:**
```bash
# Test Ansible image
./scripts/smoke-devcontainer-image.sh ansible

# Test all stacks
for stack in ansible terraform golang latex; do
  ./scripts/smoke-devcontainer-image.sh "$stack"
done

# Build and test
./scripts/smoke-devcontainer-image.sh --build ansible
```

**Options:**
- `--build` - Build the image before testing
- `--stack <name>` - Stack to test (ansible, terraform, golang, latex)

**Expected output:**
```
✓ Container starts
✓ Shell is available
✓ User is vscode
✓ Required tools installed
```

---

### check-devcontainer.sh

Validates devcontainer.json configuration files.

**What it checks:**
- JSON syntax validity
- Required fields present
- Feature compatibility
- Extension IDs

**Usage:**
```bash
# Check current .devcontainer
./scripts/check-devcontainer.sh

# Check specific stack
./scripts/check-devcontainer.sh devcontainers/terraform/devcontainer.json
```

---

### debug-devcontainer.sh

Debugging helper for devcontainer issues.

**What it shows:**
- Docker/Podman status
- Current devcontainer configuration
- Container logs
- Environment variables
- Volume mounts

**Usage:**
```bash
# Debug current environment
./scripts/debug-devcontainer.sh

# Save output to file
./scripts/debug-devcontainer.sh > debug-output.txt
```

**Useful for:**
- Container not starting
- Permission errors
- Missing tools
- Volume mount issues

---

### fix-dockerfiles.sh

Applies automated fixes to Dockerfiles.

**What it fixes:**
- Line ending issues (CRLF → LF)
- Trailing whitespace
- Missing newlines at EOF
- Common linting errors

**Usage:**
```bash
# Fix all Dockerfiles
./scripts/fix-dockerfiles.sh

# Dry run (show what would change)
./scripts/fix-dockerfiles.sh --dry-run

# Fix specific file
./scripts/fix-dockerfiles.sh devcontainers/ansible/Dockerfile
```

---

## Python Utilities

### devcontainer-metadata.py

Verifies that `.devcontainer/` matches the source template using SHA-256 signatures.

**Purpose:**
Ensures `.devcontainer/` hasn't drifted from its template source.

**Usage:**
```bash
# Verify current devcontainer
python3 scripts/devcontainer-metadata.py

# Check with custom paths
python3 scripts/devcontainer-metadata.py \
  --target .devcontainer \
  --templates devcontainers
```

**Exit codes:**
- `0` - Metadata matches (OK)
- `1` - Metadata file missing or invalid
- `2` - Template has changed (mismatch)

**Output:**
```
Stack: ansible
Signature: a1b2c3d4...
Status: OK
```

**Used by:**
- Pre-commit hooks
- CI validation
- Manual verification before committing `.devcontainer/`

---

### devcontainer-diff.py

Shows differences between `.devcontainer/` and the source template.

**Purpose:**
Helps identify local customizations or drift from the template.

**Usage:**
```bash
# Show diff for current stack
python3 scripts/devcontainer-diff.py --stack ansible

# Compare with specific template
python3 scripts/devcontainer-diff.py \
  --target .devcontainer \
  --templates devcontainers \
  --stack terraform
```

**Output:**
```diff
--- devcontainers/ansible/devcontainer.json
+++ .devcontainer/devcontainer.json
@@ -5,7 +5,7 @@
-  "image": "ghcr.io/..."
+  "build": { "dockerfile": "Dockerfile" }
```

**Exit codes:**
- `0` - No differences
- `2` - Differences found

---

## Windows Bootstrap

### bootstrap-windows.ps1

Automated setup script for Windows developers.

**What it installs:**
- WSL2 (Windows Subsystem for Linux)
- Ubuntu distribution
- Docker Desktop
- Visual Studio Code
- Git for Windows

**What it configures:**
- Corporate proxy settings (optional)
- WSL2 as default
- Docker WSL integration
- VS Code extensions (Dev Containers, Remote - WSL)

**Usage:**
```powershell
# Run as Administrator
.\scripts\bootstrap-windows.ps1

# With corporate proxy
.\scripts\bootstrap-windows.ps1 -Proxy "http://proxy.corp.com:8080"

# Skip Docker install
.\scripts\bootstrap-windows.ps1 -SkipDocker

# Dry run
.\scripts\bootstrap-windows.ps1 -WhatIf
```

**Requirements:**
- Windows 10/11 (version 2004+)
- Administrator privileges
- Internet connection

**Time to complete:** 15-30 minutes (includes reboots)

**See:** [docs/BOOTSTRAP_WINDOWS.md](../docs/BOOTSTRAP_WINDOWS.md) for detailed guide.

---

### bootstrap-wsl2.ps1

WSL2-specific bootstrap (subset of bootstrap-windows.ps1).

**Usage:**
```powershell
# Install and configure WSL2 only
.\scripts\bootstrap-wsl2.ps1
```

---

## Scenarios

The `scenarios/` subdirectory contains end-to-end workflow examples.

### run-latex-cv.sh

Generates a LaTeX CV using the Tectonic engine.

**Usage:**
```bash
# Run LaTeX CV example
./scripts/scenarios/run-latex-cv.sh
```

**What it does:**
1. Switches to LaTeX devcontainer
2. Compiles example CV from `examples/latex/cv/`
3. Outputs PDF to `build/cv.pdf`

---

### run-terraform-proxmox.sh

Runs Terraform plan for Proxmox infrastructure.

**Usage:**
```bash
# Run Terraform Proxmox example
./scripts/scenarios/run-terraform-proxmox.sh
```

**What it does:**
1. Switches to Terraform devcontainer
2. Initializes Terraform providers
3. Runs `terraform plan` for Proxmox setup
4. Shows infrastructure changes (no apply)

---

## Maintenance

### cleanup-merged-branches.sh

Cleans up Git branches that have been merged to `main` or `develop`.

**Features:**
- Dry-run mode (default)
- Interactive confirmation
- Protects important branches (`main`, `develop`, `master`)
- Cleans both local and remote branches

**Usage:**
```bash
# Dry run (show what would be deleted)
./scripts/cleanup-merged-branches.sh --dry-run

# Interactive mode
./scripts/cleanup-merged-branches.sh

# Force delete (skip confirmation)
./scripts/cleanup-merged-branches.sh --force
```

**Protected branches:**
- `main`
- `develop`
- `master`
- Current branch

**Output:**
```
🔍 Finding merged branches...

Local branches merged to main:
  - feat/old-feature (merged 5 days ago)
  - fix/bug-123 (merged 2 weeks ago)

Remote branches merged to main:
  - origin/chore/cleanup (merged 1 week ago)

Delete these branches? [y/N]
```

---

## Usage Examples

### Complete Development Workflow

```bash
# 1. Switch to Ansible stack
./scripts/use-devcontainer.sh ansible

# 2. Reopen in container (VS Code)
code .
# Select "Reopen in Container"

# 3. Run smoke tests
./scripts/run-smoke-tests.sh

# 4. Make changes...

# 5. Run full test suite
./scripts/run-ansible-tests.sh
./scripts/run-smoke-tests.sh

# 6. Clean up old branches
./scripts/cleanup-merged-branches.sh --dry-run
```

---

### CI/CD Pipeline Simulation

```bash
# Simulate what CI does
set -e

echo "Running smoke tests..."
./scripts/run-smoke-tests.sh

echo "Running Terraform validation..."
./scripts/run-terraform-tests.sh

echo "Running Ansible tests..."
./scripts/run-ansible-tests.sh

echo "Testing devcontainer builds..."
for stack in ansible terraform golang latex; do
  ./scripts/smoke-devcontainer-image.sh --build "$stack"
done

echo "✅ All checks passed!"
```

---

### Multi-Stack Development

```bash
# Work on Terraform, then switch to Golang
./scripts/use-devcontainer.sh terraform
# ... do Terraform work ...

./scripts/use-devcontainer.sh --prune golang
# --prune cleans up Terraform containers
# ... do Go work ...
```

---

### Debugging Container Issues

```bash
# Get detailed debug information
./scripts/debug-devcontainer.sh > debug.txt

# Check container configuration
./scripts/check-devcontainer.sh

# Verify template hasn't drifted
python3 scripts/devcontainer-metadata.py

# See what changed
python3 scripts/devcontainer-diff.py --stack ansible
```

---

## Common Issues

### "Permission denied" when running scripts

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Or run with bash explicitly
bash scripts/use-devcontainer.sh ansible
```

### Scripts not found when run from subdirectory

```bash
# Always run from repo root
cd /workspace
./scripts/run-smoke-tests.sh

# Or use absolute paths
/workspace/scripts/run-smoke-tests.sh
```

### Python scripts fail with "module not found"

```bash
# Ensure Python 3 is available
python3 --version

# Install dependencies
uv pip install --system -e .
```

### Windows scripts fail with "execution policy"

```powershell
# Allow script execution (as Administrator)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or run with bypass
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-windows.ps1
```

---

## Contributing

When adding new scripts:

1. **Use appropriate extension:**
   - `.sh` for shell scripts
   - `.py` for Python scripts
   - `.ps1` for PowerShell scripts

2. **Add usage documentation:**
   - Include `--help` flag
   - Document all options and arguments
   - Provide examples

3. **Follow conventions:**
   - Shell: `set -euo pipefail` at top
   - Python: Shebang `#!/usr/bin/env python3`
   - Use REPO_ROOT for path resolution

4. **Update this README:**
   - Add entry to Quick Reference table
   - Document in appropriate section
   - Include usage examples

5. **Add tests:**
   - Add test coverage in `tests/`
   - Include in CI workflow
   - Test on multiple platforms (Linux, macOS, Windows)

---

## Related Documentation

- [CONTRIBUTING.md](../docs/CONTRIBUTING.md) - Development workflow
- [ARCHITECTURE.md](../docs/ARCHITECTURE.md) - Project structure
- [VSCODE_WORKFLOW.md](../docs/VSCODE_WORKFLOW.md) - VS Code tasks and workflows
- [Makefile](../Makefile) - Universal task runner (calls many of these scripts)

---

**Questions or issues?** File an issue or check the [troubleshooting guide](../docs/TROUBLESHOOTING.md).
