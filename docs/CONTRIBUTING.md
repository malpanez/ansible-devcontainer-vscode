# Contributing Guide

Thanks for helping to evolve the Ansible DevContainer! This document captures the day-to-day workflow so changes stay consistent, tested, and easy to review.

## First Time Contributing? 👋

Welcome! We're excited to have you. Here's how to get started:

1. **Find an issue to work on**:
   - Look for issues labeled [`good-first-issue`](https://github.com/malpanez/ansible-devcontainer-vscode/labels/good-first-issue)
   - Comment on the issue to let us know you're working on it
   - If you have questions, ask! We're here to help

2. **Quick workflow**:
   ```bash
   # Fork the repo on GitHub, then clone your fork
   git clone https://github.com/YOUR-USERNAME/ansible-devcontainer-vscode.git
   cd ansible-devcontainer-vscode

   # Open in VS Code and reopen in devcontainer
   code .

   # Make your changes, test them
   make test
   make lint

   # Commit and push
   git add .
   git commit -m "feat: your amazing contribution"
   git push origin your-branch-name

   # Create a PR on GitHub
   ```

3. **What to expect**:
   - We typically review PRs within 48 hours
   - CI checks must pass (we'll help if they don't!)
   - We may suggest changes - that's normal and helps everyone learn
   - Once approved, we'll merge your contribution 🎉

## 1. Local Setup

1. Clone the repository and open it in VS Code.
2. Reopen the folder in the Dev Container when prompted. The container build installs all dependencies and caches downloads in named volumes (`uv-cache`, `ansible-galaxy-cache`) so subsequent rebuilds stay fast.
3. Run the smoke playbook once to verify the toolchain:

   ```bash
   ansible-playbook playbooks/test-environment.yml
   ```

## 2. Branching & Git Flow Workflow

This repository follows a **Git Flow** strategy to protect the `main` branch and ensure stability:

### Branch Structure

- **`main`** - Production-ready code. Protected branch, only accepts PRs.
- **`develop`** - Integration branch for ongoing development. All feature/fix PRs target here.
- **Feature branches** - Created from `develop` for new features or fixes.

### Naming Conventions

Use descriptive branch names with prefixes:
- `feat/description` - New features (e.g., `feat/podman-support`)
- `fix/description` - Bug fixes (e.g., `fix/ansible-lint-errors`)
- `chore/description` - Maintenance tasks (e.g., `chore/update-deps`)
- `refactor/description` - Code refactoring (e.g., `refactor/devcontainer-profiles`)
- `docs/description` - Documentation updates (e.g., `docs/contributing-guide`)

### Workflow Steps

1. **Create feature branch from `develop`:**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feat/your-feature-name
   ```

2. **Make changes and commit:**
   - Keep commits focused; prefer small, reviewable slices over large batches.
   - Write clear commit messages using [Conventional Commits](https://www.conventionalcommits.org/)

### Commit Message Examples

**✅ Good commit messages:**
```
feat(ansible): add Podman support for Execution Environments
fix(ci): resolve pre-commit dependency installation
chore(deps): update ansible-lint to 24.2.0
docs: add troubleshooting guide for WSL2 setup
refactor(terraform): simplify variable passing in modules
test: add integration tests for docker-in-docker feature
```

**❌ Bad commit messages:**
```
update stuff              # Too vague
fix bug                   # Which bug? Where?
WIP                       # Don't commit WIP to main branches
asdf                      # Not descriptive
Fixed the thing           # What thing?
```

**Commit message structure:**
```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

**Types:** `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`
**Scope:** `ansible`, `terraform`, `golang`, `latex`, `ci`, `docs`, `deps`

3. **Push and create PR to `develop`:**
   ```bash
   git push origin feat/your-feature-name
   gh pr create --base develop --title "feat: your feature description"
   ```

4. **After PR is merged to `develop`:**
   - If all tests pass on `develop`, a PR to `main` will be automatically created
   - Once that PR passes all checks, it will auto-merge to `main`
   - Renovate PRs automatically target `develop` and follow the same flow

### Important Notes

- **Never push directly to `main` or `develop`** - always use pull requests
- **All PRs must pass CI checks** before merging (linting, tests, security scans)
- **Renovate PRs** automatically target `develop` and will auto-merge if tests pass
- **Release flow:** `develop` → `main` happens automatically when `develop` is stable

## 3. Using the Makefile

We provide a `Makefile` with common tasks for easy development:

```bash
make help              # Show all available commands
make test              # Run all tests
make lint              # Run all linters
make format            # Format all code
make build             # Build all devcontainers
make switch-ansible    # Switch to Ansible stack
make switch-terraform  # Switch to Terraform stack
make clean             # Clean build artifacts
```

See the [Makefile](../Makefile) for the complete list of available commands.

## 4. Code Style & Automation

- Install the pre-commit hooks inside the container:

  ```bash
  pre-commit install
  pre-commit run --all-files
  ```

  Hooks cover whitespace, YAML validation, `ansible-lint`, `yamllint`, `ruff`, and `detect-secrets`. They should pass before every push.

- Dependency changes for the Ansible stack are managed with `uv` and `pyproject.toml`:

  ```bash
  # Add a new dependency
  # Edit pyproject.toml to add the package with version constraint
  uv lock
  uv pip install --system .
  ```

  Commit both `pyproject.toml` and `uv.lock`. You can also run `ansible-playbook playbooks/update-dependencies.yml` to refresh the lockfile in one step (supports proxy overrides via `uv_http_proxy`, `uv_https_proxy`, etc.).

- Python formatting and linting are managed by `ruff` and `black`. Ansible/YAML files must stay compliant with the repo’s `.ansible-lint` and `.yamllint` configs.

## 5. Testing Your Changes

### Quick Tests (Required)

Run these before every commit:

```bash
# Use the Makefile (easiest)
make lint    # Runs all linters
make test    # Runs all tests

# Or run individually
yamllint .
ansible-lint
ruff check .
```

### Code Coverage

We track code coverage with [Codecov](https://codecov.io/gh/malpanez/ansible-devcontainer-vscode):

- **Minimum coverage**: 60% (enforced in CI)
- **New code**: Should maintain or improve coverage
- **View reports**: Check the Codecov badge in README or run `make coverage-report`

Run coverage locally:

```bash
# Run tests with coverage report
make coverage

# View HTML report in browser
make coverage-report

# Or run pytest directly
pytest tests/ --cov --cov-report=html
```

Coverage reports are generated in `htmlcov/index.html`.

### Full Test Suite (Recommended)

For larger changes, run the complete test suite:

Run the following before opening a pull request:

```bash
# Lint YAML and Ansible content
yamllint .
ansible-lint

# Quick infrastructure smoke tests
ansible-playbook playbooks/test-environment.yml

# Full Molecule scenario (runs Docker containers)
molecule test --scenario-name default

# Build and smoke-test container images (optional but recommended when touching Dockerfiles)
./scripts/smoke-devcontainer-image.sh --stack base --build
./scripts/smoke-devcontainer-image.sh --stack ansible --build
./scripts/smoke-devcontainer-image.sh --stack terraform --build
```

Add or update tests alongside new roles, tasks, or Molecule scenarios. For large changes, update CI or documentation if any new commands are required.

## 6. Common Setup Issues

### "Cannot connect to Docker daemon"

**Windows**:
1. Ensure Docker Desktop is running
2. Enable WSL2 integration: Docker Desktop → Settings → Resources → WSL Integration
3. Restart VS Code from inside WSL: `code .`

**Mac**:
1. Start Docker Desktop
2. Verify it's running: `docker ps`

**Linux**:
```bash
# Add your user to docker group
sudo usermod -aG docker $USER
# Log out and back in for changes to take effect
```

### "pre-commit not found"

Inside the devcontainer, install pre-commit:
```bash
uvx pre-commit install --install-hooks
```

### "Permission denied" errors with cache directories

The devcontainer should handle this automatically. If you see permission errors:
```bash
sudo chown -R vscode:vscode /workspace/.cache /home/vscode/.cache
```

### Devcontainer build is slow

First build takes 5-10 minutes. Subsequent builds should be faster (2-4 min) due to layer caching.

**Speed it up:**
- Use the pre-built GHCR images (already configured)
- Ensure Docker has enough resources (4GB+ RAM, 2+ CPUs)
- On Windows: Use WSL2, not Hyper-V

### Ansible/Terraform/Go tools not found

Make sure you've switched to the correct devcontainer stack:
```bash
make switch-ansible    # or terraform, golang, latex
# Then: Reopen in Container (Cmd/Ctrl + Shift + P)
```

### CI checks failing but passing locally

1. Ensure you've run `make lint` and `make test` locally
2. Check the CI logs for the specific error
3. Common issues:
   - Forgot to commit a file
   - Line ending differences (we use `.gitattributes` to prevent this)
   - Missing dependency in lockfile

## 7. Pull Requests

- Include a short summary of the change, testing evidence, and any follow-up work.
- Reference issues using the GitHub shorthand (`Fixes #123`) when applicable.
- Expect CI to run linting, syntax checks, playbook tests, Molecule matrix tests, and the Dev Container build. Resolve failures before requesting review.

## 8. Getting Help

If the Dev Container build, Molecule runs, or CI jobs fail in ways the guide does not cover, open a draft PR or start a discussion with logs attached. Sharing the output of `ansible-playbook playbooks/test-environment.yml -vvv` or `molecule --debug test` speeds up triage.

Happy automating!
