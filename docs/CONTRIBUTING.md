# Contributing Guide

Thanks for helping to evolve the Ansible DevContainer! This document captures the day-to-day workflow so changes stay consistent, tested, and easy to review.

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
   - Write clear commit messages using [Conventional Commits](https://www.conventionalcommits.org/):
     ```
     feat(ansible): add Podman support for Execution Environments
     fix(ci): resolve pre-commit dependency installation
     chore(deps): update ansible-lint to 24.2.0
     ```

3. **Push and create PR to `develop`:**
   ```bash
   git push origin feat/your-feature-name
   gh pr create --base develop --title "feat: your feature description"
   ```

4. **After PR is merged to `develop`:**
   - If all tests pass on `develop`, a PR to `main` will be automatically created
   - Once that PR passes all checks, it will auto-merge to `main`
   - Dependabot PRs automatically target `develop` and follow the same flow

### Important Notes

- **Never push directly to `main` or `develop`** - always use pull requests
- **All PRs must pass CI checks** before merging (linting, tests, security scans)
- **Dependabot PRs** automatically target `develop` and will auto-merge if tests pass
- **Release flow:** `develop` → `main` happens automatically when `develop` is stable

## 3. Code Style & Automation

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

## 4. Testing Checklist

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

## 5. Pull Requests

- Include a short summary of the change, testing evidence, and any follow-up work.
- Reference issues using the GitHub shorthand (`Fixes #123`) when applicable.
- Expect CI to run linting, syntax checks, playbook tests, Molecule matrix tests, and the Dev Container build. Resolve failures before requesting review.

## 6. Getting Help

If the Dev Container build, Molecule runs, or CI jobs fail in ways the guide does not cover, open a draft PR or start a discussion with logs attached. Sharing the output of `ansible-playbook playbooks/test-environment.yml -vvv` or `molecule --debug test` speeds up triage.

Happy automating!
