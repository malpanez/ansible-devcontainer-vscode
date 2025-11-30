# Infrastructure Dev Containers for VS Code

[![CI Pipeline](https://github.com/malpanez/ansible-devcontainer-vscode/actions/workflows/ci.yml/badge.svg)](https://github.com/malpanez/ansible-devcontainer-vscode/actions/workflows/ci.yml)
[![Build Containers](https://github.com/malpanez/ansible-devcontainer-vscode/actions/workflows/build-containers.yml/badge.svg)](https://github.com/malpanez/ansible-devcontainer-vscode/actions/workflows/build-containers.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/malpanez/ansible-devcontainer-vscode/badge)](https://securityscorecards.dev/viewer/?uri=github.com/malpanez/ansible-devcontainer-vscode)
[![GHCR](https://img.shields.io/badge/GHCR-images-blue?logo=github)](https://github.com/malpanez?tab=packages&repo_name=ansible-devcontainer-vscode)
[![Renovate](https://img.shields.io/badge/renovate-enabled-brightgreen?logo=renovatebot)](https://github.com/malpanez/ansible-devcontainer-vscode/issues)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)
[![uv](https://img.shields.io/badge/uv-ready-00A3FF)](https://github.com/astral-sh/uv)

**Tool Versions:**
[![Terraform](https://img.shields.io/badge/terraform-1.14.0-7B42BC?logo=terraform)](https://www.terraform.io/)
[![Python](https://img.shields.io/badge/python-3.12.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Go](https://img.shields.io/badge/go-1.25-00ADD8?logo=go&logoColor=white)](https://go.dev/)
[![Ansible](https://img.shields.io/badge/ansible-9.x-EE0000?logo=ansible)](https://www.ansible.com/)

Modern, reproducible infrastructure development environments powered by VS Code Dev Containers and the `uv` Python toolchain. Open the repository in VS Code, pick the stack you need (Ansible, Terraform, Golang, or LaTeX), reopen in a container, and you are ready to lint, test, and ship automation from any platform (Windows + WSL2, macOS, or Linux).

## Highlights

- ⚡ **uv-first Python workflow** – dependency installs are fast and reproducible via `uv pip install --system --requirement requirements-ansible.txt` for the Ansible stack.
- 🐳 **Dev Container ready** – Dockerfile, features, extensions, and VS Code settings ship in the repo.
- 🤖 **Automation via Ansible** – `playbooks/setup-workspace.yml` provisions the container with roles for base OS tweaks, Ansible tooling, Python testing tools, and editor config.
- 🧩 **Multi-stack templates** – ship Ansible, Terraform, Golang, and LaTeX workspaces side-by-side; switch with a single helper script.
- 🧱 **Slim stack-specific images** – each stack is based on the leanest upstream image (Chainguard or slim Debian/Python) with layered cleanup for fast pulls.
- 📦 **GHCR-ready images** – Dockerfiles are optimised for publishing to `ghcr.io` so teams can pull prebuilt devcontainers instead of rebuilding locally.
- 🧪 **Quality gates baked in** – pre-commit hooks, `ansible-lint`, `yamllint`, Molecule/pytest harness, and GitHub Actions CI.
- 🪪 **Template-driven pre-commit** – `ensure-precommit` seeds the right hook config per stack and runs `uvx pre-commit` without bloating the images.
- 🔐 **Security conscious** – runs as non-root, includes Trivy scanning in CI, and keeps secrets out of the repo.
- 📣 **Responsible disclosure** – see [`SECURITY.md`](SECURITY.md) for reporting guidelines and supply-chain expectations.
- 🪟 **Windows bootstrap script** – run `scripts/bootstrap-windows.ps1` to enable WSL, configure proxies, and install Docker/VS Code with one command.

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

| Stack | Base image | Approx. size¹ | Included tooling | Cache mounts |
| --- | --- | --- | --- | --- |
| `ansible` | `python:3.12-slim-bookworm` (overrideable via `BASE_IMAGE`) | ~650 MB | uv-managed Python, Ansible + collections, `pre-commit`, `tini`, SSH/git utils | uv cache volume, Ansible Galaxy volume |
| `terraform` | multi-stage Debian (bookworm tools + runtime) | ~240 MB | Terraform CLI, Terragrunt, TFLint, SOPS, age, `uv` launcher | `${workspace}/.terraform.d/plugin-cache` bind |
| `golang` | `golang:1.25-alpine` (overrideable via `BASE_IMAGE`) | ~210 MB | Go toolchain, git, `uv` launcher, sudo minimal | Go module & build caches |
| `latex` | `debian:bookworm-slim` + Tectonic | ~320 MB | Tectonic CLI, git/perl helpers, `uv` launcher | `${HOME}/.cache/tectonic` bind |

¹Sizes are indicative for `linux/amd64` and vary slightly per architecture.

## Why not distroless or Alpine?

Dev Containers are interactive workstations: developers expect `bash`, package managers, `sudo`, and diagnostics tooling to be available. Distroless or scratch images deliberately omit those layers, which makes them great for production workloads but painful for day-to-day debugging. Alpine’s `musl` libc often breaks prebuilt Python wheels and forces slow source builds—exactly what we are trying to avoid when bootstrapping Ansible or `pre-commit`—so the Python stacks stay on slim Debian / Wolfi bases. The Go stack is the exception because it only needs the Go toolchain and busybox utilities, so `golang:1.25-alpine` keeps it lightweight without impacting DX.

## Image Publishing & GHCR

This repository publishes one image per stack (`devcontainer-ansible`, `devcontainer-terraform`, `devcontainer-golang`, `devcontainer-latex`). Tag pushes (via `.github/workflows/release.yml`) build every image for `linux/amd64` and `linux/arm64` (LaTeX ships on `amd64` only), upload build caches, and push both `:latest` and `:<tag>` variants to GHCR. The Ansible image accepts a `BASE_IMAGE` build arg so you can swap between `python:3.12-slim-bookworm` and `ghcr.io/chainguard-images/python:latest` without touching the Dockerfile.

> **Security hygiene** – `.github/workflows/build-containers.yml` runs on a weekly schedule so GHCR images automatically pick up Debian security fixes (`apt full-upgrade`) and refreshed tooling even when the repository is quiet.

To build or test images locally:

```bash
# Ansible stack (override BASE_IMAGE if you want to test the Chainguard variant)
docker build devcontainers/ansible \
  --build-arg BASE_IMAGE=python:3.12-slim-bookworm \
  -t ghcr.io/<org>/devcontainer-ansible:local

# Terraform stack (ships without Python, relies on uvx pre-commit)
docker build \
  --file devcontainers/terraform/Dockerfile \
  -t ghcr.io/<org>/devcontainer-terraform:local \
  .
```

You can now reference the local tag from `.devcontainer/devcontainer.json` or push it to GHCR with `docker push`.

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
| Terraform | `1.14.x` | Terraform Dev Container pins `1.14.0`; CI tracks the latest patch in the 1.14 series. |
| Terragrunt | `0.93.x` | Installed globally in the Terraform container for Terragrunt workflows. |
| TFLint | `0.60.x` | Available in the Terraform container; initialise rules with `tflint --init`. |
| SOPS | `3.11.x` | SOPS 3.11.0 for secrets management with age/PGP encryption. |
| age | `1.2.1` | Age encryption tool for SOPS workflows. |
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

- On Windows, run `scripts/bootstrap-windows.ps1 -ContainerEngine Podman` to install Podman Desktop instead of Docker Desktop (no commercial licensing fees). Start the Podman machine afterwards: `podman machine init --now` (first run only) and `podman machine start`.
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
- `./scripts/run-terraform-tests.sh` – formats (`terraform fmt -check`) and validates every Terraform module under `infrastructure/` (skips gracefully when no configs exist). Modules that depend on private providers (for example `infrastructure/proxmox_lab`) are skipped automatically in CI so they can be tested manually when the provider binaries are available.
- `.trivyignore` documents the temporary CVE allowlist applied to vendor-supplied Terraform tooling (age/sops/terragrunt/tflint). We keep the list short and revisit it whenever upstream ships patched binaries.
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
