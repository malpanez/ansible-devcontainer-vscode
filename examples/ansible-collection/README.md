# Ansible Collection Example

This is a template for using malpanez devcontainers with your Ansible collection.

## Quick Start

1. **Copy `.devcontainer/` to your collection**:
   ```bash
   cp -r .devcontainer /path/to/your/collection/
   ```

2. **Copy pre-commit config**:
   ```bash
   cp .pre-commit-config.yaml /path/to/your/collection/
   cp .yamllint.yml /path/to/your/collection/
   ```

3. **Open in VS Code**:
   ```bash
   code /path/to/your/collection
   # Click "Reopen in Container" when prompted
   ```

4. **Start developing**:
   ```bash
   # Pre-commit hooks are already installed
   # Edit your roles/plugins
   vim roles/security/tasks/main.yml

   # Commit (pre-commit runs automatically)
   git add roles/security/
   git commit -m "feat: add security role"

   # Pre-commit will run:
   # - ansible-lint (with auto-fix)
   # - yamllint
   # - Security checks
   # - Formatting checks
   ```

## Features Enabled

- ✅ Ansible 9.14.0 (ansible-core 2.18.2)
- ✅ Python 3.12.12 with uv (fast package manager)
- ✅ ansible-lint, yamllint
- ✅ molecule, ansible-test
- ✅ Pre-commit hooks (auto-runs before commit)
- ✅ VS Code extensions configured
- ✅ SSH keys mounted (read-only)

## Pre-commit Checks

On every commit, these run automatically:
1. ansible-lint (with --fix)
2. yamllint
3. YAML syntax validation
4. Secret detection (gitleaks)
5. Trailing whitespace removal
6. EOF newline fixes

## Development Workflow

```bash
# 1. Develop your role/plugin
vim roles/my_role/tasks/main.yml

# 2. Test locally
molecule test

# 3. Commit (checks run automatically)
git commit -am "feat: add new role"

# 4. If checks fail, fix and commit again
# ansible-lint will show what needs fixing
```

## Customization

Edit `.devcontainer/devcontainer.json` to:
- Add more VS Code extensions
- Mount additional directories
- Set environment variables
- Add Docker features

## Troubleshooting

**Pre-commit hooks not running?**
```bash
pre-commit install --install-hooks
```

**Want to run checks manually?**
```bash
pre-commit run --all-files
```

**Need to bypass checks (emergency only)?**
```bash
git commit --no-verify -m "emergency fix"
```
