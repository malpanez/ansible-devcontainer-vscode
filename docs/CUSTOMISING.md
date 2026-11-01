# Customising the Environment


- Switch Dev Container stacks with `./scripts/use-devcontainer.sh [--prune] <ansible|golang|latex|terraform>` (or the PowerShell variant, `-Prune`). The script copies the chosen template from `devcontainers/<stack>` into `.devcontainer/`; add the prune flag to remove stopped containers and volumes tied to the workspace before reopening in VS Code.
- The LaTeX stack compiles with Tectonic only. `devcontainers/latex/devcontainer.json` opens the published image and has no build args or distribution switch; to use TeX Live or MiKTeX, build your own image and point `"image"` (or `build`) at it. The Dockerfile's own args are `TECTONIC_VERSION` and `UV_VERSION`.
- Dev Container configuration has no `extends`: the reference at https://containers.dev/implementors/json_reference/ defines none. Copy a template into `.devcontainer/` and edit it, build your own image `FROM` a published one, or add `features`. The properties that matter for the user are `remoteUser` (the templates set `vscode`), `containerUser` (overrides the user for all operations in the container; defaults to `root` or the image's last `USER`) and `updateRemoteUserUID` (on Linux, when `containerUser` or `remoteUser` is set, it changes that user's UID/GID to the host user's to avoid bind-mount permission problems; defaults to `true`).
- Git inside the container: the Dev Containers extension copies the host's `.gitconfig` in on start, and sharing credentials is by SSH agent forwarding (run `ssh-add` on the host, with the agent running; on Windows start the OpenSSH Authentication Agent service) or the host's credential helper, per https://code.visualstudio.com/remote/advancedcontainers/sharing-git-credentials. Prefer that to bind-mounting `~/.ssh`. This repository's CI checks the `.gitconfig` copy (`scripts/check-devcontainer-workload.sh`) because the extension skips it when `~/.gitconfig` has sections other than `filter` and `safe` (observed on extension 0.471.0).
- Add workspace-specific mounts or environment overrides in `.devcontainer/devcontainer.json`. For example, mount a host inventory and tweak Ansible caches:
  ```jsonc
  {
    "mounts": [
      "source=${localWorkspaceFolder},target=/workspace,type=bind",
      "source=/home/$USER/.ssh,target=/home/vscode/.ssh,type=bind,consistency=cached",
      "source=/home/$USER/ansible-inventory,target=/workspace/inventory/hosts,type=bind",
    ],
    "remoteEnv": {
      "ANSIBLE_INVENTORY": "/workspace/inventory/hosts",
      "ANSIBLE_GALAXY_CACHE_DIR": "/home/vscode/.ansible/galaxy_cache",
      "UV_CACHE_DIR": "/home/vscode/.cache/uv",
    },
  }
  ```
- Use `inventory/cloud-example.yml` as a starting point for remote or cloud inventories; copy it, replace the placeholder host data, and point `ANSIBLE_INVENTORY` (or update `ansible.cfg`) to the new file.
- Update `pyproject.toml` dependencies and re-run `uv lock` to add Python tooling to the lock (Molecule/Testinfra depends on `pytest-testinfra`, already included). The images install the hashed `requirements*.txt` exports of the lock at build time; inside a running container `/usr/local` is root-owned, so try an addition in a virtual environment (`uv venv .venv && uv pip install <package>`).
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

- `./scripts/doctor-devcontainer.sh` — one-shot health check for the active `.devcontainer/`; validates metadata, compares the active files against the template, and reports whether local container tooling is installed. Add `--strict` when you want missing local tooling to fail the run.
- `./scripts/debug-devcontainer.sh` — builds and brings up a chosen stack (default `ansible`) and optionally runs a command inside it. Handy for quickly testing `./scripts/run-smoke-tests.sh` or dropping into a shell without leaving VS Code.
- `./scripts/devcontainer-metadata.py` — inspects `.devcontainer/.template-metadata.json` and validates that the recorded signature still matches the template under `devcontainers/<stack>`. Exit code `0` means metadata matches, `2` indicates drift.
- `./scripts/devcontainer-diff.py` — shows file-level diffs between `.devcontainer/` and the source template (useful when metadata reports drift). Exit code `2` indicates differences were found.
- `./scripts/smoke-devcontainer-image.sh` — builds a Dev Container image and runs per-stack smoke checks (compatible with Docker Desktop or Podman).
  Pair it with `DEVCONTAINER_CONTAINER_ENGINE=podman` to reproduce the CI job locally.
- See `docs/DEVCONTAINER_DEBUG.md` for end-to-end debugging workflows that combine these scripts.
