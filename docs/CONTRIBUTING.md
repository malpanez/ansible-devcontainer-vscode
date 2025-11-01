# Contributing Guide

Thanks for helping to evolve the Ansible DevContainer! This document captures the day-to-day workflow so changes stay consistent, tested, and easy to review.

## 1. Local Setup

1. Clone the repository and open it in VS Code.
2. Reopen the folder in the Dev Container when prompted. The container build installs all dependencies and caches downloads in named volumes (`uv-cache`, `ansible-galaxy-cache`) so subsequent rebuilds stay fast.
3. Run the smoke playbook once to verify the toolchain:

   ```bash
   ansible-playbook playbooks/test-environment.yml
   ```

## 2. Branching & Commits

- Branch from `main` using a descriptive name such as `feature/molecule-matrix` or `fix/yamllint`.
- Keep commits focused; prefer small, reviewable slices over large batches.
- Write clear commit messages in the present tense (e.g. `Add Molecule CI matrix for Debian and Ubuntu`).

## 3. Code Style & Automation

- Install the pre-commit hooks inside the container:

  ```bash
  pre-commit install
  pre-commit run --all-files
  ```

  Hooks cover whitespace, YAML validation, `ansible-lint`, `yamllint`, `ruff`, and `detect-secrets`. They should pass before every push.

- Dependency changes for the Ansible stack are managed with `uv`:

  ```bash
  uv add <package>
  uv lock
  uv export --format requirements-txt --frozen --output requirements-ansible.txt
  ```

  Commit `pyproject.toml`, `uv.lock`, and the regenerated `requirements-ansible.txt`. You can also run `ansible-playbook playbooks/update-dependencies.yml` to refresh everything in one step (supports proxy overrides via `uv_http_proxy`, `uv_https_proxy`, etc.).

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
