# syntax=docker/dockerfile:1.28
# The builder and the runtime stage both start from the hardened
# devcontainer-base layer (apt tools, gh, checksum-verified uv, pre-commit
# and yamllint, vscode user), so the two stages and the base pulled beside
# them share it. The digest below is NOT what published images
# are built on: build-containers.yml overrides BASE_IMAGE with the base
# built in the same run, and release.yml preflight overrides it with a
# locally built base. The pin is what local and PR builds resolve, and
# Renovate refreshes it, so it never needs bumping by hand.
#
# BASE_IMAGE deliberately carries BOTH the :main tag and the @sha256
# digest. The digest is what actually resolves (Docker ignores the tag
# when a digest is present), so the pin stays immutable for Scorecard's
# Pinned-Dependencies; the tag is what tells Renovate which stream to
# track — drop it and Renovate falls back to :latest, stops refreshing
# this digest, and the pin rots until GHCR prunes it and the build dies
# (that is exactly what broke main on 2026-07-24). Linters that want
# "tag or digest, not both" are false positives here: hadolint DL3006 is
# suppressed below; SonarCloud docker:S8431 has no in-repo suppression
# (Dockerfiles allow no trailing NOSONAR comment, and automatic analysis
# ignores sonar.issue.ignore.*), so it must be deactivated in the
# project's quality profile instead.
ARG BASE_IMAGE=ghcr.io/malpanez/devcontainer-base:main@sha256:24633a57eec8fd24067bd4772621f1b42975c1b465002461bfd87ea679a0f0a7

# Stage 1: install the locked Python stack. Build tools live only in this
# stage: arm64 needs gcc + libonig-dev because onigurumacffi (pulled in by
# ansible-navigator) publishes no aarch64 wheel.
# hadolint ignore=DL3006
FROM ${BASE_IMAGE} AS python-builder

# devcontainer-base ends as vscode; apt and a --system install need root.
# Numeric uid so the id resolves without /etc/passwd (DL3066). DL3002 is
# suppressed because this is a builder stage: it is never the final image,
# only /usr/local is copied out of it.
# hadolint ignore=DL3002
USER 0

# hadolint ignore=DL3008
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
      gcc \
      libc6-dev \
      libffi-dev \
      libonig-dev \
    && rm -rf /var/lib/apt/lists/*

# The hashed uv.lock export, not pyproject.toml: resolving pyproject at
# build time picked whatever PyPI served that day, so the cached CI layer
# and the uncached nightly publish shipped different versions, neither of
# them the lock's (certifi, 2026-10-26).
COPY requirements-ansible.txt /tmp/requirements-ansible.txt

# CFLAGS=-g0 because arm64 compiles onigurumacffi here from its sdist, and
# the -g in Python's own CFLAGS wrote uv's randomly named build directory
# into the .so's debug info, so the file differed in every build.
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    CFLAGS=-g0 UV_COMPILE_BYTECODE=0 uv pip install --system --require-hashes -r /tmp/requirements-ansible.txt

# ansible-core plus the collections pinned with their sha256 in
# collections.txt, instead of the ansible package's bundle of 92.
COPY devcontainers/ansible/collections.txt devcontainers/ansible/install-collections.sh /tmp/ansible-collections/
RUN SITE="$(python3 -c 'import sysconfig; print(sysconfig.get_path("purelib"))')" \
    && bash /tmp/ansible-collections/install-collections.sh "${SITE}" /tmp/ansible-collections/collections.txt

# Checked-hash bytecode instead of uv's timestamp .pyc, which the
# exporter's rewrite-timestamp would leave stale, pip left uncompiled, and
# every directory touched afterwards: see devcontainers/base for all three.
# ansible_collections gets none: ansible-core imports collection code
# through its own loader, which compiles the source in memory and never
# reads __pycache__, so bytecode there is dead weight (160 MiB of it in
# v1.4.0, for the 92 bundled collections).
RUN SITE="$(python3 -c 'import sysconfig; print(sysconfig.get_path("purelib"))')" \
    && python3 -m compileall -q -f -j 0 --invalidation-mode checked-hash \
         -x '/site-packages/(pip|ansible_collections)/' "${SITE}" \
    && find "$(dirname "${SITE}")" -type d -exec touch {} +

# Stage 2: runtime image without any build toolchain
# hadolint ignore=DL3006
FROM ${BASE_IMAGE}

# devcontainer-base ends as vscode; everything below until the USER switch
# at the end of this stage needs root (apt, install -d, COPY into /usr/local).
# Numeric uid so the id resolves without /etc/passwd (DL3066).
USER 0

ARG IMAGE_VENDOR="malpanez"

LABEL org.opencontainers.image.source="https://github.com/malpanez/ansible-devcontainer-vscode" \
      org.opencontainers.image.description="Ansible devcontainer with uv-managed Python toolchain and hardened defaults" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="${IMAGE_VENDOR}"

ENV DEBIAN_FRONTEND=noninteractive \
    WORKSPACE=/workspace \
    DEVCONTAINER_STACK=ansible \
    DEVCONTAINER_TEMPLATE_ROOT=/usr/local/share/devcontainer-skel

# Published builds get their base from the same run (build-containers.yml),
# but PR and local builds resolve the BASE_IMAGE pin, which can trail the
# published base by days; this upgrade closes that gap without waiting for
# Renovate.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update \
    && apt-get full-upgrade -y \
    && apt-get autoremove -y --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    # Wall-clock timestamps in the contents: see devcontainers/base.
    && rm -f /var/log/dpkg.log /var/log/alternatives.log \
         /var/log/apt/history.log /var/log/apt/term.log \
         /var/cache/ldconfig/aux-cache

# Bring /usr/local/lib and /usr/local/bin to the builder's state, writing
# only what differs from this stage's base. The builder started from the
# same base, so the Python stdlib, uv and the site-packages base already
# ships are byte-identical and stay in the base's layers: base installs
# pre-commit, yamllint and their dependencies from
# requirements-devcontainer-tools.txt, the same uv.lock as
# requirements-ansible.txt, so the builder's install leaves them alone.
# Copying both trees whole, as this stage used to, stored all of that a
# second time.
# --delete removes what the builder removed. That happens only when this
# base and the lock disagree, such as a pinned BASE_IMAGE that trails a lock
# bump: uv replaces the package and the base's old dist-info would
# otherwise stay beside the new one, both reported by scanners (pre-commit
# 4.6.2 next to 4.7.0, 2026-10-28). --checksum and no -t: a file is
# rewritten only when its content differs. Syncing an mtime alone would
# copy the whole file up into this layer, and the builder rewrote every
# .pyc of the base.
RUN --mount=type=bind,from=python-builder,source=/usr/local,target=/mnt/python-builder \
    rsync -rlpgoD --checksum --delete /mnt/python-builder/lib/ /usr/local/lib/ \
    && rsync -rlpgoD --checksum --delete /mnt/python-builder/bin/ /usr/local/bin/

# DL3064 fires on the *name* containing USERNAME, not on any secret: the
# value is the fixed, public account the Dev Containers specification
# expects every image to provide, and renaming it would break the spec.
# hadolint ignore=DL3064
ARG USERNAME=vscode

# devcontainer-base already creates the user; add the stack directories
RUN install -d -o "${USERNAME}" -g "${USERNAME}" "/home/${USERNAME}/.local/share/uv" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" "/home/${USERNAME}/.cache/uv" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" /usr/local/share/devcontainer-skel/ansible \
    && chown "${USERNAME}:${USERNAME}" \
         "/home/${USERNAME}/.local" \
         "/home/${USERNAME}/.local/share"

COPY --link --chmod=0444 templates/pre-commit/ansible/.pre-commit-config.yaml /usr/local/share/devcontainer-skel/ansible/.pre-commit-config.yaml
COPY --link --chmod=0555 devcontainers/scripts/ensure-precommit.sh /usr/local/bin/ensure-precommit

ENV PATH="/home/${USERNAME}/.local/bin:${PATH}"

USER ${USERNAME}

RUN git config --global init.defaultBranch main

WORKDIR ${WORKSPACE}

CMD ["/bin/bash"]
