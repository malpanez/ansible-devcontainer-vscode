# syntax=docker/dockerfile:1.7
ARG BASE_IMAGE=golang:1.25.4-alpine
FROM ${BASE_IMAGE}

ARG BUILD_DATE="unknown"
ARG VCS_REF="unknown"
ARG IMAGE_VENDOR="malpanez"

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
RUN curl -fsSL https://astral.sh/uv/install.sh | sh

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=${USER_UID}

RUN addgroup -g ${USER_GID} ${USERNAME} \
    && adduser -D -u ${USER_UID} -G ${USERNAME} -s /bin/bash ${USERNAME} \
    && echo "${USERNAME} ALL=(root) NOPASSWD: /sbin/apk, /usr/local/bin/uv, /usr/local/bin/uvx" > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME}

RUN install -d -o ${USERNAME} -g ${USERNAME} ${WORKSPACE} \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.local/bin \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.cache/uv \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/go \
    && install -d -o ${USERNAME} -g ${USERNAME} /usr/local/share/devcontainer-skel/golang

COPY --chown=${USERNAME}:${USERNAME} templates/pre-commit/golang/.pre-commit-config.yaml /usr/local/share/devcontainer-skel/golang/.pre-commit-config.yaml
COPY --chmod=0755 devcontainers/scripts/ensure-precommit.sh /usr/local/bin/ensure-precommit

ENV PATH="/home/${USERNAME}/.local/bin:/home/${USERNAME}/go/bin:${PATH}"

USER ${USERNAME}

RUN git config --global init.defaultBranch main

WORKDIR ${WORKSPACE}

CMD ["/bin/bash"]
