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

`.github/workflows/build-containers.yml` is the only workflow that publishes these images to GHCR. It runs on the daily schedule, on pushes to `main` that touch `devcontainers/**`, and on manual dispatch (one stack or all), and it is the only place that signs with cosign, attaches provenance attestations, and Grype-scans what it pushed. Scheduled and manual runs build without cache; push runs reuse the registry cache (`:buildcache-publish`) that every run re-exports, so they start from the layers of the last uncached build. The exceptions are `.github/workflows/release.yml`, which builds nothing and only adds release tags (`:<tag>`) to digests build-containers already published, and `.github/workflows/repair-ghcr.yml`, which republishes one stack on demand. `ci.yml` builds the images for testing but never pushes them.

Pushes to `main` produce multi-arch `:latest`, `:main` and `:sha-<commit>` (plus the derived `py<major><minor>` stream tag for the base); tag pushes via `release.yml` add only the immutable `:<tag>` (`:py<major><minor>-<tag>` for the base) to all six images, `devcontainer-ansible-podman` included, and never move the rolling tags.

`devcontainer-ansible` is built on the base image produced in the same run: `build-all` overrides the `BASE_IMAGE` build-arg with `devcontainer-base@<digest>` from the `build-base` job, so a published ansible image always contains the base published beside it. The digest pinned in `devcontainers/ansible/Dockerfile` is what local and PR builds resolve, and Renovate keeps it fresh.

> **Security hygiene** – `build-containers.yml` runs on a daily schedule (`0 3 * * *`) and builds every image **without cache** (`no-cache`), as do manual dispatches, so GHCR images pick up OS security fixes even when the repository is quiet. The cache has to be bypassed: BuildKit replays the cached upgrade layer (`apt-get full-upgrade`, `apk upgrade`) for as long as the Dockerfile and its pinned base digest are unchanged, so a cached rebuild republishes the same packages indefinitely while the run stays green. Push builds stay cached and are therefore at most ~24h behind.
>
> Images are published first and scanned second. When a scheduled or manual run finds fixable high/critical Grype findings in an image it has just built uncached, the run goes red: job `Base image has no fixable findings` for the base, the `build-all` matrix job for a stack (single-stack dispatches are not scanned). The image is already published, and rebuilding will not clear the finding: bump the pinned component (or widen the Dockerfile's upgrade step) that ships the vulnerable package, or record a justified exception in `.grype.yaml`. Push builds are not gated, because the next scheduled build clears on its own whatever was fixed since their cache was exported.

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

A release promotes images, it does not build them. On a version tag, `release.yml` does this for each of the six images:

1. Waits (up to two hours) until no `build-containers.yml` run is in progress on `main`, so it never reads tags a run is still moving, and fails when the tagged commit has build runs and none of them succeeded.
2. Takes the digest of `:sha-<commit>`, the gated build of the tagged commit. When that tag does not exist because the commit changed no image, it takes `:main` instead, but only if nothing under `devcontainers/` or `.github/workflows/build-containers.yml` changed between the commit `:main` was built from (its `org.opencontainers.image.revision` label) and the tagged one. An image with neither tag fails the release.
3. Verifies with cosign that `build-containers.yml` signed that digest on `main`, at the commit the revision label names.
4. Scans the digest again with the gate's policy (`.grype.yaml`, fixable high/critical findings block), since advisories may have been published after the image was gated.
5. Only when every image passed, adds the version tag to each exact digest (a `docker buildx imagetools create` dry run must reproduce the digest before any tag is written, and every tag is read back). An existing version tag is never moved to another digest.

The release notes list the digest of every image and the commit it was built from, and the release carries a [Syft](https://github.com/anchore/syft) SPDX SBOM of each released digest with its keyless cosign bundle (`.sigstore`); the same SBOMs are kept as the `devcontainer-sbom` workflow artifact. Verify a released image with:

```bash
cosign verify ghcr.io/malpanez/devcontainer-ansible:<tag> \
  --certificate-identity "https://github.com/malpanez/ansible-devcontainer-vscode/.github/workflows/build-containers.yml@refs/heads/main" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

Replace `<tag>` with the release you want to verify (for example `v1.2.3`). Releases whose notes have no *Container images* table (v1.3.29 and earlier) were rebuilt and signed by `release.yml` itself: verify those with `--certificate-identity "https://github.com/malpanez/ansible-devcontainer-vscode/.github/workflows/release.yml@refs/tags/<tag>"`. Published images are consumed from the public owner-level namespace such as `ghcr.io/malpanez/devcontainer-ansible:latest`.

If a published image ever becomes unavailable or `latest` resolves to a broken manifest, run the manual GitHub Actions workflow `Repair GHCR Images` to republish `devcontainer-base` and the affected stack, then verify `docker pull` and `docker buildx imagetools inspect` against the public tags.

To reproduce the Ansible stack outside of the Dev Container run:

```bash
ansible-playbook playbooks/setup-workspace.yml -K
```
