# syntax=docker/dockerfile:1.27
# The builder and the runtime stage both start from the hardened
# devcontainer-base layer (apt tools, gh, checksum-verified uv,
# pre-commit, vscode user), so the two stages and the base pulled beside
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
ARG BASE_IMAGE=ghcr.io/malpanez/devcontainer-base:main@sha256:503dffbb543e0c77fde1d9d6b09d97e8b53aa02972f67c152a70b9e221576fd5

# Stage 1: resolve the Python stack. Build tools live only in this stage:
# arm64 needs gcc + libonig-dev because onigurumacffi (pulled in by
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

COPY pyproject.toml /tmp/pyproject.toml

WORKDIR /tmp
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv pip install --system .

# Stage 2: runtime image without any build toolchain
# hadolint ignore=DL3006
FROM ${BASE_IMAGE}

# devcontainer-base ends as vscode; everything below until the USER switch
# at the end of this stage needs root (apt, install -d, COPY into /usr/local).
# Numeric uid so the id resolves without /etc/passwd (DL3066).
USER 0

ARG BUILD_DATE="unknown"
ARG VCS_REF="unknown"
ARG IMAGE_VENDOR="malpanez"

LABEL org.opencontainers.image.source="https://github.com/malpanez/ansible-devcontainer-vscode" \
      org.opencontainers.image.description="Ansible devcontainer with uv-managed Python toolchain and hardened defaults" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="${IMAGE_VENDOR}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}"

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
    && rm -rf /var/lib/apt/lists/*

# Copy the whole lib tree (not a version-pinned site-packages path): the
# builder shares this stage's base, so its Python minor always matches —
# hardcoding it only breaks while the pinned base lags a version bump.
COPY --link --from=python-builder /usr/local/lib /usr/local/lib
COPY --link --from=python-builder /usr/local/bin /usr/local/bin

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
