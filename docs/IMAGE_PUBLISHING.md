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

`.github/workflows/build-containers.yml` is the only workflow that publishes these images to GHCR. It runs on the daily schedule, on pushes to `main` that touch `devcontainers/**`, and on manual dispatch (one stack or all), and it is the only place that signs with cosign, attaches provenance attestations, and Grype-scans what it pushed. Scheduled and manual runs build without cache; push runs reuse the registry cache (`:buildcache-publish`) that every run re-exports, so they start from the layers of the last uncached build. The one exception is `.github/workflows/release.yml`, which builds nothing and only adds release tags (`:<tag>`) to digests build-containers already published. `ci.yml` builds the images for testing but never pushes them.

Pushes to `main` produce multi-arch `:latest`, `:main` and `:sha-<commit>` (plus the derived `py<major><minor>` stream tag for the base); tag pushes via `release.yml` add only the immutable `:<tag>` (`:py<major><minor>-<tag>` for the base) to all six images, `devcontainer-ansible-podman` included, and never move the rolling tags.

`devcontainer-ansible` is built on the base image produced in the same run: `build-all` overrides the `BASE_IMAGE` build-arg with `devcontainer-base@<digest>` from the `build-base` job, so a published ansible image always contains the base published beside it. The digest pinned in `devcontainers/ansible/Dockerfile` is what local and PR builds resolve, and Renovate keeps it fresh.

> **Security hygiene** – `build-containers.yml` runs on a daily schedule (`0 3 * * *`) and builds every image **without cache** (`no-cache`), as do manual dispatches, so GHCR images pick up OS security fixes even when the repository is quiet. The cache has to be bypassed: BuildKit replays the cached upgrade layer (`apt-get full-upgrade`, `apk upgrade`) for as long as the Dockerfile and its pinned base digest are unchanged, so a cached rebuild republishes the same packages indefinitely while the run stays green. Push builds stay cached and are therefore at most ~24h behind.
>
> Images are scanned before they are tagged, on every event. Each build is pushed untagged, by digest; Grype then scans every platform it published (amd64 and arm64), and only an image with no fixable high/critical finding on any platform is attested, signed and tagged. A rejected image leaves its tags on the last one that passed and the run goes red: job `Base image has no fixable findings` for the base, the `build-all` or `build-single` job for a stack. After a scheduled or manual (uncached) build, rebuilding will not clear the finding: bump the pinned component (or widen the Dockerfile's upgrade step) that ships the vulnerable package, or record a justified exception in `.grype.yaml`. A push build reuses cache up to a day old, so the next scheduled build may clear its finding on its own.

## Reproducible builds

Two builds of the same commit, made while the package mirrors serve the same packages, produce the same per-platform image manifest digest. That was verified for `linux/amd64`, all six images, with two uncached builds of each; `linux/arm64` runs the same steps and is expected to match, but has not been verified yet. Everything a build downloads is pinned (base images by digest, GitHub release assets by checksum, the Python stack by hash in `requirements-ansible.txt`) except the OS packages that `apt-get full-upgrade` and `apk upgrade` install, which are whatever the Debian and Alpine mirrors serve at the time.

How a build gets there:

- `build-containers.yml` passes the commit time (`git log -1 --format=%ct`) as the `SOURCE_DATE_EPOCH` build-arg, and so do the image builds in `ci.yml` and `test-containers.yml`, so CI tests the images as they are published. BuildKit writes it as the `created` time of the image config and of every history entry. `rewrite-timestamp=true` on the exporter clamps every file mtime later than it in the layers the build adds; the `FROM` image's layers are kept as they are. The `org.opencontainers.image.created` label carries the same time instead of metadata-action's clock.
- No Dockerfile declares `ARG SOURCE_DATE_EPOCH`. Undeclared, the value never reaches a `RUN` and changes no cache key; declared, it would invalidate every layer below it on every commit, in CI and in the publish cache alike. The `BUILD_DATE` and `VCS_REF` arguments the Dockerfiles used to declare are gone for the same reason, and metadata-action already labels every image with `created` and `revision`.
- Some files carry the build's time or randomness in their contents, which no mtime clamp can fix, so the Dockerfiles remove it:
  - every apt step deletes `/var/log/dpkg.log`, `/var/log/alternatives.log`, `/var/log/apt/history.log`, `/var/log/apt/term.log` and `/var/cache/ldconfig/aux-cache`, and every apk step `/var/log/apk.log`;
  - the step that creates `vscode` empties the last-change day `useradd`/`adduser` writes into `/etc/shadow`;
  - `devcontainer-ansible-podman` deletes the random `/etc/machine-id` and `/var/lib/dbus/machine-id` that the systemd and dbus packages generate;
  - `devcontainer-latex` deletes the fontconfig caches, which record each font directory's mtime;
  - the ansible builders compile with `CFLAGS=-g0`: on arm64 `onigurumacffi` is built from its sdist, and debug info would embed uv's randomly named build directory in the `.so`.
- Python bytecode written at build time is checked-hash (`python3 -m compileall --invalidation-mode checked-hash`), not uv's timestamp `.pyc`. A timestamp `.pyc` records its source's mtime, so the clamp makes it stale; `vscode` cannot write to `/usr/local/lib`, so every import of a stale module recompiles it in memory. A structure test fails on any stale timestamp `.pyc` under `/usr/local/lib/python3.*`: `tests/container-structure/base.yaml` for the base, and `ansible.yaml` for the ansible image and for `devcontainer-ansible-podman`, which `test-containers.yml` also checks with `ansible-podman.yaml`. pip, the one package the python image brings, is left uncompiled, as uv always left it. The compile runs in parallel, and parallel writes through overlayfs leave some directories with their old mtime and others with the build's, differently each time; the same step therefore touches every directory under the Python tree, and the clamp sets them all to the epoch.

What is not reproducible:

- The digest a tag points to, the image *index*. It lists the provenance and SBOM attestations, and both describe the run itself: the SLSA provenance records `startedOn`, `finishedOn` and an invocation ID, the SPDX SBOM a `creationInfo.created` time and a random `documentNamespace`. Compare the per-platform manifests inside the index instead.
- A rebuild after the mirrors have moved, typically on another day. `apt-get full-upgrade` and `apk upgrade` install the newest packages on purpose, so that every scheduled build ships the security fixes published since the last one, and the digest moves with them.
- `devcontainer-ansible` across different bases. Published builds use the base built in the same run, so two ansible builds match only when their `BASE_IMAGE` resolves to the same base manifest.

To check it, build one image twice without cache and compare the manifest digests. The OCI exporter needs a `docker-container` builder (`docker buildx create --use`) or Docker's containerd image store:

```bash
EPOCH="$(git log -1 --format=%ct)"
for run in 1 2; do
  docker buildx build --no-cache --platform linux/amd64 \
    --build-arg SOURCE_DATE_EPOCH="${EPOCH}" \
    --provenance=false --sbom=false \
    --output "type=oci,dest=golang-${run}.tar,rewrite-timestamp=true,compression=zstd,compression-level=12,force-compression=true,oci-mediatypes=true" \
    -f devcontainers/golang/Dockerfile .
  tar -xOf "golang-${run}.tar" index.json | jq -r '.manifests[0].digest'
done
```

Without attestations the OCI layout points straight at the image manifest, and its digest is the one the attested build lists in its index. For two published runs, resolve each run's index digest (the `digest` output of its build step) to the platform manifest with `IMAGE=ghcr.io/malpanez/devcontainer-<stack> DIGEST=<index digest> PLATFORM=linux/amd64 REQUIRED=true bash scripts/resolve-platform-manifest.sh`.

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
4. Scans every platform of the digest again (amd64, and arm64 when the image has it) with the gate's policy (`.grype.yaml`, fixable high/critical findings block), since advisories may have been published after the image was gated.
5. Only when every image passed, adds the version tag to each exact digest (a `docker buildx imagetools create` dry run must reproduce the digest before any tag is written, and every tag is read back). An existing version tag is never moved to another digest.

The release notes list the digest of every image and the commit it was built from, and the release carries a [Syft](https://github.com/anchore/syft) SPDX SBOM of each released digest with its keyless cosign bundle (`.sigstore`); the same SBOMs are kept as the `devcontainer-sbom` workflow artifact. Verify a released image with:

```bash
cosign verify ghcr.io/malpanez/devcontainer-ansible:<tag> \
  --certificate-identity "https://github.com/malpanez/ansible-devcontainer-vscode/.github/workflows/build-containers.yml@refs/heads/main" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

Replace `<tag>` with the release you want to verify (for example `v1.2.3`). Releases whose notes have no *Container images* table (v1.3.29 and earlier) were rebuilt and signed by `release.yml` itself: verify those with `--certificate-identity "https://github.com/malpanez/ansible-devcontainer-vscode/.github/workflows/release.yml@refs/tags/<tag>"`. Published images are consumed from the public owner-level namespace such as `ghcr.io/malpanez/devcontainer-ansible:latest`.

If a published image ever becomes unavailable or `latest` resolves to a broken manifest, dispatch `Build and Publish Containers` on `main` with `stack: all`: it rebuilds every image uncached, builds ansible on the base from the same run, and republishes only what passes the scan gate. A single-stack dispatch also works, but ansible then uses the base digest pinned in its Dockerfile, and `ansible-podman` is only rebuilt by `all`. Then verify `docker pull` and `docker buildx imagetools inspect` against the public tags.

To reproduce the Ansible stack outside of the Dev Container run:

```bash
ansible-playbook playbooks/setup-workspace.yml -K
```

## Nightly scan of the newest release

A version tag is never rebuilt or moved, and `release.yml` scans an image only on the day it is released, so an advisory published later would otherwise never be reported against it; on 2026-10-28 v1.3.29 still carried fixable criticals that no scan had reported. `.github/workflows/scan-release-images.yml` rescans the newest GitHub release every night (`23 12 * * *`, from `main` like every schedule); dispatch it with `tag` to scan another release.

- Each of the six images is resolved to the index digest of its version tag and scanned by that digest. The base's tag is `py<major><minor>-<tag>`, with the stream derived by `scripts/derive-python-tag.sh` from the base Dockerfile of the tagged commit, as `release.yml` did.
- amd64 is scanned through the index, arm64 by its own manifest (`scripts/resolve-platform-manifest.sh`). arm64 is required wherever `build-containers.yml` builds it, which is every image except `devcontainer-latex`, so a release index without it fails.
- The policy is the gate's: `.grype.yaml` of the commit the workflow runs on, fixable high/critical findings. `scripts/count-fixable-findings.sh` gives the verdict, and a platform that could not be judged fails the image.
- Each image's job summary names the tag, the digest and the count. Findings are uploaded to code scanning as `grype-release-<image>` and `grype-release-<image>-arm64`, apart from the `grype-<image>` categories of `build-containers.yml`, which cover `main`. Only the newest release is uploaded; a dispatch for an older one reports in its job summary only.

A red run means everyone who pins that release gets a fixable high or critical vulnerability. Cut a patch release: when `main`'s images pass the build-containers scan gate, releasing `main` ships the fix; otherwise bump the pinned component (or widen the Dockerfile's upgrade step) that ships the vulnerable package first. Or record a justified exception in `.grype.yaml`.
