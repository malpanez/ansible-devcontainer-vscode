# syntax=docker/dockerfile:1.7
ARG BASE_IMAGE=golang:1.25.11-alpine3.23@sha256:60e626bbde32def8694687d03536ea4341b19e5f068e9a630225a1dfbd0505c9
# hadolint ignore=DL3006
FROM ${BASE_IMAGE}

ARG BUILD_DATE="unknown"
ARG VCS_REF="unknown"
ARG IMAGE_VENDOR="malpanez"
# renovate: datasource=github-releases depName=astral-sh/uv
ARG UV_VERSION=0.11.26

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

RUN addgroup -g ${USER_GID} ${USERNAME} \
    && adduser -D -u ${USER_UID} -G ${USERNAME} -s /bin/bash ${USERNAME} \
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
