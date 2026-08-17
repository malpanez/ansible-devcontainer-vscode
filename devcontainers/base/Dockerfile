# syntax=docker/dockerfile:1.25
FROM python:3.14.6-slim-bookworm@sha256:4c92ffcde4dd6f1ff72a24518f49fd4990b27134987dfa31a733badde66df9f8

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
ARG UV_VERSION=0.12.5
# Kept in step with the pre-commit pinned in pyproject/uv.lock so the
# image and the repo run the same hooks. Renovate bumps it.
ARG PRE_COMMIT_VERSION=4.6.2

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
        rsync \
        sshpass \
        sudo \
        unzip \
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
    curl --proto '=https' --tlsv1.2 -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
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

RUN groupadd --gid "${USER_GID}" "${USERNAME}" \
    && useradd --uid "${USER_UID}" --gid "${USER_GID}" -m "${USERNAME}" \
    && install -d -m 755 "/home/${USERNAME}/.cache/pre-commit" \
    && install -d -m 700 "/home/${USERNAME}/.ansible/tmp" \
    && install -d -m 755 "/home/${USERNAME}/.ansible/galaxy_cache" \
    && chown -R "${USERNAME}:${USERNAME}" "/home/${USERNAME}/.cache" \
    && chown -R "${USERNAME}:${USERNAME}" "/home/${USERNAME}/.ansible" \
    && case "$(dpkg --print-architecture)" in \
         amd64) UV_ARCH="x86_64-unknown-linux-musl" ;; \
         arm64) UV_ARCH="aarch64-unknown-linux-musl" ;; \
         *) printf 'Unsupported arch: %s\n' "$(dpkg --print-architecture)" >&2; exit 1 ;; \
       esac \
    && curl --proto '=https' --tlsv1.2 -fsSL "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${UV_ARCH}.tar.gz" \
         -o "/tmp/uv-${UV_ARCH}.tar.gz" \
    && curl --proto '=https' --tlsv1.2 -fsSL "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${UV_ARCH}.tar.gz.sha256" \
         -o "/tmp/uv-${UV_ARCH}.tar.gz.sha256" \
    && echo "$(cut -d' ' -f1 "/tmp/uv-${UV_ARCH}.tar.gz.sha256")  /tmp/uv-${UV_ARCH}.tar.gz" | sha256sum -c - \
    && tar -xzf "/tmp/uv-${UV_ARCH}.tar.gz" -C /tmp \
    && install -m 755 "/tmp/uv-${UV_ARCH}/uv" /usr/local/bin/uv \
    && install -m 755 "/tmp/uv-${UV_ARCH}/uvx" /usr/local/bin/uvx \
    && rm -rf "/tmp/uv-${UV_ARCH}.tar.gz" "/tmp/uv-${UV_ARCH}.tar.gz.sha256" "/tmp/uv-${UV_ARCH}" \
    # --only-binary :all: refuses sdists, so no setup.py from a
    # dependency runs at build time (docker:S8541). Safe here because
    # pre-commit and its deps publish wheels for amd64 and arm64; the
    # other install sites cannot use it (they build the local project,
    # or pull onigurumacffi, which has no aarch64 wheel).
    && uv pip install --system --only-binary :all: "pre-commit==${PRE_COMMIT_VERSION}" \
    && mkdir -p /workspace \
    && chown "${USERNAME}:${USERNAME}" /workspace
ENV PATH="/usr/local/bin:${PATH}"
WORKDIR /workspace
