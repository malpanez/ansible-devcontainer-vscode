# Image Publishing & GHCR


This repository publishes six container images to GHCR:

| Image                         | Variants | Platforms    | Purpose                                              |
| ----------------------------- | -------- | ------------ | ---------------------------------------------------- |
| `devcontainer-base`           | derived `py<major><minor>`, `main`, `latest` | amd64, arm64 | Python base layer with uv and pre-commit; the stream tag comes from `scripts/derive-python-tag.sh`, never hardcoded |
| `devcontainer-ansible`        | `latest` | amd64, arm64 | Standard Ansible environment                         |
| `devcontainer-ansible-podman` | `latest` | amd64, arm64 | Ansible + Podman for rootless container workflows    |
| `devcontainer-terraform`      | `latest` | amd64, arm64 | Terraform + Terragrunt + TFLint + SOPS + age         |
| `devcontainer-golang`         | `latest` | amd64, arm64 | Go development environment                           |
| `devcontainer-latex`          | `latest` | amd64 only   | LaTeX with Tectonic engine                           |

`.github/workflows/build-containers.yml` is the only workflow that publishes these images to GHCR. It runs on the daily schedule, on pushes to `main` that touch `devcontainers/**`, and on manual dispatch (one stack or all), and it is the only place that signs with cosign, attaches provenance attestations, and Grype-scans what it pushed. The single exception is `.github/workflows/release.yml`, which owns release tags (`:<tag>`), and `.github/workflows/repair-ghcr.yml`, which republishes one stack on demand. `ci.yml` builds the images for testing but never pushes them.

Pushes to `main` produce multi-arch `:latest`, `:main` and `:sha-<commit>` (plus the derived `py<major><minor>` stream tag for the base); tag pushes via `release.yml` produce `:latest` and `:<tag>`.

`devcontainer-ansible` is built on the base image produced in the same run: `build-all` overrides the `BASE_IMAGE` build-arg with `devcontainer-base@<digest>` from the `build-base` job, so a published ansible image always contains the base published beside it. The digest pinned in `devcontainers/ansible/Dockerfile` is what local and PR builds resolve, and Renovate keeps it fresh.

> **Security hygiene** – `build-containers.yml` runs on a daily schedule (`0 3 * * *`) so GHCR images automatically pick up Debian security fixes (`apt full-upgrade`) and refreshed tooling even when the repository is quiet.

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
