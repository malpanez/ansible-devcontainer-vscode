# syntax=docker/dockerfile:1.7
# renovate: datasource=github-releases depName=tectonic-typesetting/tectonic
ARG TECTONIC_VERSION=0.15.0
FROM debian:bookworm-slim@sha256:60eac759739651111db372c07be67863818726f754804b8707c90979bda511df

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

# hadolint ignore=DL3008
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
      bash \
      ca-certificates \
      curl \
      git \
      # runtime dependency of the tectonic gnu binary
      libgraphite2-3 \
      perl \
      sudo \
      unzip \
    && apt-get autoremove -y --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# Tectonic publishes no checksum manifest; hashes pinned per release.
# Note: 0.15.0 ships no aarch64 gnu artifact, only musl.
RUN set -eux; \
    ARCH="${TARGETARCH:-$(dpkg --print-architecture)}"; \
    case "${ARCH}" in \
      amd64|x86_64) TECTONIC_ARCH="x86_64-unknown-linux-gnu"; \
        TECTONIC_SHA256="875fbbc9ab48560d7776088c608e0beee49197b57ab4a2f6c5385b2c661c842f" ;; \
      arm64|aarch64) TECTONIC_ARCH="aarch64-unknown-linux-musl"; \
        TECTONIC_SHA256="1f59f9fb8eb65e8ba18658fc9016767e7d3e12488ded8b8fffa34254e51ce42c" ;; \
      *) echo "Unsupported architecture ${ARCH}" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%40${TECTONIC_VERSION}/tectonic-${TECTONIC_VERSION}-${TECTONIC_ARCH}.tar.gz" \
      -o /tmp/tectonic.tar.gz; \
    echo "${TECTONIC_SHA256}  /tmp/tectonic.tar.gz" | sha256sum -c -; \
    TMP_DIR="$(mktemp -d /tmp/tectonic.XXXXXX)"; \
    tar -xzf /tmp/tectonic.tar.gz -C "${TMP_DIR}"; \
    SRC="$(find "${TMP_DIR}" -type f -name tectonic -perm -u+x | head -n1 || true)"; \
    if [ -z "${SRC}" ] || [ ! -f "${SRC}" ]; then \
      echo "Unable to locate tectonic binary" >&2; exit 1; \
    fi; \
    install -m 0755 "${SRC}" /usr/local/bin/tectonic; \
    rm -rf /tmp/tectonic.tar.gz "${TMP_DIR}"

# renovate: datasource=github-releases depName=astral-sh/uv
ARG UV_VERSION=0.9.13
RUN set -eux; \
    case "$(dpkg --print-architecture)" in \
      amd64) UV_ARCH="x86_64-unknown-linux-musl" ;; \
      arm64) UV_ARCH="aarch64-unknown-linux-musl" ;; \
      *) printf 'Unsupported arch: %s\n' "$(dpkg --print-architecture)" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${UV_ARCH}.tar.gz" \
      -o "/tmp/uv-${UV_ARCH}.tar.gz"; \
    curl -fsSL "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${UV_ARCH}.tar.gz.sha256" \
      -o "/tmp/uv-${UV_ARCH}.tar.gz.sha256"; \
    echo "$(cut -d' ' -f1 "/tmp/uv-${UV_ARCH}.tar.gz.sha256")  /tmp/uv-${UV_ARCH}.tar.gz" | sha256sum -c -; \
    tar -xzf "/tmp/uv-${UV_ARCH}.tar.gz" -C /tmp; \
    install -m 755 "/tmp/uv-${UV_ARCH}/uv" /usr/local/bin/uv; \
    install -m 755 "/tmp/uv-${UV_ARCH}/uvx" /usr/local/bin/uvx; \
    rm -rf "/tmp/uv-${UV_ARCH}.tar.gz" "/tmp/uv-${UV_ARCH}.tar.gz.sha256" "/tmp/uv-${UV_ARCH}"

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=${USER_UID}

RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME} \
    && install -d -o ${USERNAME} -g ${USERNAME} ${WORKSPACE} \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.local/bin \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.cache/uv \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.cache/Tectonic \
    && install -d -o ${USERNAME} -g ${USERNAME} /usr/local/share/devcontainer-skel/latex

COPY --link --chmod=0444 templates/pre-commit/latex/.pre-commit-config.yaml /usr/local/share/devcontainer-skel/latex/.pre-commit-config.yaml
COPY --link --chmod=0555 devcontainers/scripts/ensure-precommit.sh /usr/local/bin/ensure-precommit

ENV PATH="/home/${USERNAME}/.local/bin:${PATH}"

USER ${USERNAME}

RUN git config --global init.defaultBranch main

WORKDIR ${WORKSPACE}

CMD ["/bin/bash"]
