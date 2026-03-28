# syntax=docker/dockerfile:1.7
ARG BASE_IMAGE=python:3.12-slim-bookworm@sha256:5621ae4640bf259c8a9f09c513cd6c80fc14b3fab3d9cf99f3227637cdf78525
# hadolint ignore=DL3006
FROM ${BASE_IMAGE}

ARG TARGETPLATFORM
ARG TARGETARCH
ARG TARGETOS
ARG BUILD_DATE="unknown"
ARG VCS_REF="unknown"
ARG IMAGE_VENDOR="malpanez"
# renovate: datasource=github-releases depName=astral-sh/uv
ARG UV_VERSION="0.9.13"

LABEL org.opencontainers.image.source="https://github.com/malpanez/ansible-devcontainer-vscode" \
      org.opencontainers.image.description="Ansible devcontainer with uv-managed Python toolchain and hardened defaults" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="${IMAGE_VENDOR}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}"

ENV DEBIAN_FRONTEND=noninteractive \
    UV_INSTALL_DIR=/usr/local/bin \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    WORKSPACE=/workspace \
    DEVCONTAINER_STACK=ansible \
    DEVCONTAINER_TEMPLATE_ROOT=/usr/local/share/devcontainer-skel

# Install system dependencies.
# build-essential / libffi-dev / libssl-dev / python3-dev are intentionally
# omitted: uv resolves manylinux binary wheels for all packages in
# pyproject.toml (ansible, cryptography, cffi, etc.) so no C compiler is
# needed at image build time, saving ~400 MB.
# Note: git and github-cli (gh) pre-installed to avoid DevContainer features rebuild.
# hadolint ignore=DL3008,DL3015
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      git \
      openssh-client \
      rsync \
      sudo \
      unzip \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gh \
    && apt-get autoremove -y --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv with pinned version (direct binary, no pipe-to-shell)
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN set -eux; \
    case "$(dpkg --print-architecture)" in \
      amd64) UV_ARCH="x86_64-unknown-linux-musl" ;; \
      arm64) UV_ARCH="aarch64-unknown-linux-musl" ;; \
      *) printf 'Unsupported arch: %s\n' "$(dpkg --print-architecture)" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${UV_ARCH}.tar.gz" \
      -o /tmp/uv.tar.gz; \
    tar -xzf /tmp/uv.tar.gz -C /tmp; \
    install -m 755 "/tmp/uv-${UV_ARCH}/uv" /usr/local/bin/uv; \
    install -m 755 "/tmp/uv-${UV_ARCH}/uvx" /usr/local/bin/uvx; \
    rm -rf /tmp/uv.tar.gz "/tmp/uv-${UV_ARCH}"

COPY --link pyproject.toml /tmp/pyproject.toml

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
    && printf '%s ALL=(root) NOPASSWD: /usr/local/bin/uv, /usr/local/bin/uvx, /usr/local/bin/ansible-galaxy\n' \
        "${USERNAME}" > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME} \
    && install -d -o ${USERNAME} -g ${USERNAME} ${WORKSPACE} \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.local/share/uv \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.cache/uv \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.cache/pre-commit \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.cache/go-build \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.ansible \
    && install -d -o ${USERNAME} -g ${USERNAME} /usr/local/share/devcontainer-skel/ansible

COPY --link --chmod=0444 templates/pre-commit/ansible/.pre-commit-config.yaml /usr/local/share/devcontainer-skel/ansible/.pre-commit-config.yaml
COPY --link --chmod=0555 devcontainers/scripts/ensure-precommit.sh /usr/local/bin/ensure-precommit

ENV PATH="/home/${USERNAME}/.local/bin:${PATH}"

USER ${USERNAME}

RUN git config --global init.defaultBranch main

WORKDIR ${WORKSPACE}

CMD ["/bin/bash"]
