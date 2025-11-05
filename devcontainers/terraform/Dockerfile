# syntax=docker/dockerfile:1.7
ARG TERRAGRUNT_VERSION=0.54.17
ARG TFLINT_VERSION=0.51.1
ARG BASE_IMAGE=ghcr.io/malpanez/devcontainer-base:py312
ARG CHECKOV_CONSTRAINT="checkov>=3.0.0,<4.0.0"

FROM --platform=$BUILDPLATFORM hashicorp/terraform:${TERRAFORM_VERSION} AS terraform-cli

# BuildKit platform arguments
ARG TARGETARCH
ARG TARGETOS

FROM --platform=$BUILDPLATFORM debian:bookworm-slim AS terraform-tools

ARG TERRAGRUNT_VERSION
ARG TFLINT_VERSION
ARG TARGETARCH

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      unzip \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    case "${TARGETARCH}" in \
      amd64) ARCH="amd64" ;; \
      arm64) ARCH="arm64" ;; \
      *) echo "Unsupported architecture: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    mkdir -p /opt/bin; \
    curl -fsSL "https://github.com/gruntwork-io/terragrunt/releases/download/v${TERRAGRUNT_VERSION}/terragrunt_linux_${ARCH}" \
      -o /tmp/terragrunt; \
    curl -fsSL "https://github.com/gruntwork-io/terragrunt/releases/download/v${TERRAGRUNT_VERSION}/SHA256SUMS" \
      -o /tmp/terragrunt.sha256; \
    grep "terragrunt_linux_${ARCH}$" /tmp/terragrunt.sha256 > /tmp/terragrunt.sha256.selected; \
    sha256sum --check /tmp/terragrunt.sha256.selected; \
    install -m 0755 /tmp/terragrunt /opt/bin/terragrunt; \
    rm -f /tmp/terragrunt /tmp/terragrunt.sha256 /tmp/terragrunt.sha256.selected; \
    curl -fsSL "https://github.com/terraform-linters/tflint/releases/download/v${TFLINT_VERSION}/tflint_linux_${ARCH}.zip" \
      -o /tmp/tflint.zip; \
    curl -fsSL "https://github.com/terraform-linters/tflint/releases/download/v${TFLINT_VERSION}/tflint_checksums.txt" \
      -o /tmp/tflint.sha256; \
    grep "tflint_linux_${ARCH}.zip$" /tmp/tflint.sha256 > /tmp/tflint.sha256.selected; \
    sha256sum --check /tmp/tflint.sha256.selected; \
    unzip -q /tmp/tflint.zip -d /tmp; \
    install -m 0755 /tmp/tflint /opt/bin/tflint; \
    rm -rf /tmp/tflint /tmp/tflint.zip /tmp/tflint.sha256 /tmp/tflint.sha256.selected

FROM cgr.dev/chainguard/terraform:latest

ARG BUILD_DATE="unknown"
ARG VCS_REF="unknown"
ARG IMAGE_VENDOR="malpanez"

LABEL org.opencontainers.image.source="https://github.com/malpanez/ansible-devcontainer-vscode" \
      org.opencontainers.image.description="Terraform devcontainer with Terragrunt, TFLint, and uv-powered pre-commit" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="${IMAGE_VENDOR}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}"

ENV UV_INSTALL_DIR=/usr/local/bin \
    UV_LINK_MODE=copy \
    TF_PLUGIN_CACHE_DIR=/workspaces/.terraform.d/plugin-cache \
    WORKSPACE=/workspace \
    DEVCONTAINER_STACK=terraform \
    DEVCONTAINER_TEMPLATE_ROOT=/usr/local/share/devcontainer-skel

RUN apk add --no-cache \
      bash \
      curl \
      git \
      sudo \
      unzip

RUN curl -fsSL https://astral.sh/uv/install.sh | sh

COPY --from=terraform-tools /opt/bin/terragrunt /usr/local/bin/terragrunt
COPY --from=terraform-tools /opt/bin/tflint /usr/local/bin/tflint

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=${USER_UID}

RUN addgroup -g ${USER_GID} ${USERNAME} \
    && adduser -D -u ${USER_UID} -G ${USERNAME} -s /bin/bash ${USERNAME} \
    && echo "${USERNAME} ALL=(root) NOPASSWD: /sbin/apk, /usr/local/bin/uv, /usr/local/bin/uvx, /usr/local/bin/terragrunt, /usr/local/bin/terraform" > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME}

RUN install -d -o ${USERNAME} -g ${USERNAME} ${WORKSPACE} \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.local/bin \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.cache/uv \
    && install -d -o ${USERNAME} -g ${USERNAME} /usr/local/share/devcontainer-skel/terraform

COPY --chown=${USERNAME}:${USERNAME} templates/pre-commit/terraform/.pre-commit-config.yaml /usr/local/share/devcontainer-skel/terraform/.pre-commit-config.yaml
COPY --chmod=0755 devcontainers/scripts/ensure-precommit.sh /usr/local/bin/ensure-precommit

ENV PATH="/home/${USERNAME}/.local/bin:${PATH}"

USER ${USERNAME}

RUN git config --global init.defaultBranch main

WORKDIR ${WORKSPACE}

CMD ["/bin/bash"]
