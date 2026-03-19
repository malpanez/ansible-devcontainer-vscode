# CLAUDE.md — ansible-devcontainer-vscode

Professional-grade multi-stack VS Code devcontainer repository.
Supports Ansible, Terraform, Go, and LaTeX development environments.
Published as team-ready images to GHCR.

## Project Overview

| Aspect             | Detail                                                         |
| ------------------ | -------------------------------------------------------------- |
| **Purpose**        | Reproducible dev containers for infrastructure engineers       |
| **Stacks**         | Ansible · Terraform (default) · GoLang · LaTeX                 |
| **Images**         | GHCR-published, slim builds (240–650 MB)                       |
| **Python runtime** | uv-managed, Python 3.12 — always `uv run`, never bare `python` |
| **Branch flow**    | `feature/*` → `develop` PR → auto-promote → `main`             |
| **Testing**        | pytest (95 % coverage) · molecule · pre-commit hooks           |

## Development Workflow

1. Make changes
2. Lint: `make lint` (runs yamllint, hadolint, shellcheck, ruff, ansible-lint)
3. Test: `make test`
4. Validate containers: `make validate-yaml && make validate-docker`
5. Full CI locally: `make ci-local`
6. Run pre-commit on staged files: `uvx pre-commit run --files $(git diff --name-only --cached)`
7. Commit with conventional commits (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `security:`)
   - **Do NOT add Co-Authored-By lines** to commit messages
8. Push to feature branch → open PR **to `develop`** (never directly to `main`)

## Commands Reference

```sh
# Setup
make setup              # Install all dependencies (uv sync)
make update-deps        # Update pre-commit hooks

# Quality
make lint               # All pre-commit hooks (YAML, Python, Shell, Docker)
make lint-fix           # Auto-fix where possible
make test               # pytest suite (95 % coverage required)
make security           # Trivy + secrets detection
make ci-local           # Full CI pipeline locally

# Container validation
make validate-yaml      # yamllint on all YAML
make validate-docker    # hadolint on all Dockerfiles
make build              # Build devcontainer images locally
make doctor-devcontainer # Health check + drift detection

# Stack switching
make switch-ansible     # Point .devcontainer/ to Ansible stack
make switch-terraform   # Point .devcontainer/ to Terraform stack
make switch-golang      # Point .devcontainer/ to Go stack
make switch-latex       # Point .devcontainer/ to LaTeX stack

# Ansible testing (via uv run)
uv run molecule test -s <scenario>       # Full test cycle
uv run molecule converge                 # Faster iteration (no destroy)
uv run molecule verify                   # Verifications only
uv run ansible-lint roles/ playbooks/   # Lint all Ansible content

# Terraform validation
terraform fmt -recursive                 # Format all .tf files
terraform validate                       # Validate config
tflint                                   # Lint rules
```

## Code Style & Conventions

### Python

- Formatter/linter: **ruff** (120-char lines, configured in `pyproject.toml`)
- Always `uv run pytest`, never bare `pytest`
- Coverage threshold: **95 %** — do not lower it

### YAML

- 2-space indentation, validated with **yamllint**
- All GitHub workflow files must pass yamllint

### Shell scripts

- **Bash only** (not `sh`)
- Always start with `set -euo pipefail`
- Pass **ShellCheck** without warnings
- Use `printf` over `echo` for portability

### Dockerfiles

- Validated with **hadolint**
- Multi-stage builds preferred, non-root user (`vscode`) enforced
- **Pin exact versions** — never use `latest`
- Verify checksums for downloaded binaries

### Ansible

- Roles in `roles/`, playbooks in `playbooks/`, collections in `collections/`
- Every role must have molecule tests in `molecule/`
- Lint with **ansible-lint** before any commit touching roles or playbooks

### Terraform

- `terraform fmt` before every commit
- Pin provider versions in `required_providers`
- Lint with **tflint**

## Branch Flow

```
main (protected)
  ↑ auto-promoted from develop by CI
develop (protected)
  ↑ all PRs target here
feature/*, fix/*, docs/*, chore/*, refactor/*
hotfix/* → main (ONLY for urgent production fixes — rare)
```

- Branch names must match the pattern `(feature|fix|docs|chore|refactor|security|hotfix)/...`
- `enforce-promotion-path.yml` workflow rejects PRs that bypass `develop`

## Devcontainer Architecture

```
python:3.12-slim-bookworm
  └─ devcontainers/base/   (shared Python layer)
       └─ devcontainers/ansible/

debian:bookworm-slim
  ├─ devcontainers/terraform/
  └─ devcontainers/latex/

golang:1.23-alpine
  └─ devcontainers/golang/
```

`.devcontainer/` is a **symlink/copy** of the active stack. Switch with `make switch-<stack>`.
After switching, always run `make doctor-devcontainer`.

## Things Claude Should NOT Do

- **Never** use `npm`, `node`, or TypeScript/JS tooling — this is not a JS project
- **Never** open a PR to `main` — always target `develop`
- **Never** use bare `python` or `pip` — use `uv run` or `uvx`
- **Never** use `latest` as a Docker image tag
- **Never** skip pre-commit hooks (`--no-verify`) — fix the issue instead
- **Never** commit secrets or credentials
- **Never** modify `.devcontainer/` without running `make doctor-devcontainer` afterward
- **Never** add a new role without molecule tests
- **Never** use `sh` for scripts — use `bash` with `set -euo pipefail`
- **Never** lower the 95 % test coverage threshold
- **Never** add Co-Authored-By lines to commit messages
- **Always** run `uvx pre-commit run --files <files>` before committing

## Adding a New Tool to a Container

1. Edit `devcontainers/<stack>/Dockerfile`
2. Pin exact version with checksum verification
3. Add tool to `tests/test_devcontainer_tools.py`
4. Update docs if user-facing
5. Run `make ci-local` before committing

## Self-Improvement

After every mistake, add a rule here. Prefix with the context where it applies.

---

_Keep this file current. Every rule prevents a repeated mistake._
