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
[![Ansible](https://img.shields.io/badge/ansible--core-EE0000?logo=ansible)](https://www.ansible.com/)
[![Terraform](https://img.shields.io/badge/terraform-7B42BC?logo=terraform)](https://www.terraform.io/)
[![Go](https://img.shields.io/badge/go-00ADD8?logo=go&logoColor=white)](https://go.dev/)
[![Python](https://img.shields.io/badge/python-3776AB?logo=python&logoColor=white)](https://www.python.org/)

Pull a pre-built infrastructure workspace from GHCR and start writing Terraform or running Ansible in **under 30 seconds** — roughly 2–4× smaller than Microsoft's devcontainer images, with no local setup and no drift between machines. Pick the stack you need (Ansible, Terraform, Golang, or LaTeX), reopen in VS Code, and your entire toolchain is already installed, locked, and ready. Works on Windows + WSL2, macOS, and Linux.

## Highlights

- ⚡ **uv-first Python workflow** – dependency installs are fast and reproducible: `uv.lock` is the source of truth and the images install its hashed `requirements*.txt` exports with `uv pip install --require-hashes`.
- 🐳 **Dev Container ready** – Dockerfile, features, extensions, and VS Code settings ship in the repo.
- 🤖 **Automation via Ansible** – `playbooks/setup-workspace.yml` provisions the container with roles for base OS tweaks, Ansible tooling, Python testing tools, and editor config.
- 🧩 **Multi-stack templates** – ship Ansible, Terraform, Golang, and LaTeX workspaces side-by-side; switch with a single helper script.
- 🧱 **Slim stack-specific images** – each stack is based on the leanest upstream image (slim Debian/Python, or Alpine for Go) with layered cleanup for fast pulls.
- 📦 **GHCR-ready images** – Dockerfiles are optimised for publishing to `ghcr.io` so teams can pull prebuilt devcontainers instead of rebuilding locally.
- 🧪 **Quality gates baked in** – pre-commit hooks, `ansible-lint`, `yamllint`, Molecule/pytest harness, and GitHub Actions CI.
- 🪪 **Template-driven pre-commit** – every image ships pre-commit and yamllint at the versions `uv.lock` pins, and `ensure-precommit` seeds the right hook config per stack.
- 🔐 **Security conscious** – runs as non-root, gates every published image on a Grype scan, and keeps secrets out of the repo.
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

# Pick the stack you need (the repository ships with terraform active)
./scripts/use-devcontainer.sh terraform   # or ansible | golang | latex
# Or use: make switch-terraform

code .

# When prompted, choose "Dev Containers: Reopen in Container"
# VS Code pulls the stack's published GHCR image instead of building the Dockerfile.
```

Each stack comes in two variants, both copied into `.devcontainer/`:

- `devcontainer.json` opens the published image
  `ghcr.io/malpanez/devcontainer-<stack>:vX.Y.Z@sha256:…`, pinned to a release
  version tag plus that tag's index digest. Version tags are never rebuilt,
  moved or deleted, so the pin keeps pulling the image the release shipped;
  Renovate bumps the templates to each new release. Codespaces opens this one.
- `local-build/devcontainer.json` ("… (local build)") builds the stack's
  `Dockerfile` from this checkout, for working on the image itself. Its build
  context is `${localWorkspaceFolder}`, so the workspace folder must be the
  repository root: `devcontainer up --workspace-folder . --config .devcontainer/local-build/devcontainer.json`.

When **Reopen in Container** asks which configuration to open, pick the plain
stack name for the published image.

> **New Windows laptop?** Run [`scripts/bootstrap-windows.ps1`](scripts/bootstrap-windows.ps1) from an elevated PowerShell prompt (see [`docs/BOOTSTRAP_WINDOWS.md`](docs/BOOTSTRAP_WINDOWS.md)) to enable WSL, configure proxies, and install Docker Desktop / VS Code automatically.

## Pre-commit Strategy

Every stack ships with a ready-to-use `.pre-commit-config.yaml`, and every image ships `pre-commit` and `yamllint` at the exact versions in `uv.lock`, installed hash-verified at build time:

- **Ansible** gets them from `requirements-ansible.txt`, with the rest of its Python stack.
- **Base, Terraform, Golang and LaTeX** get them from `requirements-devcontainer-tools.txt`, the export of the lock's `devcontainer-tools` group. Base installs into its system Python. Terraform, Golang and LaTeX have no Python of their own, so they carry a root-owned venv at `/opt/devcontainer-tools`, on a uv-managed CPython pinned to the base image's version, with only `pre-commit` and `yamllint` linked into `/usr/local/bin`.

The image also bakes in `/usr/local/bin/ensure-precommit`, which the `postCreateCommand` runs. It:

1. Copies the right template from `/usr/local/share/devcontainer-skel/<stack>/` if the workspace does not provide one.
2. Runs `pre-commit install -f` with the image's pre-commit. It never installs pre-commit and never runs `pre-commit autoupdate`; an image without pre-commit is broken, and the script fails and says so.

## Available Stacks

| Stack       | Base image                                                                          | Size¹     | Included tooling                                                              | Cache mounts (named volumes)                         |
| ----------- | ----------------------------------------------------------------------------------- | --------- | ----------------------------------------------------------------------------- | ---------------------------------------------------- |
| `ansible`   | `devcontainer-base` (`python:3.14-slim-trixie`; `BASE_IMAGE` takes another base build) | 436 MiB   | uv-managed Python, Ansible + collections, `pre-commit`, SSH/git utils; the template runs it with `--init` | `uv-cache`, `ansible-galaxy-cache`                   |
| `terraform` | `debian:trixie-slim` (multi-stage: tools fetched in a separate stage)               | 669 MiB   | Terraform CLI, Terragrunt, TFLint, SOPS, age, `uv` launcher                   | `uv-cache`, `terraform-plugin-cache`                 |
| `golang`    | `golang:1.27-alpine3.23` (Alpine, musl; see the note below the table)               | 376 MiB   | Go toolchain, git, `uv` launcher                                              | `go-mod-cache`, `go-build-cache`                     |
| `latex`     | `debian:trixie-slim` + Tectonic                                                     | 335 MiB   | Tectonic CLI, git/perl helpers, `uv` launcher                                 | `tectonic-cache`, `uv-cache`, `pre-commit-cache`     |

¹Uncompressed size in MiB of the `linux/amd64` image (`docker image inspect` `.Size`, as CI's size gate measures it). `ansible-podman` is 518 MiB, `ansible-aws` 719 MiB, `terraform-aws` 918 MiB and the base 330 MiB. The limits CI enforces are in [`.github/image-size-budgets.json`](.github/image-size-budgets.json). `latex` is published for `linux/amd64` only; the other stacks also for `linux/arm64`.

> **Golang is the one Alpine (musl) image, and it is published for `linux/arm64`.** VS Code's [Linux requirements](https://code.visualstudio.com/docs/remote/linux) list "Alpine Linux 64-bit x86 containers or WSL hosts (3.16+)" as supported in Dev Containers and WSL, and warn: "Extensions installed in the container may not work due to `glibc` dependencies in extension native code." They call AArch64 "preview", because extensions there may ship only x86_64 native code. So on an arm64 host (Apple Silicon, Graviton) `devcontainer-golang` is outside what VS Code lists as supported, and an extension with native code can fail to start in it. If one does, use a Debian-based stack or build your own image on `golang:<version>-trixie`.

### AWS templates

`devcontainers/terraform/devcontainer.aws.json` and
`devcontainers/ansible/devcontainer.aws.json` open `devcontainer-terraform-aws`
and `devcontainer-ansible-aws`, the images with AWS CLI v2 (and, for Ansible,
`amazon.aws` and `boto3`). The plain terraform and ansible images have no
`aws` command.

- **No credentials are mounted.** The templates do not bind-mount the host's
  `~/.aws`, so they start on a machine that has none, and the container cannot
  read or change the host's credentials.
- **Forwarded variables.** `AWS_PROFILE`, `AWS_REGION` and `AWS_DEFAULT_REGION`
  reach the container only if they are set on the host, through
  `"runArgs": ["--env", "AWS_PROFILE", ...]`. A `remoteEnv` entry with
  `${localEnv:AWS_PROFILE}` would pass an empty string when the variable is
  unset, and the AWS CLI rejects that (`The config profile () could not be
  found`).
- **Logging in happens inside the container**: run `aws configure`, or
  `aws sso login --no-browser` and open the printed URL on the host. The login
  lives in the container's home and is lost when the container is rebuilt.
- **Using the host's `~/.aws` instead.** Add this entry to `mounts` in your
  copy of the template:

  ```json
  "source=${localEnv:HOME}/.aws,target=/home/vscode/.aws,type=bind,readonly"
  ```

  Trade-offs: with `readonly`, `aws sso login` cannot write its token cache;
  without it, anything in the container can change the host's credentials.
  Either way the container does not start if `~/.aws` does not exist on the
  host.

## Why not distroless or Alpine?

See [docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md).

## Image Publishing & GHCR

Images for every stack are built, scanned, attested and published to
GHCR by CI. See [docs/IMAGE_PUBLISHING.md](docs/IMAGE_PUBLISHING.md)
for tags, pull commands and the publishing pipeline.

## Toolchain Overview

The table below outlines the tooling shipped with the images (the sources of truth are listed under Pinned Tool Versions); the terraform images carry HashiCorp utilities plus pre-commit and yamllint, while Golang and LaTeX stay intentionally lean.

| Area             | Included tooling                                                                                                   |
| ---------------- | ------------------------------------------------------------------------------------------------------------------ |
| Provisioning     | `ansible-core`, ansible-navigator, ansible-builder (the `ansible` package and its bundled collections are not shipped) |
| Linting          | ansible-lint, yamllint, black, pre-commit (ansible images); TFLint (terraform images)                              |
| Python packaging | [`uv`](https://github.com/astral-sh/uv) for package installation and script execution                              |
| Collections      | `ansible.posix`, `community.general`, `community.docker` and their dependency `community.library_inventory_filtering_v1` (see `devcontainers/ansible/collections.txt`); `amazon.aws` only in `devcontainer-ansible-aws` (see `collections-aws.txt`). `kubernetes.core` is not shipped: install it from a `requirements.yml`. The repo-root `requirements.yml` is this repository's own dependency list, not the images' |
| VS Code          | Recommended extensions, workspace settings, and tasks delivered by the `vscode_config` role                        |
| Terraform        | Terraform CLI, Terragrunt, TFLint, SOPS, age (no `aws` command: use `devcontainer-terraform-aws`)                  |

The Python dependencies of the images are declared in `pyproject.toml` and locked in `uv.lock`; `requirements*.txt` are generated from the lock. If you prefer an isolated virtual environment, run `uv venv .venv && uv pip install -e .` inside the container; VS Code will automatically pick up `.venv` thanks to the defaults in `.vscode/settings.json`.

## Pinned Tool Versions

Tool versions are pinned at their single source of truth — duplicated
version tables rot:

- **Python packages**: `pyproject.toml` + `uv.lock` (exports:
  `requirements.txt`, `requirements-ansible.txt`, `requirements-aws.txt`)
- **CLI tools** (terraform, terragrunt, tflint, sops, age, uv, tectonic):
  `ARG *_VERSION` at the top of each `devcontainers/*/Dockerfile`, each
  download verified against its upstream checksum
- **AWS CLI** (only in `devcontainer-terraform-aws` and
  `devcontainer-ansible-aws`): `devcontainers/scripts/install-aws-cli.sh`,
  with the sha256 of each architecture's download
- **Base images**: digest-pinned `FROM` lines in the same Dockerfiles

## Local Workflow

1. **Open the repo with VS Code** and reopen it in the Dev Container.
2. **Run the bootstrap playbook** if you need to reconfigure the workspace manually:
   ```bash
   ansible-playbook playbooks/setup-workspace.yml --tags base,ansible
   ```
   The play escalates with `sudo` (`become: true`), which the images do not carry: run it on a host (WSL, a VM), not inside a published image. `ansible.cfg` no longer enables `become` for every play, so `ansible-playbook playbooks/test-environment.yml` and `update-dependencies.yml` run unprivileged inside the container.
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

- `ci.yml` – runs repository-wide `uvx pre-commit run --all-files`, lints shell and PowerShell scripts, keeps Go/Terraform checks, builds the Dev Container images whose inputs changed (`linux/amd64`), gates them on the size budgets in `.github/image-size-budgets.json`, smoke-tests them, and scans them with Grype (`.grype.yaml`: fixable high/critical findings block), plus `hadolint`. Publishing is not done here: see `build-containers.yml`.
- `build-containers.yml` – the only workflow that publishes `latest`, `main` and the Python stream tag: daily and on pushes to `main`, uncached, Grype-gated, signed and attested.
- `release.yml` – on a version tag, verifies the cosign signature of the image digests `build-containers.yml` built and gated, re-scans them with Grype, adds the version tag to those exact digests and attaches signed SBOMs to the GitHub release. It builds nothing.

CI takes its Python, Go and Terraform versions from the Dockerfiles (`scripts/derive-toolchain-versions.sh`), so it tests the toolchain the images ship.

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
| `devcontainer_base`     | System packages, user creation, a NOPASSWD sudo rule for that user, timezone (host provisioning; no image runs this role)                            | `devcontainer_base_user`, `devcontainer_base_timezone`                                                                                                                     |
| `ansible_environment`   | Installs uv, Python requirements, Ansible collections, drops `ansible.cfg` & `.ansible-lint` | `ansible_environment_config_dir`, `ansible_environment_python_requirements_file`, `ansible_environment_collection_requirements_file`, `ansible_environment_uv_binary_path` |
| `python_tools`          | Shell PATH tweaks and pytest config                                                          | `python_tools_devcontainer_user`, `python_tools_ansible_config_dir`                                                                                                        |
| `vscode_config`         | VS Code settings, extensions, tasks                                                          | `vscode_config_workspace_dir`, `vscode_config_python_interpreter_path`                                                                                                     |
| `devcontainer_template` | Copies Dev Container template into `.devcontainer/`                                          | `devcontainer_template_stack`, `devcontainer_template_root`, `devcontainer_template_target`, `devcontainer_template_clean`                                                 |

Override defaults in `roles/*/defaults/main.yml` or pass extra vars (`-e variable=value`) to tailor the workspace.

## Testing & Verification

- `./scripts/run-smoke-tests.sh` — fast smoke test that also asserts Ansible/ansible-core match the pinned requirements.
- `./scripts/run-ansible-tests.sh` — runs `ansible-test sanity` against every role (set `ANSIBLE_TEST_PYTHON_VERSION` to change the interpreter).
- `./scripts/smoke-devcontainer-image.sh` — builds a Dev Container image and runs per-stack smoke checks (compatible with Docker Desktop or Podman).
- `./scripts/smoke-devcontainer-image.sh --stack <name> --build` — builds a stack image (`ansible`, `ansible-aws`, `terraform`, `terraform-aws`, `golang`, `latex`) and runs an end-to-end smoke check used in CI.
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

- Dependencies are defined in `pyproject.toml` and locked via `uv.lock`. Run `uv lock` whenever you add or upgrade packages. The `requirements*.txt` files are generated from the lock (hashed), and the image builds install those with `uv pip install --require-hashes`.
- To test upgrades locally:
  ```bash
  uv lock --upgrade package_name
  ```
  Commit `uv.lock` and the updated `pyproject.toml`, then regenerate the `requirements*.txt` exports (`renovate-postprocess.yml` does it for Renovate's PRs). `uv pip install --system` cannot write to `/usr/local` as `vscode` inside a published image.
- You can automate the lock refresh with `ansible-playbook playbooks/update-dependencies.yml`. Pass `uv_http_proxy`, `uv_https_proxy`, `uv_index_url`, or `uv_no_proxy` as extra vars when running behind a corporate proxy.

## Testing

- `pre-commit run --all-files` – runs yamllint/ansible-lint/ruff/detect-secrets.
- `./scripts/run-ansible-tests.sh` – executes `ansible-test sanity` for every role (respects `ANSIBLE_TEST_PYTHON_VERSION`, defaults to the pinned Python).
- `ansible-playbook playbooks/setup-workspace.yml --check` – dry-run validation of the provisioning playbook.
- `./scripts/run-smoke-tests.sh` – convenience wrapper around `playbooks/test-environment.yml`; pass extra args to forward flags (e.g. `--check`).
- `./scripts/run-terraform-tests.sh` – formats (`terraform fmt -check`) and validates every Terraform module under `infrastructure/` (skips gracefully when no configs exist). Modules that depend on private providers (for example `infrastructure/proxmox_lab`) are skipped automatically in CI so they can be tested manually when the provider binaries are available.
- `.grype.yaml` holds the justified CVE exceptions for the image scan gate (for example the CPython bundled by the AWS CLI). Each entry carries its reason, and the list is kept short.
- `ansible-playbook playbooks/update-dependencies.yml` – regenerates `uv.lock` from `pyproject.toml`.
- `molecule test` – full integration verification.
  Run `molecule test --scenario-name latex` to exercise the latex template copy.
- `tflint --init && tflint` – optional Terraform lint (configure rules in `infrastructure/.tflint.hcl`).
- `checkov -d infrastructure/` – run policy-as-code scans locally; Checkov is not in the images, install it with `uv tool install checkov`.

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

- 🔒 **Grype Scanning**: Every published image is scanned for CVEs before it is tagged (`build-containers.yml`), and again at release
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
- **🚀 Direct Pull**: git and github-cli (gh) are pre-installed in the images, and AWS CLI v2 in the `-aws` variants, eliminating the need for DevContainer features that trigger rebuilds
- **🔧 Pre-commit Permissions**: Fixed permission issues with gitleaks/Go cache by setting `PRE_COMMIT_HOME` and ensuring proper cache directory ownership

### Using DevContainers in Your Projects

Want to use these production-ready containers in your own Ansible or Terraform projects? See:

- **[INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md)** - Complete integration guide with setup instructions, pre-commit hooks explanation, and troubleshooting
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
