# Corporate & Restricted Network Guide

Some organisations run Windows + WSL2 behind VPNs, TLS interception, or authenticated proxies. This guide lists the extra steps needed so the Dev Container toolchain can install dependencies reliably in those environments.

> **Scope** – the instructions assume Windows 10/11 with WSL2 (Ubuntu) and Docker Desktop. Adapt the proxy hostnames/ports to match your corporate infrastructure.

> **Note on container engines** – the Windows bootstrap script can install Docker Desktop (default) or Podman (`-ContainerEngine Podman`). Podman avoids Docker Desktop’s commercial licensing requirements while still enabling VS Code Dev Container workflows.

If you opt for Podman:

- **Windows** – install Podman Desktop, then run `podman machine init --now` (first time) and `podman machine start` before launching VS Code. Podman Desktop exposes a Docker-compatible socket automatically.
- **Linux** – enable the user socket so VS Code can reach the Podman API:
  ```bash
  systemctl --user enable --now podman.socket
  export DOCKER_HOST=unix://$(podman info --format '{{ .Host.RemoteSocket.Path }}')
  ```
- **VS Code** – add `"dev.containers.dockerPath": "podman"` to your settings so the Remote Containers extension invokes the Podman CLI.
- **Smoke tests** – run `./scripts/check-devcontainer.sh` (builds every template) or `./scripts/debug-devcontainer.sh --stack <name> -- ./scripts/run-smoke-tests.sh` to validate container engines behind the firewall.

## 1. VPN Access for Docker Desktop

1. **Install the Docker Desktop “VPNKit” distro**
   - Open PowerShell as Administrator.
   - Run:
     ```powershell
     wsl --install --distribution docker-desktop-data
     wsl --install --distribution docker-desktop
     ```
   - Launch Docker Desktop once so it completes the VPNKit setup.
2. In Docker Desktop → Settings → Resources → Network, ensure **“VPN compatibility mode”** is enabled if your corporate VPN blocks the default hypervisor networking.

## 2. Configure Proxy Settings

### Windows Host (Docker Desktop)
- Docker Desktop → Settings → Resources → Proxies → enter your corporate HTTP/HTTPS proxy URLs.
- Alternatively set the environment variables in PowerShell:
  ```powershell
  setx HTTP_PROXY http://proxy.corp.example:8080
  setx HTTPS_PROXY http://proxy.corp.example:8443
  ```
  Restart Docker Desktop afterwards.

### WSL2 Ubuntu
Add the proxy to `/etc/environment` so it applies to shell sessions:

```bash
sudo tee -a /etc/environment <<'EOF'
HTTP_PROXY=http://proxy.corp.example:8080
HTTPS_PROXY=http://proxy.corp.example:8443
NO_PROXY=localhost,127.0.0.1,::1,.corp.example
EOF
```

Also export the variables in `~/.bashrc` (or `~/.profile`) so `uv`, `pip`, and `ansible-galaxy` inherit them when you work inside the Dev Container:

```bash
export HTTP_PROXY=http://proxy.corp.example:8080
export HTTPS_PROXY=http://proxy.corp.example:8443
export NO_PROXY=localhost,127.0.0.1,::1,.corp.example
```

When running the automation playbooks directly, you can also pass proxy settings as extra vars so they flow into the Dev Container provisioning:

```bash
ansible-playbook playbooks/setup-workspace.yml \
  -e ansible_environment_http_proxy=http://proxy.corp.example:8080 \
  -e ansible_environment_https_proxy=http://proxy.corp.example:8443 \
  -e ansible_environment_no_proxy=localhost,127.0.0.1,::1,.corp.example \
  -e ansible_environment_uv_index_url=https://artifactory.corp/pypi/simple
```

### Git
If Git is behind TLS interception, configure it once:

```bash
git config --global http.proxy http://proxy.corp.example:8080
git config --global https.proxy http://proxy.corp.example:8443
```

## 3. Trust Internal Certificates

If your organisation MITM’s TLS connections, export the corporate CA certificate (usually a `.cer` or `.pem` file) from Windows’ certificate manager and copy it into WSL:

```bash
sudo cp corp-root-ca.pem /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

For the Dev Container:
1. Place the certificate in `.devcontainer/certs/` (create the directory if absent).
2. Extend `.devcontainer/Dockerfile` with:
   ```dockerfile
   COPY certs/*.pem /usr/local/share/ca-certificates/
   RUN update-ca-certificates
   ```
3. Rebuild the container so tools such as `uv`, `ansible-galaxy`, and `docker` trust your internal CA.

## 4. Use an Internal Package Mirror

If direct internet access is blocked, mirror the upstream feeds through your company’s Artifactory/Nexus:

| Tool | Override | Example |
| --- | --- | --- |
| `uv` / `pip` | `UV_INDEX_URL` / `PIP_INDEX_URL` | `export UV_INDEX_URL="https://artifactory.corp/pypi/simple"` |
| `ansible-galaxy` | `ansible.cfg` → `galaxy_server:` | Edit `roles/ansible_environment/templates/ansible.cfg.j2` to point to the mirror |
| Docker builds | Docker Desktop → Settings → Proxies; optionally configure `~/.docker/config.json` with `"proxies"` |

When cloning collections or roles from GitHub is blocked, preload them into `collections/ansible_collections` and rebuild the Dev Container so they are available offline.

## 5. Dev Container Build Flags

Add the following to `.devcontainer/devcontainer.json` when you need to pass proxy settings into the container at build time:

```json
"build": {
  "dockerfile": "Dockerfile",
  "context": "..",
  "args": {
    "HTTP_PROXY": "${localEnv:HTTP_PROXY}",
    "HTTPS_PROXY": "${localEnv:HTTPS_PROXY}",
    "NO_PROXY": "${localEnv:NO_PROXY}"
  }
},
"remoteEnv": {
  "HTTP_PROXY": "${localEnv:HTTP_PROXY}",
  "HTTPS_PROXY": "${localEnv:HTTPS_PROXY}",
  "NO_PROXY": "${localEnv:NO_PROXY}"
}
```

Ensure those variables are defined in your Windows environment before launching VS Code.

## 6. Offline Bootstrap Checklist

If you must work fully offline:

1. Mirror the Ansible stack's `requirements-ansible.txt` packages with `uv pip download -r requirements-ansible.txt --dest ./wheelhouse`.
2. Mirror Ansible collections: `ansible-galaxy collection download -r requirements.yml --download-path collections/offline`.
3. Mount the mirrors inside the Dev Container and configure `UV_INDEX_URL=file:///workspace/wheelhouse`.
4. Run `ansible-playbook playbooks/setup-workspace.yml --extra-vars "uv_index_url=file:///workspace/wheelhouse ansible_galaxy_offline_path=/workspace/collections/offline"`.

Document the commands in your team wiki so future contributors can reuse the cache.

## 7. Troubleshooting

- **Docker Desktop fails behind VPN** – reinstall Docker Desktop with the latest WSL kernel; verify that the `docker-desktop` WSL distro is running (`wsl -l -v`).
- **Slow package installs** – enable the named caches we ship (`uv-cache`, `ansible-galaxy-cache`) and use the mirrors mentioned above.
- **SSH host key errors** – corporate proxies sometimes block SSH; switch to HTTPS clones or configure an internal Git mirror.

Keeping this guidance close to the source means new developers can get unblocked quickly even on tightly-controlled networks. Feel free to customise the values to match your environment and submit pull requests if additional scenarios need coverage.
