# Infrastructure Dev Containers for VS Code

[![CI Pipeline](https://github.com/malpanez/ansible-devcontainer-vscode/actions/workflows/ci.yml/badge.svg)](https://github.com/malpanez/ansible-devcontainer-vscode/actions/workflows/ci.yml)
[![Lint](https://github.com/malpanez/ansible-devcontainer-vscode/actions/workflows/lint.yml/badge.svg)](https://github.com/malpanez/ansible-devcontainer-vscode/actions/workflows/lint.yml)
[![Roadmap](https://img.shields.io/badge/roadmap-public-1f6feb.svg)](docs/ROADMAP.md)
[![Portfolio](https://img.shields.io/badge/portfolio-notes-6f42c1.svg)](docs/PORTFOLIO.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)
[![uv](https://img.shields.io/badge/uv-ready-00A3FF)](https://github.com/astral-sh/uv)

Modern, reproducible infrastructure development environments powered by VS Code Dev Containers and the `uv` Python toolchain. Open the repository in VS Code, pick the stack you need (Ansible, Terraform, Golang, or LaTeX), reopen in a container, and you are ready to lint, test, and ship automation from any platform (Windows + WSL2, macOS, or Linux).

## Highlights

- ⚡ **uv-first Python workflow** – dependency installs are fast and reproducible via `uv pip install --system --requirement requirements-ansible.txt` for the Ansible stack.
- 🐳 **Dev Container ready** – Dockerfile, features, extensions, and VS Code settings ship in the repo.
- 🤖 **Automation via Ansible** – `playbooks/setup-workspace.yml` provisions the container with roles for base OS tweaks, Ansible tooling, Python testing tools, and editor config.
- 🧩 **Multi-stack templates** – ship Ansible, Terraform, Golang, and LaTeX workspaces side-by-side; switch with a single helper script.
- 🧱 **Shared Python base layer** – build once, reuse across Ansible/Terraform images, and publish it to GHCR for consistent tooling.
- 📦 **GHCR-ready images** – Dockerfiles are optimised for publishing to `ghcr.io` so teams can pull prebuilt devcontainers instead of rebuilding locally.
- 🧪 **Quality gates baked in** – pre-commit hooks, `ansible-lint`, `yamllint`, Molecule/pytest harness, and GitHub Actions CI.
- 🔐 **Security conscious** – runs as non-root, includes Trivy scanning in CI, and keeps secrets out of the repo.
- 📣 **Responsible disclosure** – see [`SECURITY.md`](SECURITY.md) for reporting guidelines and supply-chain expectations.
- 🪟 **Windows bootstrap script** – run `scripts/bootstrap-wsl2.ps1` (see [Windows onboarding](docs/ONBOARDING-WINDOWS.md)) to enable WSL, configure Docker or Podman, and install VS Code in one go.

## Requirements

| Platform | What you need |
| --- | --- |
| Windows 10/11 | WSL2 (Ubuntu recommended), Docker Desktop with WSL integration, Visual Studio Code, and the Dev Containers extension |
| macOS / Linux | Docker Engine or Docker Desktop, Visual Studio Code + Dev Containers extension |
| Everywhere | Git, ability to clone this repository |

> **Tip (Windows)** – enable WSL2 (`wsl --install`), reboot, install Ubuntu from the Microsoft Store, then install Docker Desktop and enable “Use the WSL 2 based engine”. Launch VS Code from inside WSL (`code .`) so the Remote – WSL and Dev Containers extensions can build the workspace container seamlessly.

## Quick Start

```bash
# inside WSL2 or any terminal with Docker + VS Code available
git clone https://github.com/malpanez/ansible-devcontainer-vscode.git
cd ansible-devcontainer-vscode

# Pick the stack you need (defaults to Ansible if you skip this step)
./scripts/use-devcontainer.sh terraform   # or ansible | golang | latex

code .

# When prompted, choose "Dev Containers: Reopen in Container"
# VS Code pulls the published GHCR image for the chosen stack.
```

> **New Windows laptop?** Run [`scripts/bootstrap-wsl2.ps1`](scripts/bootstrap-wsl2.ps1) from an elevated PowerShell prompt (see [`docs/ONBOARDING-WINDOWS.md`](docs/ONBOARDING-WINDOWS.md)) to enable WSL, configure Docker Desktop or Podman, and install VS Code automatically.

### Handy VS Code Tasks

The workspace ships curated tasks under `.vscode/tasks.json` so you can jump straight into automation:

- **Devcontainer: Rebuild \<stack\>** – runs `devcontainer build --workspace-folder devcontainers/<stack>` to refresh the Ansible, Terraform, Golang, or LaTeX images without leaving VS Code.
- **Terraform: Validate** and **Ansible: Lint All** – wrap the helper scripts (`run-terraform-tests.sh`, `ansible-lint`) so you can run the usual CI checks from *Terminal → Run Task…*.
- **Devcontainer: Build All** – executes `scripts/check-devcontainer.sh` to smoke-test every stack before pushing changes.

Use them from the command palette (`Ctrl/Cmd+Shift+P → Run Task`) whenever you switch stacks or need a quick validation pass.

## Available Stacks

| Stack | Purpose | Key tooling delivered |
| --- | --- | --- |
| `ansible` | Full Ansible automation workspace | ansible-navigator, ansible-lint, Molecule + pytest, uv-based Python toolchain |
| `terraform` | Terraform + Terragrunt with Ansible utilities | Terraform CLI, Terragrunt, TFLint, Checkov, shared Ansible linting helpers |
| `golang` | Lightweight Go development container | Go 1.22 toolchain (install goimports/delve/golangci-lint as needed) |
| `latex` | Authoring LaTeX documents | MiKTeX (default) or TeX Live, latexmk/biber tooling |

## Image Publishing & GHCR

This repository now publishes a shared Python base (`ghcr.io/<org>/devcontainer-base:py312`) plus one image per stack (`devcontainer-ansible`, `devcontainer-terraform`, `devcontainer-golang`, `devcontainer-latex`). Tag pushes (via `.github/workflows/release.yml`) build every image for `linux/amd64` and `linux/arm64` (LaTeX ships on `amd64` only) and push both `:latest` and `:<tag>` variants to GHCR.

> **Security hygiene** – `.github/workflows/build-containers.yml` runs on a weekly schedule so GHCR images automatically pick up Debian security fixes (`apt full-upgrade`) and refreshed tooling even when the repository is quiet.

To build or test images locally:

```bash
# Build the shared base (must exist before the Python stacks are built)
docker build -f devcontainers/base/Dockerfile -t ghcr.io/<org>/devcontainer-base:py312 .

# Build a stack image using the base you just built
docker build -f devcontainers/terraform/Dockerfile \
  --build-arg BASE_IMAGE=ghcr.io/<org>/devcontainer-base:py312 \
  -t ghcr.io/<org>/devcontainer-terraform:local .
```

You can now reference the local tag from `.devcontainer/devcontainer.json` or push it to GHCR with `docker push`. Use `BASE_IMAGE=python:3.12-slim-bookworm` if you need a one-off rebuild without producing the shared base first.

Release builds sign every image with [cosign](https://github.com/sigstore/cosign) and attach SPDX SBOMs generated with [Syft](https://github.com/anchore/syft). Verify a published image with:

```bash
cosign verify ghcr.io/malpanez/devcontainer-ansible:latest \
  --certificate-identity "https://github.com/malpanez/ansible-devcontainer-vscode/.github/workflows/release.yml@refs/tags/<tag>" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

Replace `<tag>` with the release you want to verify (for example `v1.2.3`). SBOMs ship as release workflow artifacts under the `devcontainer-sbom` name so you can audit dependencies alongside the signed image.

To reproduce the Ansible stack outside of the Dev Container run:

```bash
ansible-playbook playbooks/setup-workspace.yml -K
```

## Toolchain Overview

The table below outlines the tooling shipped with the Ansible stack; Terraform inherits the Python toolchain plus HashiCorp utilities, while Golang and LaTeX stay intentionally lean.

| Area | Included tooling |
| --- | --- |
| Provisioning | Ansible 9, ansible-navigator, Molecule (Docker driver), pytest, pytest-ansible, pytest-testinfra |
| Linting | ansible-lint (production profile), yamllint, ruff, black, mypy, tflint |
| Python packaging | [`uv`](https://github.com/astral-sh/uv) for package installation and script execution |
| Collections | `ansible.posix`, `community.general`, `community.docker`, `kubernetes.core`, `amazon.aws` (see `requirements.yml`) |
| VS Code | Recommended extensions, workspace settings, and tasks delivered by the `vscode_config` role |
| Terraform | Terraform CLI, Terragrunt, TFLint, Checkov (Dev Container installs; CI mirrors tooling) |

All Python dependencies for the Ansible stack live in `requirements-ansible.txt` (referenced by a thin `requirements.txt` wrapper) and are installed system-wide in the container with `uv`. If you prefer an isolated virtual environment, run `uv venv .venv && uv pip install -r requirements-ansible.txt` inside the container; VS Code will automatically pick up `.venv` thanks to the defaults in `.vscode/settings.json`. Other stacks install only the tooling they need (for example, Terraform pins Terraform/Terragrunt/TFLint via the Dockerfile and installs Checkov with `uv pip install "checkov>=3.0.0,<4.0.0"`).

## Pinned Tool Versions

| Tool | Version | Notes |
| --- | --- | --- |
| Terraform | `1.13.x` | Terraform Dev Container pins `1.13.4`; CI tracks the latest patch in the 1.13 series. |
| Terragrunt | `0.54.x` | Installed globally in the Terraform container for Terragrunt workflows. |
| TFLint | `0.51.x` | Available in the Terraform container; initialise rules with `tflint --init`. |
| Checkov | `>=3.0.0,<4.0.0` | Installed via `uv`; run `checkov -d infrastructure/` for policy scans. |
| Ansible | `9.13.0` | Locked in `requirements-ansible.txt` / `uv.lock`; smoke playbooks enforce the version. |

Update this table whenever you bump toolchains so contributors stay aligned with CI.

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

GitHub Actions workflows are defined in `.github/workflows/`:

- `ci.yml` – installs dependencies with `uv`, lints YAML, runs `ansible-lint`, executes playbooks, validates Terraform, builds Dev Container images (Docker + Podman), lints Dockerfiles with `hadolint`, smoke-tests each stack, scans the resulting images with Trivy, lints shell/PowerShell scripts, and verifies published GHCR tags on `main`.
- `lint.yml` – fast yamllint + ansible-lint checks on YAML/Ansible changes.
- `release.yml` – publishes tagged releases, runs preflight container scans, signs GHCR images with cosign, uploads SPDX SBOMs, and smoke-tests the new GHCR tags with the Dev Containers CLI.

All jobs use Python 3.12 on `ubuntu-latest`. The shared toolchain mirrors the Dev Container ensuring parity between local development and CI.

## Repository Layout

```
.
├── .devcontainer/           # Dockerfile + devcontainer.json (uv-enabled)
├── .github/workflows/       # CI/CD pipelines
├── .vscode/                 # Local workspace defaults
├── inventory/               # Sample localhost inventory
├── playbooks/               # Ansible playbooks (setup + verification)
├── roles/                   # Role-based workspace provisioning
├── requirements-ansible.txt # Ansible stack Python dependencies consumed via uv
├── requirements.txt         # Compatibility wrapper referencing requirements-ansible.txt
├── requirements.yml         # Ansible collections
└── docs/                   # Documentation (bootstrap guides, roadmap, quick starts)
```

## Workspace Roles & Variables

| Role | Purpose | Key variables |
| --- | --- | --- |
| `devcontainer_base` | System packages, user creation, sudoers hardening, timezone | `devcontainer_base_user`, `devcontainer_base_timezone` |
| `ansible_environment` | Installs uv, Python requirements, Ansible collections, drops `ansible.cfg` & `.ansible-lint` | `ansible_environment_config_dir`, `ansible_environment_python_requirements_file`, `ansible_environment_collection_requirements_file`, `ansible_environment_uv_binary_path` |
| `python_tools` | Shell PATH tweaks and pytest config | `python_tools_devcontainer_user`, `python_tools_ansible_config_dir` |
| `vscode_config` | VS Code settings, extensions, tasks | `vscode_config_workspace_dir`, `vscode_config_python_interpreter_path` |
| `devcontainer_template` | Copies Dev Container template into `.devcontainer/` | `devcontainer_template_stack`, `devcontainer_template_root`, `devcontainer_template_target`, `devcontainer_template_clean` |

Override defaults in `roles/*/defaults/main.yml` or pass extra vars (`-e variable=value`) to tailor the workspace.

## Testing & Verification

- `./scripts/run-smoke-tests.sh` — fast smoke test that also asserts Ansible/ansible-core match the pinned requirements.
- `./scripts/run-ansible-tests.sh` — runs `ansible-test sanity` against every role (set `ANSIBLE_TEST_PYTHON_VERSION` to change the interpreter).
- `./scripts/check-devcontainer.sh` — builds each Dev Container template locally via the Dev Containers CLI (compatible with Docker Desktop or Podman).
- `./scripts/smoke-devcontainer-image.sh --stack <name> --build` — builds a stack image (base, ansible, terraform, golang, latex) and runs an end-to-end smoke check used in CI.
- `molecule test` — spins up Debian with all roles applied and verifies via Testinfra (`molecule/default/tests/test_default.py`).
- GitHub Actions runs linting, playbooks, Molecule, container build, and Go formatting/vet/test when a `go.mod` is present (see `.github/workflows/ci.yml`).
  The workflow also executes `ansible-test` sanity checks and a Podman-based Dev Container matrix to keep Docker/Podman parity.
- See [`docs/`](docs/README.md) for scenario walkthroughs (Terraform Proxmox, LaTeX résumé), corporate network tips, and the Windows bootstrap guide.

## Scenario Playbooks

Need inspiration for real-world workflows? Start with the scenario guides under [`docs/scenarios`](docs/scenarios):

- [`terraform-proxmox.md`](docs/scenarios/terraform-proxmox.md) — provisions the Proxmox homelab modules using the Terraform stack.
- [`latex-cv.md`](docs/scenarios/latex-cv.md) — compiles a LaTeX résumé with the LaTeX devcontainer and VS Code tasks.

Each scenario lists the recommended stack, prerequisite commands, and smoke tests so you can adapt them for demos or portfolio work.

## Customising the Environment

- Switch Dev Container stacks with `./scripts/use-devcontainer.sh [--prune] <ansible|golang|latex|terraform>` (or the PowerShell variant, `-Prune`). The script copies the chosen template from `devcontainers/<stack>` into `.devcontainer/`; add the prune flag to remove stopped containers and volumes tied to the workspace before reopening in VS Code.
- The LaTeX stack defaults to MiKTeX but accepts build args in `devcontainers/latex/devcontainer.json` (`LATEX_DISTRO`/`LATEX_IMAGE`). Set them to `texlive` and a TeX Live image (e.g. `ghcr.io/xu-cheng/texlive-full:latest`) to switch distributions without editing the Dockerfile.
- Add workspace-specific mounts or environment overrides in `.devcontainer/devcontainer.json`. For example, mount a host inventory and tweak Ansible caches:
  ```jsonc
  {
    "mounts": [
      "source=${localWorkspaceFolder},target=/workspace,type=bind",
      "source=/home/$USER/.ssh,target=/home/vscode/.ssh,type=bind,consistency=cached",
      "source=/home/$USER/ansible-inventory,target=/workspace/inventory/hosts,type=bind"
    ],
    "remoteEnv": {
      "ANSIBLE_INVENTORY": "/workspace/inventory/hosts",
      "ANSIBLE_GALAXY_CACHE_DIR": "/home/vscode/.ansible/galaxy_cache",
      "UV_CACHE_DIR": "/home/vscode/.cache/uv"
    }
  }
  ```
- Use `inventory/cloud-example.yml` as a starting point for remote or cloud inventories; copy it, replace the placeholder host data, and point `ANSIBLE_INVENTORY` (or update `ansible.cfg`) to the new file.
- Update `requirements-ansible.txt` and re-run `uv pip install --system --requirement requirements-ansible.txt` to add Python tooling (Molecule/Testinfra depends on `pytest-testinfra`, already included).
- Add collections to `requirements.yml` and rerun `ansible-galaxy collection install -r requirements.yml`.
- Adjust VS Code defaults by editing the templates under `roles/vscode_config/templates/` so the changes apply to every workspace bootstrap.
- Use `playbooks/setup-workspace.yml --tags …` to run only selected roles (e.g. `--tags vscode` to refresh editor settings).
- Set `workspace_stack=<stack>` when running `playbooks/setup-workspace.yml` to copy the matching Dev Container template automatically (handled by the `devcontainer_template` role; defaults to `ansible`; valid values: `ansible`, `golang`, `latex`, `terraform`).
- The workspace playbook sets `devcontainer_template_skip_when_unchanged: true`; metadata in `.devcontainer/.template-metadata.json` keeps track of the stack and template checksum so reruns only copy when the source changes.
- Override role defaults using the namespaced variables (for example `devcontainer_base_user`, `python_tools_ansible_config_dir`, or `vscode_config_workspace_dir`). Legacy variable names are still accepted for backward compatibility but will be removed in a future release.

### Using Podman for Dev Containers

- On Windows, run `scripts/bootstrap-wsl2.ps1 -UsePodman` to install Podman Desktop instead of Docker Desktop (no commercial licensing fees). Start the Podman machine afterwards: `podman machine init --now` (first run only) and `podman machine start`.
- In VS Code, set `"dev.containers.dockerPath": "podman"` in `.vscode/settings.json` (or user settings) so Remote Containers calls the Podman CLI. On Linux, ensure the Podman socket is available by enabling the user service (`systemctl --user enable --now podman.socket`).
- When using CLI workflows, export `DOCKER_HOST` from `podman system service --time=0` (Linux) or rely on Podman Desktop’s Docker API compatibility (Windows). The clean-up flags in `scripts/use-devcontainer.sh`/`.ps1` already work with Podman for removing stopped containers and volumes.
- To make the VS Code setting easy to adopt across the team, add `.vscode/settings.json` with:
  ```json
  {
    "dev.containers.dockerPath": "podman"
  }
  ```
  Commit it (or share via `.vscode.example/`) so Remote Containers targets Podman automatically when contributors clone the repo.
  The repository includes `.vscode/settings.example.json` if you want to distribute a starter config instead of committing the settings file directly.

### Dev Container Diagnostics

- `./scripts/debug-devcontainer.sh` — builds and brings up a chosen stack (default `ansible`) and optionally runs a command inside it. Handy for quickly testing `./scripts/run-smoke-tests.sh` or dropping into a shell without leaving VS Code.
- `./scripts/devcontainer-metadata.py` — inspects `.devcontainer/.template-metadata.json` and validates that the recorded signature still matches the template under `devcontainers/<stack>`. Exit code `0` means metadata matches, `2` indicates drift.
- `./scripts/devcontainer-diff.py` — shows file-level diffs between `.devcontainer/` and the source template (useful when metadata reports drift). Exit code `2` indicates differences were found.
- `./scripts/check-devcontainer.sh` — builds each Dev Container template locally via the Dev Containers CLI (compatible with Docker Desktop or Podman).
  Pair it with `DEVCONTAINER_CONTAINER_ENGINE=podman` to reproduce the CI job locally.
- See `docs/DEVCONTAINER_DEBUG.md` for end-to-end debugging workflows that combine these scripts.

## Dependency Management

- Dependencies are defined in `pyproject.toml` and locked via `uv.lock`. Run `uv lock && uv export --format requirements-txt --frozen --output requirements-ansible.txt` whenever you add or upgrade packages.
- Installations in the Dev Container and CI still consume `requirements-ansible.txt` (plus the lightweight `requirements.txt` wrapper) so downstream users without `uv` can keep using pip.
- To test upgrades locally:
  ```bash
  uv lock --upgrade package_name
  uv export --format requirements-txt --frozen --output requirements-ansible.txt
  ```
  Commit both `uv.lock` and the regenerated `requirements-ansible.txt`.
- You can automate the lock refresh with `ansible-playbook playbooks/update-dependencies.yml`. Pass `uv_http_proxy`, `uv_https_proxy`, `uv_index_url`, or `uv_no_proxy` as extra vars when running behind a corporate proxy.

## Testing

- `pre-commit run --all-files` – runs yamllint/ansible-lint/ruff/detect-secrets.
- `./scripts/run-ansible-tests.sh` – executes `ansible-test sanity` for every role (respects `ANSIBLE_TEST_PYTHON_VERSION`, defaults to the pinned Python).
- `ansible-playbook playbooks/setup-workspace.yml --check` – dry-run validation of the provisioning playbook.
- `./scripts/run-smoke-tests.sh` – convenience wrapper around `playbooks/test-environment.yml`; pass extra args to forward flags (e.g. `--check`).
- `./scripts/run-terraform-tests.sh` – formats (`terraform fmt -check`) and validates every Terraform module under `infrastructure/` (skips gracefully when no configs exist).
- `ansible-playbook playbooks/update-dependencies.yml` – regenerates `uv.lock` and `requirements-ansible.txt`.
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

## Portfolio & Narrative

- `docs/PORTFOLIO.md` captures the automation story behind this repo (useful for blog posts or personal branding).
- `docs/ROADMAP.md` lists planned enhancements such as extra Dev Containers, CV automation in LaTeX, and onboarding tooling.
- `docs/CHANGELOG.md` tracks notable changes between releases.
- `docs/SECRETS.md` explains how to handle credentials safely across Terraform and Ansible workflows.

## Windows Bootstrap

- Run `scripts/bootstrap-wsl2.ps1` from an elevated PowerShell session to install Windows Terminal, Git, VS Code, PowerShell 7, WSL2 + Ubuntu, your chosen container engine (Docker Desktop by default or Podman via `-UsePodman`), and the VS Code Remote extensions.
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
