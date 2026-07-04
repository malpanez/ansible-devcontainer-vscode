# Infrastructure Dev Containers for VS Code

[![CI Pipeline](https://github.com/malpanez/ansible-devcontainer-vscode/actions/workflows/ci.yml/badge.svg)](https://github.com/malpanez/ansible-devcontainer-vscode/actions/workflows/ci.yml)
[![Build Containers](https://github.com/malpanez/ansible-devcontainer-vscode/actions/workflows/build-containers.yml/badge.svg)](https://github.com/malpanez/ansible-devcontainer-vscode/actions/workflows/build-containers.yml)
[![CodeQL](https://github.com/malpanez/ansible-devcontainer-vscode/actions/workflows/codeql.yml/badge.svg)](https://github.com/malpanez/ansible-devcontainer-vscode/actions/workflows/codeql.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/malpanez/ansible-devcontainer-vscode/badge)](https://securityscorecards.dev/viewer/?uri=github.com/malpanez/ansible-devcontainer-vscode)
[![SBOM](https://github.com/malpanez/ansible-devcontainer-vscode/actions/workflows/sbom-verification.yml/badge.svg)](https://github.com/malpanez/ansible-devcontainer-vscode/actions/workflows/sbom-verification.yml)
[![Code Quality](https://github.com/malpanez/ansible-devcontainer-vscode/actions/workflows/quality.yml/badge.svg)](https://github.com/malpanez/ansible-devcontainer-vscode/actions/workflows/quality.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

[![GHCR](https://img.shields.io/badge/GHCR-images-blue?logo=github)](https://github.com/malpanez?tab=packages&repo_name=ansible-devcontainer-vscode)
[![Open in GitHub Codespaces](https://img.shields.io/badge/Codespaces-Open-blue?logo=github)](https://codespaces.new/malpanez/ansible-devcontainer-vscode)
[![Renovate](https://img.shields.io/badge/renovate-enabled-brightgreen?logo=renovatebot)](https://github.com/malpanez/ansible-devcontainer-vscode/issues)
[![uv](https://img.shields.io/badge/uv-ready-00A3FF?logo=astral)](https://github.com/astral-sh/uv)

**Stacks:**
[![Ansible](https://img.shields.io/badge/ansible-9.14.0-EE0000?logo=ansible)](https://www.ansible.com/)
[![Terraform](https://img.shields.io/badge/terraform-1.14.0-7B42BC?logo=terraform)](https://www.terraform.io/)
[![Go](https://img.shields.io/badge/go-1.25-00ADD8?logo=go&logoColor=white)](https://go.dev/)
[![Python](https://img.shields.io/badge/python-3.12.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)

Pull a pre-built infrastructure workspace from GHCR and start writing Terraform or running Ansible in **under 30 seconds** — 3–5× smaller than Microsoft's devcontainer images, with no local setup and no drift between machines. Pick the stack you need (Ansible, Terraform, Golang, or LaTeX), reopen in VS Code, and your entire toolchain is already installed, locked, and ready. Works on Windows + WSL2, macOS, and Linux.

## Highlights

- ⚡ **uv-first Python workflow** – dependency installs are fast and reproducible via `uv pip install --system .` using `pyproject.toml` for the Ansible stack.
- 🐳 **Dev Container ready** – Dockerfile, features, extensions, and VS Code settings ship in the repo.
- 🤖 **Automation via Ansible** – `playbooks/setup-workspace.yml` provisions the container with roles for base OS tweaks, Ansible tooling, Python testing tools, and editor config.
- 🧩 **Multi-stack templates** – ship Ansible, Terraform, Golang, and LaTeX workspaces side-by-side; switch with a single helper script.
- 🧱 **Slim stack-specific images** – each stack is based on the leanest upstream image (Chainguard or slim Debian/Python) with layered cleanup for fast pulls.
- 📦 **GHCR-ready images** – Dockerfiles are optimised for publishing to `ghcr.io` so teams can pull prebuilt devcontainers instead of rebuilding locally.
- 🧪 **Quality gates baked in** – pre-commit hooks, `ansible-lint`, `yamllint`, Molecule/pytest harness, and GitHub Actions CI.
- 🪪 **Template-driven pre-commit** – `ensure-precommit` seeds the right hook config per stack and runs `uvx pre-commit` without bloating the images.
- 🔐 **Security conscious** – runs as non-root, includes Trivy scanning in CI, and keeps secrets out of the repo.
- 🤖 **AI agent safe by design** – run Claude Code, Copilot, or any AI agent with full permissions inside the container. Worst case: a broken workspace, back to normal with `git reset` in seconds. Your host OS, credentials, and other projects are never at risk.
- 📣 **Responsible disclosure** – see [`SECURITY.md`](SECURITY.md) for reporting guidelines and supply-chain expectations.
- 🪟 **Windows bootstrap script** – run `scripts/bootstrap-windows.ps1` to enable WSL, configure proxies, and install Docker/VS Code with one command.

## Requirements

| Platform      | What you need                                                                                                        |
| ------------- | -------------------------------------------------------------------------------------------------------------------- |
| Windows 10/11 | WSL2 (Ubuntu recommended), Docker Desktop with WSL integration, Visual Studio Code, and the Dev Containers extension |
| macOS / Linux | Docker Engine or Docker Desktop, Visual Studio Code + Dev Containers extension                                       |
| Everywhere    | Git, ability to clone this repository                                                                                |

> **Tip (Windows)** – enable WSL2 (`wsl --install`), reboot, install Ubuntu from the Microsoft Store, then install Docker Desktop and enable “Use the WSL 2 based engine”. Launch VS Code from inside WSL (`code .`) so the Remote – WSL and Dev Containers extensions can build the workspace container seamlessly.

## Why not Microsoft's devcontainer images?

Full digest pinning, checksum-verified tooling and slimmer bases — the
complete rationale lives in [docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md).

## Quick Start

### Option 1: GitHub Codespaces (Fastest - No Setup Required)

Launch in your browser with one click:

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/malpanez/ansible-devcontainer-vscode)

**Ready in 30-60 seconds** - No local installation needed!

### Option 2: Local Dev Container

```bash
# inside WSL2 or any terminal with Docker + VS Code available
git clone https://github.com/malpanez/ansible-devcontainer-vscode.git
cd ansible-devcontainer-vscode

# Pick the stack you need (defaults to Ansible if you skip this step)
./scripts/use-devcontainer.sh terraform   # or ansible | golang | latex
# Or use: make switch-terraform

code .

# When prompted, choose "Dev Containers: Reopen in Container"
# VS Code pulls the published GHCR image for the chosen stack.
```

> **New Windows laptop?** Run [`scripts/bootstrap-windows.ps1`](scripts/bootstrap-windows.ps1) from an elevated PowerShell prompt (see [`docs/BOOTSTRAP_WINDOWS.md`](docs/BOOTSTRAP_WINDOWS.md)) to enable WSL, configure proxies, and install Docker Desktop / VS Code automatically.

## Pre-commit Strategy

Every stack ships with a ready-to-use `.pre-commit-config.yaml`. The image bakes in `/usr/local/bin/ensure-precommit`, a tiny helper that:

1. Copies the right template from `/usr/local/share/devcontainer-skel/<stack>/` if the workspace does not provide one.
2. Runs `uv tool install pre-commit` followed by `uvx pre-commit install -f` and `uvx pre-commit autoupdate`.

This keeps developer experience consistent:

- **Ansible** builds from `python:3.12-slim-bookworm` (switchable to `ghcr.io/chainguard-images/python:latest` via `BASE_IMAGE`) and installs Ansible + hooks with `uv pip install --system`.
- **Terraform, Golang, and LaTeX** remain Python-free. They install the `uv` launcher only, so `uvx pre-commit` bootstraps Python on-demand without bloating the image.
- In VS Code, the `postCreateCommand` simply calls `ensure-precommit`, guaranteeing hooks are installed on day one.
- CI mirrors the workflow with `uvx pre-commit run --all-files`, so the same hook set gates every PR.

## Available Stacks

| Stack       | Base image                                                  | Approx. size¹ | Included tooling                                                              | Cache mounts                                  |
| ----------- | ----------------------------------------------------------- | ------------- | ----------------------------------------------------------------------------- | --------------------------------------------- |
| `ansible`   | `python:3.12-slim-bookworm` (overrideable via `BASE_IMAGE`) | ~650 MB       | uv-managed Python, Ansible + collections, `pre-commit`, `tini`, SSH/git utils | uv cache volume, Ansible Galaxy volume        |
| `terraform` | multi-stage Debian (bookworm tools + runtime)               | ~240 MB       | Terraform CLI, Terragrunt, TFLint, SOPS, age, `uv` launcher                   | `${workspace}/.terraform.d/plugin-cache` bind |
| `golang`    | `golang:1.23-alpine` (overrideable via `BASE_IMAGE`)        | ~210 MB       | Go toolchain, git, `uv` launcher, sudo minimal                                | Go module & build caches                      |
| `latex`     | `debian:bookworm-slim` + Tectonic                           | ~320 MB       | Tectonic CLI, git/perl helpers, `uv` launcher                                 | `${HOME}/.cache/tectonic` bind                |

¹Sizes are indicative for `linux/amd64` and vary slightly per architecture.

## Why not distroless or Alpine?

See [docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md).

## Image Publishing & GHCR

Images for every stack are built, scanned, attested and published to
GHCR by CI. See [docs/IMAGE_PUBLISHING.md](docs/IMAGE_PUBLISHING.md)
for tags, pull commands and the publishing pipeline.

## Toolchain Overview

The table below outlines the tooling shipped with the Ansible stack; Terraform inherits the Python toolchain plus HashiCorp utilities, while Golang and LaTeX stay intentionally lean.

| Area             | Included tooling                                                                                                   |
| ---------------- | ------------------------------------------------------------------------------------------------------------------ |
| Provisioning     | Ansible 9, ansible-navigator, Molecule (Docker driver), pytest, pytest-ansible, pytest-testinfra                   |
| Linting          | ansible-lint (production profile), yamllint, ruff, black, mypy, tflint                                             |
| Python packaging | [`uv`](https://github.com/astral-sh/uv) for package installation and script execution                              |
| Collections      | `ansible.posix`, `community.general`, `community.docker`, `kubernetes.core`, `amazon.aws` (see `requirements.yml`) |
| VS Code          | Recommended extensions, workspace settings, and tasks delivered by the `vscode_config` role                        |
| Terraform        | Terraform CLI, Terragrunt, TFLint, Checkov (Dev Container installs; CI mirrors tooling)                            |

All Python dependencies for the Ansible stack are declared in `pyproject.toml` and locked in `uv.lock`. The container installs them system-wide with `uv pip install --system .` during build. If you prefer an isolated virtual environment, run `uv venv .venv && uv pip install -e .` inside the container; VS Code will automatically pick up `.venv` thanks to the defaults in `.vscode/settings.json`. Other stacks install only the tooling they need (for example, Terraform pins Terraform/Terragrunt/TFLint via the Dockerfile and installs Checkov with `uv pip install "checkov>=3.0.0,<4.0.0"`).

## Pinned Tool Versions

Tool versions are pinned at their single source of truth — duplicated
version tables rot:

- **Python packages**: `pyproject.toml` + `uv.lock` (exports:
  `requirements.txt`, `requirements-ansible.txt`)
- **CLI tools** (terraform, terragrunt, tflint, sops, age, uv, AWS CLI,
  tectonic): `ARG *_VERSION` at the top of each `devcontainers/*/Dockerfile`,
  each download verified against its upstream checksum
- **Base images**: digest-pinned `FROM` lines in the same Dockerfiles

## Local Workflow

1. **Open the repo with VS Code** and reopen it in the Dev Container.
2. **Run the bootstrap playbook** if you need to reconfigure the workspace manually:
   ```bash
   ansible-playbook playbooks/setup-workspace.yml --tags base,ansible
   ```
3. **Use the VS Code tasks** (`Ctrl+Shift+B` / `Cmd+Shift+B`):
   - `Ansible: Lint All`
   - `Ansible: Syntax Check`
   - `Ansible: Setup (Check)`
   - `YAML: Lint All`
   - `Smoke Tests` (runs `./scripts/run-smoke-tests.sh`)
   - `Test: Health Check` (`ansible-playbook playbooks/setup-workspace.yml --check`)
   - `Molecule: Test` (runs the full Molecule + Testinfra scenario)
   - `Dependencies: Refresh Lock` (invokes `ansible-playbook playbooks/update-dependencies.yml`)
   - `Pre-commit: Run All`
4. **Pre-commit** protects commits automatically. Install the hooks once:

   ```bash
   pre-commit install
   pre-commit run --all-files

   The hook stack covers `ansible-lint`, `yamllint`, `ruff` (lint + format), and `detect-secrets` (baseline stored in `.secrets.baseline`).
   ```

## CI/CD

GitHub Actions workflows live under `.github/workflows/`:

- `ci.yml` – runs repository-wide `uvx pre-commit run --all-files`, lints shell and PowerShell scripts, keeps Go/Terraform checks, builds every Dev Container as a multi-arch (`linux/amd64,linux/arm64`) `buildx` job with registry-backed caches, smoke-tests the loaded images, and gates on Trivy CRITICAL findings plus `hadolint`.
- `lint.yml` – lightweight watcher that reuses the same `uvx pre-commit` pipeline when YAML or Ansible content changes.
- `release.yml` – publishes tagged releases, reuses the hardened build pipeline, pushes images/SBOMs to GHCR, and signs them with cosign.

All jobs use Python 3.12 on `ubuntu-latest`. The shared toolchain mirrors the Dev Container ensuring parity between local development and CI.

## Repository Layout

```
.
├── .devcontainer/           # Dockerfile + devcontainer.json (uv-enabled)
├── .github/workflows/       # CI/CD pipelines
├── .vscode/                 # Local workspace defaults
├── devcontainers/           # Stack-specific Dockerfiles (ansible, terraform, golang, latex)
├── inventory/               # Sample localhost inventory
├── playbooks/               # Ansible playbooks (setup + verification)
├── roles/                   # Role-based workspace provisioning
├── pyproject.toml           # Python dependencies (Ansible stack)
├── uv.lock                  # Locked dependency versions
├── requirements.yml         # Ansible collections
└── docs/                   # Documentation (bootstrap guides, roadmap, quick starts)
```

## Workspace Roles & Variables

| Role                    | Purpose                                                                                      | Key variables                                                                                                                                                              |
| ----------------------- | -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `devcontainer_base`     | System packages, user creation, sudoers hardening, timezone                                  | `devcontainer_base_user`, `devcontainer_base_timezone`                                                                                                                     |
| `ansible_environment`   | Installs uv, Python requirements, Ansible collections, drops `ansible.cfg` & `.ansible-lint` | `ansible_environment_config_dir`, `ansible_environment_python_requirements_file`, `ansible_environment_collection_requirements_file`, `ansible_environment_uv_binary_path` |
| `python_tools`          | Shell PATH tweaks and pytest config                                                          | `python_tools_devcontainer_user`, `python_tools_ansible_config_dir`                                                                                                        |
| `vscode_config`         | VS Code settings, extensions, tasks                                                          | `vscode_config_workspace_dir`, `vscode_config_python_interpreter_path`                                                                                                     |
| `devcontainer_template` | Copies Dev Container template into `.devcontainer/`                                          | `devcontainer_template_stack`, `devcontainer_template_root`, `devcontainer_template_target`, `devcontainer_template_clean`                                                 |

Override defaults in `roles/*/defaults/main.yml` or pass extra vars (`-e variable=value`) to tailor the workspace.

## Testing & Verification

- `./scripts/run-smoke-tests.sh` — fast smoke test that also asserts Ansible/ansible-core match the pinned requirements.
- `./scripts/run-ansible-tests.sh` — runs `ansible-test sanity` against every role (set `ANSIBLE_TEST_PYTHON_VERSION` to change the interpreter).
- `./scripts/smoke-devcontainer-image.sh` — builds a Dev Container image and runs per-stack smoke checks (compatible with Docker Desktop or Podman).
- `./scripts/smoke-devcontainer-image.sh --stack <name> --build` — builds a stack image (`ansible`, `terraform`, `golang`, `latex`) and runs an end-to-end smoke check used in CI.
- `molecule test` — spins up Debian with all roles applied and verifies via Testinfra (`molecule/default/tests/test_default.py`).
- GitHub Actions runs `uvx pre-commit`, targeted playbook/Molecule checks, Go/Terraform tests when relevant, and the hardened container pipeline described above (see `.github/workflows/ci.yml`).
- See [`docs/`](docs/README.md) for scenario walkthroughs (Terraform Proxmox, LaTeX résumé), corporate network tips, and the Windows bootstrap guide.

## Scenario Playbooks

Need inspiration for real-world workflows? Start with the scenario guides under [`docs/scenarios`](docs/scenarios):

- [`terraform-proxmox.md`](docs/scenarios/terraform-proxmox.md) — provisions the Proxmox homelab modules using the Terraform stack.
- [`latex-cv.md`](docs/scenarios/latex-cv.md) — compiles a LaTeX résumé with the LaTeX devcontainer and VS Code tasks.

Each scenario lists the recommended stack, prerequisite commands, and smoke tests so you can adapt them for demos or portfolio work.

## Customising the Environment

Extend a stack profile from your own `.devcontainer/devcontainer.json`,
add tools at build time, or layer extra VS Code settings — recipes in
[docs/CUSTOMISING.md](docs/CUSTOMISING.md).

## Branch Flow

- Feature work should target `develop`.
- Promotion to `main` is expected to happen from `develop` through the repository automation.
- Urgent production fixes may target `main` from `hotfix/*`.
- The repository enforces this path in `.github/workflows/enforce-promotion-path.yml`.

## Dependency Management

- Dependencies are defined in `pyproject.toml` and locked via `uv.lock`. Run `uv lock` whenever you add or upgrade packages.
- Installations in the Dev Container and CI use `uv pip install --system .` directly from `pyproject.toml`, letting `uv` handle dependency resolution automatically.
- To test upgrades locally:
  ```bash
  uv lock --upgrade package_name
  uv pip install --system .
  ```
  Commit `uv.lock` and the updated `pyproject.toml`.
- You can automate the lock refresh with `ansible-playbook playbooks/update-dependencies.yml`. Pass `uv_http_proxy`, `uv_https_proxy`, `uv_index_url`, or `uv_no_proxy` as extra vars when running behind a corporate proxy.

## Testing

- `pre-commit run --all-files` – runs yamllint/ansible-lint/ruff/detect-secrets.
- `./scripts/run-ansible-tests.sh` – executes `ansible-test sanity` for every role (respects `ANSIBLE_TEST_PYTHON_VERSION`, defaults to the pinned Python).
- `ansible-playbook playbooks/setup-workspace.yml --check` – dry-run validation of the provisioning playbook.
- `./scripts/run-smoke-tests.sh` – convenience wrapper around `playbooks/test-environment.yml`; pass extra args to forward flags (e.g. `--check`).
- `./scripts/run-terraform-tests.sh` – formats (`terraform fmt -check`) and validates every Terraform module under `infrastructure/` (skips gracefully when no configs exist). Modules that depend on private providers (for example `infrastructure/proxmox_lab`) are skipped automatically in CI so they can be tested manually when the provider binaries are available.
- `.trivyignore` documents the temporary CVE allowlist applied to vendor-supplied Terraform tooling (age/sops/terragrunt/tflint). We keep the list short and revisit it whenever upstream ships patched binaries.
- `ansible-playbook playbooks/update-dependencies.yml` – regenerates `uv.lock` from `pyproject.toml`.
- `molecule test` – full integration verification.
  Run `molecule test --scenario-name latex` to exercise the MiKTeX ↔ TeX Live toggle specifically.
- `tflint --init && tflint` – optional Terraform lint (configure rules in `infrastructure/.tflint.hcl`).
- `checkov -d infrastructure/` – run policy-as-code scans locally; the Terraform container installs Checkov by default.

## Infrastructure Modules

- `infrastructure/README.md` documents the Terraform module layout and how to extend it.
- `infrastructure/proxmox_lab/` provides a starter module for Proxmox VE VMs (clone existing templates and customise via `virtual_machines`).
- Copy `proxmox.auto.tfvars.example` into a git-ignored `.tfvars` file and populate secrets via environment variables before planning or applying.

## Secrets Management

- Follow `docs/SECRETS.md` to keep API tokens and credentials out of git while still enabling local automation.
- Use the shipped `.secrets.baseline` and `pre-commit` hooks to catch accidental leaks before pushing.
- Populate GitHub repository secrets (e.g. `TF_PM_TOKEN_ID`, `TF_PM_TOKEN_SECRET`) before enabling Terraform plans in CI.

## Security & Code Scanning

This repository implements comprehensive security scanning and automated alert management:

- 🔒 **Trivy Scanning**: All container images scanned for CVEs during build
- 📊 **SARIF Upload**: Security findings integrated into GitHub Security tab
- 🤖 **Automated Alert Management**: Weekly cleanup of stale/false-positive alerts

**For security reports**: See [`SECURITY.md`](SECURITY.md) for responsible disclosure guidelines.

**Alert Management**:

- Automated workflow runs weekly to clean up stale alerts (90+ days old)
- Manual trigger available via GitHub Actions → "Security Alert Management"
- Custom dismissal rules in [`.github/scripts/manage-code-scanning-alerts.sh`](.github/scripts/manage-code-scanning-alerts.sh)
- Configuration file: [`.github/security-alert-exceptions.yml`](.github/security-alert-exceptions.yml)

See [`.github/scripts/README.md`](.github/scripts/README.md) for automation details and usage.

## Performance Optimizations

Recent optimizations have significantly improved DevContainer startup times:

- **⚡ Fast Startup**: Containers now start in ~30 seconds (previously 2-5 minutes)
- **🚀 Direct Pull**: git, github-cli (gh), and AWS CLI v2 are pre-installed in base images, eliminating the need for DevContainer features that trigger rebuilds
- **🔧 Pre-commit Permissions**: Fixed permission issues with gitleaks/Go cache by setting `PRE_COMMIT_HOME` and ensuring proper cache directory ownership

### Using DevContainers in Your Projects

Want to use these production-ready containers in your own Ansible or Terraform projects? See:

- **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** - Complete integration guide with setup instructions, pre-commit hooks explanation, and troubleshooting
- **[examples/](examples/)** - Ready-to-use templates for Ansible collections and Terraform projects
  - [Ansible Collection Template](examples/ansible-collection/) - Includes [PROMPT_FOR_LLM.md](examples/ansible-collection/PROMPT_FOR_LLM.md) (copy-paste prompt for Claude/ChatGPT)
  - [Terraform Project Template](examples/terraform-project/) - Includes [PROMPT_FOR_LLM.md](examples/terraform-project/PROMPT_FOR_LLM.md) (copy-paste prompt for Claude/ChatGPT)
  - [DEVCONTAINER_FEATURES_EXPLAINED.md](examples/DEVCONTAINER_FEATURES_EXPLAINED.md) - Technical explanation of pull vs build behavior

**Quick Setup** (one-line command):

```bash
# For Ansible Collections
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/ansible-collection/.devcontainer/devcontainer.json -o .devcontainer/devcontainer.json --create-dirs

# For Terraform Projects
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.devcontainer/devcontainer.json -o .devcontainer/devcontainer.json --create-dirs
```

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) – visual architecture diagrams (Mermaid) showing container build hierarchy, CI/CD pipeline, dependency management flow, and security scanning strategy.
- `docs/PORTFOLIO.md` captures the automation story behind this repo (useful for blog posts or personal branding).
- `docs/ROADMAP.md` lists planned enhancements such as extra Dev Containers, CV automation in LaTeX, and onboarding tooling.
- `docs/CHANGELOG.md` tracks notable changes between releases.
- `docs/RELEASE_FLOW.md` documents the `develop -> main` promotion path and the `hotfix/* -> main` escape hatch.
- `docs/SECRETS.md` explains how to handle credentials safely across Terraform and Ansible workflows.
- [`docs/IMAGE_PUBLISHING.md`](docs/IMAGE_PUBLISHING.md) – GHCR tags, pull commands and the publishing pipeline.
- [`docs/CUSTOMISING.md`](docs/CUSTOMISING.md) – extending stack profiles and adding tools.
- [`docs/DESIGN_DECISIONS.md`](docs/DESIGN_DECISIONS.md) – why not Microsoft's images, distroless or Alpine.

## Windows Bootstrap

- Run `scripts/bootstrap-windows.ps1` from an elevated PowerShell session to install Windows Terminal, Git, VS Code, PowerShell 7, WSL2 + Ubuntu, your chosen container engine (Docker Desktop by default or Podman via `-ContainerEngine Podman`), and the VS Code Remote extensions.
- Optional flags: `-SkipDocker`, `-SkipWSL`, `-ProxyUrl`, `-ProxyBypassList`, and `-PersistProxy` for corporate environments. The script validates winget availability, configures proxies, and reports any reboot requirements. When selecting Podman, use the `-ContainerEngine Podman` switch to avoid Docker Desktop’s commercial licensing requirements.
- After reboot (if prompted), launch Ubuntu in WSL2, finish the distro bootstrap, clone the repo, and follow the Quick Start.

## Corporate Networks

If you are behind a VPN, TLS intercept proxy, or an internal Artifactory mirror, review `docs/CORPORATE_NETWORK.md` for guidance on proxy variables, certificate trust, and running the Dev Container in restricted environments.

## Contributing

See `docs/CONTRIBUTING.md` for branching strategy, lint/test expectations, and pull request guidelines.

## License

Distributed under the MIT License. See `LICENSE` for details.

## 💖 Support This Project

If this project has helped you or your team, please consider:

- ⭐ Starring the repository
- 🐛 Reporting bugs or suggesting features
- 💰 [Sponsoring on GitHub](https://github.com/sponsors/malpanez)
- 💼 [Hiring me for consulting](mailto:alpanez.alcalde@gmail.com)

## 💼 Enterprise Support & Training

Organizations using this in production can get:

- Implementation consulting
- Custom feature development
- Team training workshops
- Priority support with SLA

**Rate:** Competitive day rates for Ireland market
**Contact:** alpanez.alcalde@gmail.com

---

Built with ❤️ by [Miguel Alpañez](https://github.com/malpanez) | DevOps Consultant | Dublin, Ireland
