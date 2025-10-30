# Windows Bootstrap Guide

Use this guide to provision a brand-new Windows 11 laptop with everything required to run the devcontainers in this repository. The PowerShell helper script automates the high-friction steps (WSL enablement, proxy configuration, optional tooling installs) so you can focus on development.

## Prerequisites

- Windows 11 build 22621 or later (Windows 10 works but requires manual WSL prerequisites).
- Administrator access (the script must run elevated).
- Internet connectivity or access to your corporate software distribution channels.

## Quick Start

1. Open **PowerShell** as Administrator.
2. Clone or download this repository.
3. Run the bootstrap script (adjust parameters as needed):

   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
   .\scripts\bootstrap-windows.ps1 `
     -InstallDockerDesktop `
     -InstallVSCode `
     -HttpProxy "http://proxy.internal:8080" `
     -HttpsProxy "http://proxy.internal:8080" `
     -NoProxy "localhost,127.0.0.1,.corp.local"
   ```

4. Reboot if prompted after WSL installation.
5. Launch the requested WSL distribution (Ubuntu by default) and create your Linux user account.
6. Inside WSL, clone this repository and run `./scripts/use-devcontainer.sh <stack>` followed by **Dev Containers: Reopen in Container** in VS Code.

## Script Options

| Parameter | Description |
| --- | --- |
| `-Distribution <name>` | WSL distribution to install (default: `Ubuntu`). |
| `-InstallDockerDesktop` | Installs Docker Desktop via `winget`. |
| `-InstallPodmanDesktop` | Installs Podman Desktop via `winget`. |
| `-InstallVSCode` | Installs Visual Studio Code and the recommended extensions. |
| `-SkipGit` | Skip Git for Windows installation (installed by default). |
| `-HttpProxy` / `-HttpsProxy` / `-NoProxy` | Configure system/user environment variables for corporate proxies. |
| `-SkipWSL` | Skip enabling WSL features (useful on locked-down or CI machines). |

The script validates administrative privileges, enables the `VirtualMachinePlatform` and `Microsoft-Windows-Subsystem-Linux` features, and runs `wsl.exe --install` if the requested distribution is missing. When a proxy is specified, both uppercase and lowercase variants of the environment variables are populated for compatibility.

## Post-Bootstrap Tasks

- **Docker or Podman setup**: open the installed desktop app once to finish initialization, then sign in if your organisation requires it. For Docker Desktop, enable WSL integration for the chosen distribution.
- **VS Code remote extensions**: the script installs the Remote WSL/Containers extensions, but you may want to sign in with your GitHub / Azure account to sync settings.
- **Corporate certificate authorities**: import any internal CA bundles into Windows **and** the WSL distribution to avoid TLS errors. The Ansible roles accept `ansible_environment_uv_index_url` and proxy overrides if additional registries need to be trusted.
- **Clone repositories**: run `git clone https://github.com/<org>/<repo>.git` inside WSL to keep working directories on the Linux filesystem (`~/workspace`).

## Troubleshooting

- **winget missing** – install the latest [App Installer](https://www.microsoft.com/p/app-installer/9nblggh4nns1) from the Microsoft Store and rerun the script.
- **WSL install fails** – ensure virtualization is enabled in BIOS/UEFI and that Hyper-V is not disabled by Group Policy. Retry the script after enabling.
- **Corporate proxy prompts** – provide `-HttpProxy/-HttpsProxy` arguments or set them manually before running the script. Confirm access with `Invoke-WebRequest https://www.microsoft.com`.
- **Docker Desktop blocked** – use `-InstallPodmanDesktop` instead and configure the Podman socket for Dev Containers (`podman machine init --now`).
- **Script not recognized** – run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` before invoking the script to allow local execution.

For deeper context on proxy-aware workflows and offline mirrors, see `docs/CORPORATE_NETWORK.md`. If you encounter gaps, open an issue or submit a pull request with the adjustments needed for your environment. ***!
