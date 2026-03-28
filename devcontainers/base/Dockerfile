# syntax=docker/dockerfile:1.7
ARG PYTHON_IMAGE=python:3.12.12-slim-bookworm@sha256:5621ae4640bf259c8a9f09c513cd6c80fc14b3fab3d9cf99f3227637cdf78525
# hadolint ignore=DL3006
FROM ${PYTHON_IMAGE}

# BuildKit platform arguments
ARG TARGETPLATFORM
ARG TARGETARCH
ARG TARGETOS

LABEL maintainer="alpanez.alcalde@gmail.com" \
      description="Shared Python base layer for infrastructure devcontainers" \
      org.opencontainers.image.source="https://github.com/malpanez/ansible-devcontainer-vscode" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="malpanez"

ENV DEBIAN_FRONTEND=noninteractive
ENV UV_INSTALL_DIR=/usr/local/bin
ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1
# renovate: datasource=github-releases depName=astral-sh/uv
ARG UV_VERSION=0.9.13

# Common system packages used across Python-based stacks.
# hadolint ignore=DL3008,DL3015
RUN --mount=type=cache,target=/var/lib/apt/lists,id=apt-lists-${TARGETARCH},sharing=locked \
    --mount=type=cache,target=/var/cache/apt,id=apt-cache-${TARGETARCH},sharing=locked \
    apt-get update \
    && apt-get full-upgrade -y \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        gnupg \
        jq \
        openssh-client \
        sshpass \
        sudo \
        vim-tiny \
        yamllint \
    && apt-get autoremove -y --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI (gh) to avoid DevContainer features rebuild
# https://github.com/cli/cli/blob/trunk/docs/install_linux.md
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# hadolint ignore=DL3008
RUN --mount=type=cache,target=/var/lib/apt/lists,id=apt-lists-${TARGETARCH},sharing=locked \
    --mount=type=cache,target=/var/cache/apt,id=apt-cache-${TARGETARCH},sharing=locked \
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gh \
    && apt-get autoremove -y --purge \
    && apt-get clean

# Configure non-root workspace user.
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME} \
    && printf '%s ALL=(root) NOPASSWD: /usr/local/bin/uv, /usr/local/bin/uvx\n' "${USERNAME}" > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME} \
    && install -d -m 755 /home/${USERNAME}/.cache/pre-commit \
    && install -d -m 700 /home/${USERNAME}/.ansible/tmp \
    && install -d -m 755 /home/${USERNAME}/.ansible/galaxy_cache \
    && chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}/.cache \
    && chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}/.ansible \
    && case "$(dpkg --print-architecture)" in \
         amd64) UV_ARCH="x86_64-unknown-linux-musl" ;; \
         arm64) UV_ARCH="aarch64-unknown-linux-musl" ;; \
         *) printf 'Unsupported arch: %s\n' "$(dpkg --print-architecture)" >&2; exit 1 ;; \
       esac \
    && curl -fsSL "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${UV_ARCH}.tar.gz" \
         -o /tmp/uv.tar.gz \
    && tar -xzf /tmp/uv.tar.gz -C /tmp \
    && install -m 755 "/tmp/uv-${UV_ARCH}/uv" /usr/local/bin/uv \
    && install -m 755 "/tmp/uv-${UV_ARCH}/uvx" /usr/local/bin/uvx \
    && rm -rf /tmp/uv.tar.gz "/tmp/uv-${UV_ARCH}" \
    && uv pip install --system pre-commit \
    && mkdir -p /workspace \
    && chown ${USERNAME}:${USERNAME} /workspace
ENV PATH="/usr/local/bin:${PATH}"
WORKDIR /workspace
