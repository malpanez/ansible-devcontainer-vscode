# Windows WSL2 Onboarding

This guide automates the initial setup required for contributors using Windows so they can launch the Dev Container stacks with minimal manual configuration.

## Prerequisites

- Windows 11 (build 22000+) or Windows 10 (build 19044+) with administrator access.
- Virtualisation enabled in BIOS/UEFI.
- Internet connectivity with access to the Microsoft Store and GitHub.

## Quick Start

Open an elevated PowerShell session and run:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
irm https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/scripts/bootstrap-wsl2.ps1 | iex
```

The bootstrap script performs the following steps:

1. Installs or upgrades WSL2 with the default Ubuntu distribution.
2. Ensures the `wsl --install` prerequisites (VirtualMachinePlatform, Hyper-V) are enabled.
3. Installs Docker Desktop (or Podman if requested) with WSL integration enabled.
4. Configures WSL to use systemd, sets resource defaults, and enables automatic time synchronisation.
5. Installs VS Code (if missing) plus the "Dev Containers" extension.
6. Clones this repository inside the Ubuntu environment and launches VS Code connected to the Dev Container.

Once the script completes, Ubuntu automatically opens. Sign in with your GitHub credentials if prompted, then run:

```bash
/devcontainer_cli bootstrap
# or reopen the repository in VS Code (Ctrl+Shift+P → "Dev Containers: Reopen in Container")
```

## Manual Steps (Fallback)

If the automated flow cannot be used, follow these manual steps:

1. Install WSL2 and Ubuntu via `wsl --install -d Ubuntu`.
2. Install Docker Desktop and enable "Use the WSL 2 based engine" + integration for Ubuntu.
3. Install VS Code and the Dev Containers extension.
4. Inside Ubuntu, install Git and clone the repository:
   ```bash
   sudo apt update && sudo apt install -y git
   git clone https://github.com/malpanez/ansible-devcontainer-vscode.git
   cd ansible-devcontainer-vscode
   code .
   ```
5. When prompted by VS Code, reopen the workspace in the Dev Container.

## Next Steps

- Review [docs/ROADMAP.md](./ROADMAP.md) for upcoming work.
- Run the VS Code tasks "Devcontainer: Rebuild <stack>" to build the stack you need.
- Launch `./scripts/run-terraform-tests.sh` or `./scripts/run-ansible-tests.sh` to validate your tooling.

Please report issues or missing steps via GitHub Issues so the onboarding flow can continue improving.
