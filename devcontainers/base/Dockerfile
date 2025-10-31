# syntax=docker/dockerfile:1.7
ARG PYTHON_IMAGE=python:3.12-slim-bookworm
FROM ${PYTHON_IMAGE}

# BuildKit platform arguments
ARG TARGETPLATFORM
ARG TARGETARCH
ARG TARGETOS

LABEL maintainer="alpanez.alcalde@gmail.com"
LABEL description="Shared Python base layer for infrastructure devcontainers"

ENV DEBIAN_FRONTEND=noninteractive
ENV UV_INSTALL_DIR=/usr/local/bin
ENV UV_LINK_MODE=copy
ARG UV_VERSION=0.4.21

# Common system packages used across Python-based stacks.
RUN --mount=type=cache,target=/var/lib/apt/lists,id=apt-lists-${TARGETARCH},sharing=locked \
    --mount=type=cache,target=/var/cache/apt,id=apt-cache-${TARGETARCH},sharing=locked \
    apt-get update \
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
    && rm -rf /var/lib/apt/lists/*

# Configure non-root workspace user.
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME} \
    && echo "${USERNAME} ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME}

# Ensure cache directories exist and are owned by the non-root user.
RUN install -d -m 755 /home/${USERNAME}/.cache/pre-commit \
    && install -d -m 700 /home/${USERNAME}/.ansible/tmp \
    && install -d -m 755 /home/${USERNAME}/.ansible/galaxy_cache \
    && chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}/.cache \
    && chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}/.ansible

# Install uv once for downstream layers (pinned via PyPI).
RUN python -m pip install --no-cache-dir "uv==${UV_VERSION}"
ENV PATH="/usr/local/bin:${PATH}"

# Prepare shared workspace path (ownership fixed by child layers if needed).
RUN mkdir -p /workspace && chown ${USERNAME}:${USERNAME} /workspace
WORKDIR /workspace
