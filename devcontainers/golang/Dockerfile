# syntax=docker/dockerfile:1.7
ARG BASE_IMAGE=golang:1.25.6-alpine3.22@sha256:fa3380ab0d73b706e6b07d2a306a4dc68f20bfc1437a6a6c47c8f88fe4af6f75
# hadolint ignore=DL3006
FROM ${BASE_IMAGE}

ARG BUILD_DATE="unknown"
ARG VCS_REF="unknown"
ARG IMAGE_VENDOR="malpanez"
# renovate: datasource=github-releases depName=astral-sh/uv
ARG UV_VERSION=0.9.13

LABEL org.opencontainers.image.source="https://github.com/malpanez/ansible-devcontainer-vscode" \
      org.opencontainers.image.description="Golang devcontainer with uv-driven pre-commit workflow" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="${IMAGE_VENDOR}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}"

ENV UV_INSTALL_DIR=/usr/local/bin \
    UV_LINK_MODE=copy \
    WORKSPACE=/workspace \
    DEVCONTAINER_STACK=golang \
    DEVCONTAINER_TEMPLATE_ROOT=/usr/local/share/devcontainer-skel \
    GOPATH=/home/vscode/go

RUN apk add --no-cache \
      bash=~5 \
      curl=~8 \
      git=~2 \
      sudo=~1

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN set -eux; \
    case "$(uname -m)" in \
      x86_64) UV_ARCH="x86_64-unknown-linux-musl" ;; \
      aarch64) UV_ARCH="aarch64-unknown-linux-musl" ;; \
      *) printf 'Unsupported arch: %s\n' "$(uname -m)" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${UV_ARCH}.tar.gz" \
      -o /tmp/uv.tar.gz; \
    tar -xzf /tmp/uv.tar.gz -C /tmp; \
    install -m 755 "/tmp/uv-${UV_ARCH}/uv" /usr/local/bin/uv; \
    install -m 755 "/tmp/uv-${UV_ARCH}/uvx" /usr/local/bin/uvx; \
    rm -rf /tmp/uv.tar.gz "/tmp/uv-${UV_ARCH}"

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=${USER_UID}

RUN addgroup -g ${USER_GID} ${USERNAME} \
    && adduser -D -u ${USER_UID} -G ${USERNAME} -s /bin/bash ${USERNAME} \
    && printf '%s ALL=(root) NOPASSWD: /sbin/apk, /usr/local/bin/uv, /usr/local/bin/uvx\n' \
        "${USERNAME}" > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME} \
    && install -d -o ${USERNAME} -g ${USERNAME} ${WORKSPACE} \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.local/bin \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.cache/uv \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/go \
    && install -d -o ${USERNAME} -g ${USERNAME} /usr/local/share/devcontainer-skel/golang

COPY --link --chmod=0444 templates/pre-commit/golang/.pre-commit-config.yaml /usr/local/share/devcontainer-skel/golang/.pre-commit-config.yaml
COPY --link --chmod=0555 devcontainers/scripts/ensure-precommit.sh /usr/local/bin/ensure-precommit

ENV PATH="/home/${USERNAME}/.local/bin:/home/${USERNAME}/go/bin:${PATH}"

USER ${USERNAME}

RUN git config --global init.defaultBranch main

WORKDIR ${WORKSPACE}

CMD ["/bin/bash"]
