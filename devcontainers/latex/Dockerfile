# syntax=docker/dockerfile:1.7
ARG TECTONIC_VERSION=0.15.0
FROM debian:bookworm-slim

ARG TECTONIC_VERSION
ARG TARGETARCH
ARG BUILD_DATE="unknown"
ARG VCS_REF="unknown"
ARG IMAGE_VENDOR="malpanez"

LABEL org.opencontainers.image.source="https://github.com/malpanez/ansible-devcontainer-vscode" \
      org.opencontainers.image.description="Lightweight LaTeX devcontainer powered by Tectonic and uv pre-commit tooling" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="${IMAGE_VENDOR}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}"

ENV DEBIAN_FRONTEND=noninteractive \
    UV_INSTALL_DIR=/usr/local/bin \
    UV_LINK_MODE=copy \
    WORKSPACE=/workspace \
    DEVCONTAINER_STACK=latex \
    DEVCONTAINER_TEMPLATE_ROOT=/usr/local/share/devcontainer-skel \
    TECTONIC_CACHE_DIR=/home/vscode/.cache/Tectonic

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      git \
      perl \
      sudo \
      unzip \
      xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    case "${TARGETARCH}" in \
      amd64) TECTONIC_ARCH="x86_64-unknown-linux-gnu" ;; \
      arm64) TECTONIC_ARCH="aarch64-unknown-linux-gnu" ;; \
      *) echo "Unsupported architecture ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%40${TECTONIC_VERSION}/tectonic-${TECTONIC_VERSION}-${TECTONIC_ARCH}.tar.gz" \
      -o /tmp/tectonic.tar.gz; \
    tar -xzf /tmp/tectonic.tar.gz -C /tmp; \
    install -m 0755 "/tmp/tectonic-${TECTONIC_VERSION}-${TECTONIC_ARCH}/tectonic" /usr/local/bin/tectonic; \
    rm -rf /tmp/tectonic*

RUN curl -fsSL https://astral.sh/uv/install.sh | sh

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=${USER_UID}

RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME} \
    && echo "${USERNAME} ALL=(root) NOPASSWD: /usr/bin/apt-get, /usr/local/bin/uv, /usr/local/bin/uvx" > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME}

RUN install -d -o ${USERNAME} -g ${USERNAME} ${WORKSPACE} \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.local/bin \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.cache/uv \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.cache/Tectonic \
    && install -d -o ${USERNAME} -g ${USERNAME} /usr/local/share/devcontainer-skel/latex

COPY --chown=${USERNAME}:${USERNAME} templates/pre-commit/latex/.pre-commit-config.yaml /usr/local/share/devcontainer-skel/latex/.pre-commit-config.yaml
COPY --chmod=0755 devcontainers/scripts/ensure-precommit.sh /usr/local/bin/ensure-precommit

ENV PATH="/home/${USERNAME}/.local/bin:${PATH}"

USER ${USERNAME}

RUN git config --global init.defaultBranch main

WORKDIR ${WORKSPACE}

CMD ["/bin/bash"]
