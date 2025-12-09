# syntax=docker/dockerfile:1.7
ARG BASE_IMAGE=python:3.12-slim-bookworm@sha256:5621ae4640bf259c8a9f09c513cd6c80fc14b3fab3d9cf99f3227637cdf78525
FROM ${BASE_IMAGE}

ARG TARGETPLATFORM
ARG TARGETARCH
ARG TARGETOS
ARG BUILD_DATE="unknown"
ARG VCS_REF="unknown"
ARG IMAGE_VENDOR="malpanez"
ARG UV_VERSION="0.5.11"

LABEL org.opencontainers.image.source="https://github.com/malpanez/ansible-devcontainer-vscode" \
      org.opencontainers.image.description="Ansible devcontainer with uv-managed Python toolchain and hardened defaults" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="${IMAGE_VENDOR}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}"

ENV DEBIAN_FRONTEND=noninteractive \
    UV_INSTALL_DIR=/usr/local/bin \
    UV_LINK_MODE=copy \
    WORKSPACE=/workspace \
    DEVCONTAINER_STACK=ansible \
    DEVCONTAINER_TEMPLATE_ROOT=/usr/local/share/devcontainer-skel

# Install system dependencies
# Note: git and github-cli (gh) installed via apt to avoid DevContainer features rebuild
# Note: NOT installing tini since we use --init in runArgs
# hadolint ignore=DL3008,DL3015
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
      git \
      openssh-client \
      rsync \
      curl \
      ca-certificates \
      unzip \
      sudo \
      build-essential \
      libffi-dev \
      libonig-dev \
      libssl-dev \
      python3-dev \
      pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI (gh) to avoid DevContainer features rebuild
# https://github.com/cli/cli/blob/trunk/docs/install_linux.md
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*

# Install uv with pinned version for reproducibility
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN curl -fsSL https://astral.sh/uv/${UV_VERSION}/install.sh | sh

COPY pyproject.toml /tmp/pyproject.toml

WORKDIR /tmp
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv pip install --system . \
    && rm -f /tmp/pyproject.toml

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=${USER_UID}

# Hardened sudoers: only allow uv, uvx, ansible-galaxy (no apt-get)
# This forces package installations to happen during build, not at runtime
RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME} \
    && echo "${USERNAME} ALL=(root) NOPASSWD: /usr/bin/uv, /usr/bin/uvx, /usr/local/bin/ansible-galaxy" > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME}

RUN install -d -o ${USERNAME} -g ${USERNAME} ${WORKSPACE} \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.local/share/uv \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.cache/uv \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.cache/pre-commit \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.cache/go-build \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.ansible \
    && install -d -o ${USERNAME} -g ${USERNAME} /usr/local/share/devcontainer-skel/ansible

COPY --chown=${USERNAME}:${USERNAME} templates/pre-commit/ansible/.pre-commit-config.yaml /usr/local/share/devcontainer-skel/ansible/.pre-commit-config.yaml
COPY --chmod=0755 devcontainers/scripts/ensure-precommit.sh /usr/local/bin/ensure-precommit

ENV PATH="/home/${USERNAME}/.local/bin:${PATH}"

USER ${USERNAME}

RUN git config --global init.defaultBranch main

WORKDIR ${WORKSPACE}

CMD ["/bin/bash"]
