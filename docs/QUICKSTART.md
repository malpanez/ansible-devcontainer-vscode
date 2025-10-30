# Quick Start – Ansible DevContainer

This guide walks through configuring a Windows 11 workstation with WSL2 and VS Code to use this repository. The same steps (minus WSL) apply on macOS or Linux.

## 1. Prepare the host

### Windows + WSL2

> In a hurry? Run `.\scripts\bootstrap-windows.ps1 -InstallDockerDesktop -InstallVSCode` from an elevated PowerShell window to automate the WSL, Docker, and VS Code setup. See [docs/BOOTSTRAP_WINDOWS.md](BOOTSTRAP_WINDOWS.md) for the full parameter list and troubleshooting tips.

1. Open PowerShell as Administrator and enable WSL2 if you have not already:
   ```powershell
   wsl --install
   ```
2. Reboot when prompted.
3. Launch the Ubuntu distribution from the Microsoft Store and create your user.
4. Choose a container engine:
   - **Docker Desktop** – install it and enable **“Use the WSL 2 based engine”** plus Ubuntu under **Settings → Resources → WSL Integration**.
   - **Podman Desktop** – install from [podman-desktop.io](https://podman-desktop.io/), launch it once, then run `podman machine init --now` (first time only). Ensure `podman machine start` succeeds whenever you sign in.
5. Install [Visual Studio Code](https://code.visualstudio.com/) plus the extensions **Remote – WSL** and **Dev Containers**.
6. (Podman only) Open VS Code user/workspace settings and set `dev.containers.dockerPath` to `podman` (the repo ships `.vscode/settings.example.json` with this entry).

### macOS / Linux

Install Docker Desktop, Docker Engine, or Podman, Visual Studio Code, and the Dev Containers extension.

## 2. Clone the repository (inside WSL)

1. Launch **Windows Terminal** → **Ubuntu** (or open the WSL shell from VS Code via `Ctrl+Shift+P` → `Remote-WSL: New Window Using Distro...`).
2. Clone and open the workspace:
   ```bash
   git clone https://github.com/malpanez/ansible-devcontainer-vscode.git
   cd ansible-devcontainer-vscode
   code .
   ```
3. VS Code opens a WSL window. Wait until the lower-left status bar shows `WSL: Ubuntu`.

## 3. Choose a Dev Container stack (before the first reopen)

By default the repository launches the **ansible** stack. Available templates include `ansible`, `golang`, `latex`, and `terraform`. To select another stack before the initial build:

1. In the WSL terminal (repo root):
   ```bash
   ./scripts/use-devcontainer.sh latex      # or golang / terraform / ansible
   ```
   - Append `--prune` to remove stopped containers/volumes.
   - On PowerShell use `./scripts/use-devcontainer.ps1 -Stack latex`.
2. (Optional) Run the workspace playbook so Ansible copies the matching template now:
   ```bash
   ansible-playbook playbooks/setup-workspace.yml -e workspace_stack=latex
   ```

If you skip these steps the first container build uses the ansible template. You can revisit this later and rebuild the container to switch stacks.

## 4. Reopen the folder in the Dev Container

1. In VS Code click **“Reopen in Container”** when prompted. If the toast does not appear, use `Ctrl+Shift+P` → **“Dev Containers: Reopen in Container”**.
2. Ensure your container engine is running:
   - Docker Desktop: the whale icon should be active and the Ubuntu distro enabled under WSL Integration.
   - Podman Desktop: start Podman Desktop (or `podman machine start`) so the Docker-compatible socket is available.
3. The Dev Container build runs inside WSL and may take several minutes on first run. Subsequent rebuilds are faster thanks to cached layers.
4. When the build finishes the status bar shows `Dev Container: <stack>`; you are now inside the container.

## 5. What happens during the build

- VS Code pulls the prebuilt GHCR image for the selected stack (Ansible by default); Python stacks share the `devcontainer-base:py312` layer.
- The image already includes system packages and `uv`; only stack-specific tooling needs to install at runtime.
- For the Ansible stack the `postCreateCommand` installs collections via `ansible-galaxy collection install -r requirements.yml`.
- Workspace playbooks/roles are available under `/workspace`.

## 6. Validate the environment

Open the integrated terminal inside the Dev Container and run:

```bash
ansible --version
ansible-lint --version
uv --version
ansible-playbook playbooks/test-environment.yml
```

All commands should succeed without additional configuration.

## 7. Daily workflow

| Task | Command |
| --- | --- |
| Format & lint everything | `pre-commit run --all-files` |
| Check playbook syntax | `ansible-playbook playbooks/*.yml --syntax-check` |
| Run smoke test | `ansible-playbook playbooks/test-environment.yml` |
| Install new Python dependencies (Ansible stack) | `uv pip install --system --requirement requirements-ansible.txt` |
| Install new collections | `ansible-galaxy collection install -r requirements.yml` |
| Validate Terraform modules | `./scripts/run-terraform-tests.sh` |

Terraform modules live under `infrastructure/`. Start with
`infrastructure/proxmox_lab/README.md` for a guided example, and keep secrets
out of git by following `docs/SECRETS.md`.

You can also use VS Code tasks (`Ctrl+Shift+B`) to run the most common lint/test commands.

## 8. Troubleshooting

- **Container rebuilds are slow** – run `Dev Containers: Rebuild Without Cache` only after dependency changes; otherwise `Dev Containers: Rebuild Container` reuses cached layers.
- **Missing binaries** – ensure `uv` is on the PATH (`which uv`). If not, rerun `curl -LsSf https://astral.sh/uv/install.sh | sh` inside the container.
- **Ansible collections out of date** – rerun `ansible-galaxy collection install -r requirements.yml`.
- **WSL cannot access Docker** – open Docker Desktop and ensure the Ubuntu distribution is enabled under Settings → Resources → WSL Integration.
- **VS Code cannot talk to Podman** – verify `podman machine start` succeeds, then ensure `dev.containers.dockerPath` is set to `podman` and the Podman Desktop Docker API is enabled under Settings → Connections.
- **Need to debug a failing Dev Container** – use `./scripts/debug-devcontainer.sh --stack <name>` to build, start, and open a shell (or run any command) inside the template via the Dev Containers CLI.
- **Metadata says “mismatch”** – run `./scripts/devcontainer-metadata.py` to compare `.devcontainer/.template-metadata.json` against the source template and identify drift.

## 9. Swap stacks after the first build

1. Run the stack switcher again from the WSL shell:
   ```bash
   ./scripts/use-devcontainer.sh golang
   ```
   (Use the PowerShell variant for Windows-native shells.)
2. Reopen the project with `Ctrl+Shift+P` → **Dev Containers: Rebuild Container** so the new template is copied and the image rebuilds.

## 10. Next steps

- Customise VS Code defaults by editing the templates in `roles/vscode_config/templates/` and re-running `ansible-playbook playbooks/setup-workspace.yml --tags vscode`.
- Extend the Ansible Python toolchain by appending to `requirements-ansible.txt` and running `uv pip install --system --requirement requirements-ansible.txt`.
- Hook this repository into your own projects by adding additional roles or playbooks.
- Review `docs/DEVCONTAINER_DEBUG.md` for tips when a container build misbehaves or you need to verify Podman vs Docker behaviour.
