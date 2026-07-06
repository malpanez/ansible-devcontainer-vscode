# syntax=docker/dockerfile:1.7
# Runtime and builder share the hardened devcontainer-base layer (apt
# tools, gh, checksum-verified uv, pre-commit, vscode user), so pulling
# several stacks reuses it. release.yml preflight overrides BASE_IMAGE
# with a locally built base; bump the digest when base:main is rebuilt.
ARG BASE_IMAGE=ghcr.io/malpanez/devcontainer-base:main@sha256:89f4e222350fe7a21adfe160a74d7711d35134057f66d1a683a15a38620e9ee4

# Stage 1: resolve the Python stack. Build tools live only in this stage:
# arm64 needs gcc + libonig-dev because onigurumacffi (pulled in by
# ansible-navigator) publishes no aarch64 wheel.
# hadolint ignore=DL3006
FROM ${BASE_IMAGE} AS python-builder

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

# Extras on top of devcontainer-base: rsync/unzip for Ansible workflows
# (also being added to base itself) and libonig5, the runtime library
# behind the source-built onigurumacffi on arm64.
# hadolint ignore=DL3008
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
      libonig5 \
      rsync \
      unzip \
    && apt-get autoremove -y --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the whole lib tree (not a version-pinned site-packages path): the
# builder shares this stage's base, so its Python minor always matches —
# hardcoding it only breaks while the pinned base lags a version bump.
COPY --link --from=python-builder /usr/local/lib /usr/local/lib
COPY --link --from=python-builder /usr/local/bin /usr/local/bin

ARG USERNAME=vscode

# devcontainer-base already creates the user; add the stack directories
RUN install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.local/share/uv \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.cache/uv \
    && install -d -o ${USERNAME} -g ${USERNAME} /usr/local/share/devcontainer-skel/ansible \
    && chown ${USERNAME}:${USERNAME} \
         /home/${USERNAME}/.local \
         /home/${USERNAME}/.local/share

COPY --link --chmod=0444 templates/pre-commit/ansible/.pre-commit-config.yaml /usr/local/share/devcontainer-skel/ansible/.pre-commit-config.yaml
COPY --link --chmod=0555 devcontainers/scripts/ensure-precommit.sh /usr/local/bin/ensure-precommit

ENV PATH="/home/${USERNAME}/.local/bin:${PATH}"

USER ${USERNAME}

RUN git config --global init.defaultBranch main

WORKDIR ${WORKSPACE}

CMD ["/bin/bash"]
