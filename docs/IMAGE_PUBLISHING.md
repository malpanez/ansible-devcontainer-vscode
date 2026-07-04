# Image Publishing & GHCR


This repository publishes six container images to GHCR:

| Image                         | Variants | Platforms    | Purpose                                              |
| ----------------------------- | -------- | ------------ | ---------------------------------------------------- |
| `devcontainer-base`           | `py312`  | amd64, arm64 | Shared Python 3.12 base layer with uv and pre-commit |
| `devcontainer-ansible`        | `latest` | amd64, arm64 | Standard Ansible environment                         |
| `devcontainer-ansible-podman` | `latest` | amd64, arm64 | Ansible + Podman for rootless container workflows    |
| `devcontainer-terraform`      | `latest` | amd64, arm64 | Terraform + Terragrunt + TFLint + SOPS + age         |
| `devcontainer-golang`         | `latest` | amd64, arm64 | Go development environment                           |
| `devcontainer-latex`          | `latest` | amd64 only   | LaTeX with Tectonic engine                           |

Tag pushes (via `.github/workflows/release.yml`) and pushes to `main` trigger multi-arch builds, upload build caches, and push both `:latest` and `:<tag>` (for releases) or `:sha-<commit>` (for main branch) variants to GHCR.

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

Replace `<tag>` with the release you want to verify (for example `v1.2.3`). Published images are consumed from the public owner-level namespace such as `ghcr.io/malpanez/devcontainer-ansible:latest`; SBOMs ship as release workflow artifacts under the `devcontainer-sbom` name so you can audit dependencies alongside the signed image.

If a published image ever becomes unavailable or `latest` resolves to a broken manifest, run the manual GitHub Actions workflow `Repair GHCR Images` to republish `devcontainer-base` and the affected stack, then verify `docker pull` and `docker buildx imagetools inspect` against the public tags.

To reproduce the Ansible stack outside of the Dev Container run:

```bash
ansible-playbook playbooks/setup-workspace.yml -K
```
