# syntax=docker/dockerfile:1.26
# renovate: datasource=github-releases depName=tectonic-typesetting/tectonic
ARG TECTONIC_VERSION=0.17.0
FROM debian:bookworm-slim@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171

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
      fontconfig \
      git \
      perl \
      sudo \
      unzip \
    && apt-get autoremove -y --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# Tectonic publishes no checksum manifest; hashes pinned per release.
# musl artifacts on both arches: they are static, so they keep working
# regardless of the base image's glibc (the gnu builds broke on 0.16.9).
RUN set -eux; \
    ARCH="${TARGETARCH:-$(dpkg --print-architecture)}"; \
    case "${ARCH}" in \
      amd64|x86_64) TECTONIC_ARCH="x86_64-unknown-linux-musl"; \
        TECTONIC_SHA256="8533d07f9ccbd7a65824b9e0459041bca34af1eb33daba48f59215593753a3b7" ;; \
      arm64|aarch64) TECTONIC_ARCH="aarch64-unknown-linux-musl"; \
        TECTONIC_SHA256="b10954a95404f3ab2328d2fa59a5ebab8e657f893fab096f98be8db7c0c979b8" ;; \
      *) echo "Unsupported architecture ${ARCH}" >&2; exit 1 ;; \
    esac; \
    curl --proto '=https' --tlsv1.2 -fsSL "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%40${TECTONIC_VERSION}/tectonic-${TECTONIC_VERSION}-${TECTONIC_ARCH}.tar.gz" \
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
ARG UV_VERSION=0.12.7
RUN set -eux; \
    case "$(dpkg --print-architecture)" in \
      amd64) UV_ARCH="x86_64-unknown-linux-musl" ;; \
      arm64) UV_ARCH="aarch64-unknown-linux-musl" ;; \
      *) printf 'Unsupported arch: %s\n' "$(dpkg --print-architecture)" >&2; exit 1 ;; \
    esac; \
    curl --proto '=https' --tlsv1.2 -fsSL "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${UV_ARCH}.tar.gz" \
      -o "/tmp/uv-${UV_ARCH}.tar.gz"; \
    curl --proto '=https' --tlsv1.2 -fsSL "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${UV_ARCH}.tar.gz.sha256" \
      -o "/tmp/uv-${UV_ARCH}.tar.gz.sha256"; \
    echo "$(cut -d' ' -f1 "/tmp/uv-${UV_ARCH}.tar.gz.sha256")  /tmp/uv-${UV_ARCH}.tar.gz" | sha256sum -c -; \
    tar -xzf "/tmp/uv-${UV_ARCH}.tar.gz" -C /tmp; \
    install -m 755 "/tmp/uv-${UV_ARCH}/uv" /usr/local/bin/uv; \
    install -m 755 "/tmp/uv-${UV_ARCH}/uvx" /usr/local/bin/uvx; \
    rm -rf "/tmp/uv-${UV_ARCH}.tar.gz" "/tmp/uv-${UV_ARCH}.tar.gz.sha256" "/tmp/uv-${UV_ARCH}"

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=${USER_UID}

RUN groupadd --gid "${USER_GID}" "${USERNAME}" \
    && useradd --uid "${USER_UID}" --gid "${USER_GID}" -m "${USERNAME}" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" "${WORKSPACE}" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" "/home/${USERNAME}/.local/bin" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" "/home/${USERNAME}/.cache/uv" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" "/home/${USERNAME}/.cache/Tectonic" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" /usr/local/share/devcontainer-skel/latex

COPY --link --chmod=0444 templates/pre-commit/latex/.pre-commit-config.yaml /usr/local/share/devcontainer-skel/latex/.pre-commit-config.yaml
COPY --link --chmod=0555 devcontainers/scripts/ensure-precommit.sh /usr/local/bin/ensure-precommit

ENV PATH="/home/${USERNAME}/.local/bin:${PATH}"

USER ${USERNAME}

RUN git config --global init.defaultBranch main

WORKDIR ${WORKSPACE}

CMD ["/bin/bash"]
