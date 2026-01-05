# syntax=docker/dockerfile:1.7
ARG DEBIAN_VERSION=bookworm-slim
ARG TERRAFORM_VERSION=1.14.0
ARG TERRAGRUNT_VERSION=0.93.11
ARG TFLINT_VERSION=0.60.0
ARG SOPS_VERSION=3.11.0
ARG AGE_VERSION=1.2.1
ARG BASE_IMAGE=debian:${DEBIAN_VERSION}@sha256:72ceb30c8c49e50d4bf87aa6eb5390c3bcf091c13f41e6382e79953ea44c11c8

FROM --platform=$BUILDPLATFORM debian:${DEBIAN_VERSION}@sha256:72ceb30c8c49e50d4bf87aa6eb5390c3bcf091c13f41e6382e79953ea44c11c8 AS fetch
ARG TARGETARCH
ARG TERRAFORM_VERSION TFLINT_VERSION TERRAGRUNT_VERSION SOPS_VERSION AGE_VERSION

COPY devcontainers/terraform/install_age.sh /tmp/install_age.sh

# hadolint ignore=DL3008
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      unzip \
      xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    case "$TARGETARCH" in \
      amd64|arm64) ARCH="$TARGETARCH" ;; \
      *) echo "Arquitectura no soportada: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    mkdir -p /tmp/bin; \
    curl -fsSL "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_${ARCH}.zip" \
      -o /tmp/terraform.zip; \
    unzip -d /tmp/bin /tmp/terraform.zip; \
    curl -fsSL "https://github.com/gruntwork-io/terragrunt/releases/download/v${TERRAGRUNT_VERSION}/terragrunt_linux_${ARCH}" \
      -o /tmp/bin/terragrunt; \
    chmod +x /tmp/bin/terragrunt; \
    curl -fsSL "https://github.com/terraform-linters/tflint/releases/download/v${TFLINT_VERSION}/tflint_linux_${ARCH}.zip" \
      -o /tmp/tflint.zip; \
    unzip -d /tmp/bin /tmp/tflint.zip; \
    curl -fsSL "https://github.com/getsops/sops/releases/download/v${SOPS_VERSION}/sops-v${SOPS_VERSION}.linux.${ARCH}" \
      -o /tmp/bin/sops; \
    chmod +x /tmp/bin/sops; \
    /bin/bash /tmp/install_age.sh "${AGE_VERSION}" "${ARCH}";

FROM ${BASE_IMAGE}

ARG BUILD_DATE="unknown"
ARG VCS_REF="unknown"
ARG IMAGE_VENDOR="malpanez"

LABEL org.opencontainers.image.source="https://github.com/malpanez/ansible-devcontainer-vscode" \
      org.opencontainers.image.description="Terraform devcontainer with Terragrunt, TFLint, SOPS, age, and uv-powered pre-commit" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="${IMAGE_VENDOR}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}"

ENV DEBIAN_FRONTEND=noninteractive \
    UV_INSTALL_DIR=/usr/local/bin \
    UV_LINK_MODE=copy \
    TF_PLUGIN_CACHE_DIR=/workspaces/.terraform.d/plugin-cache \
    WORKSPACE=/workspace \
    DEVCONTAINER_STACK=terraform \
    DEVCONTAINER_TEMPLATE_ROOT=/usr/local/share/devcontainer-skel

# Install system dependencies
# Note: git, github-cli (gh), and aws-cli installed to avoid DevContainer features rebuild
# hadolint ignore=DL3008,DL3015
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
      bash \
      ca-certificates \
      curl \
      git \
      sudo \
      unzip \
    && rm -rf /var/lib/apt/lists/*

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install GitHub CLI (gh) to avoid DevContainer features rebuild
# https://github.com/cli/cli/blob/trunk/docs/install_linux.md
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -fsSL https://astral.sh/uv/install.sh | sh

# Install AWS CLI v2 to avoid DevContainer features rebuild
# https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
ARG TARGETARCH
RUN set -eux; \
    case "$TARGETARCH" in \
      amd64) AWS_ARCH="x86_64" ;; \
      arm64) AWS_ARCH="aarch64" ;; \
      *) echo "Arquitectura no soportada: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-${AWS_ARCH}.zip" -o /tmp/awscliv2.zip \
    && unzip -q /tmp/awscliv2.zip -d /tmp \
    && /tmp/aws/install --bin-dir /usr/local/bin --install-dir /usr/local/aws-cli \
    && rm -rf /tmp/awscliv2.zip /tmp/aws

COPY --from=fetch --link --chmod=0755 /tmp/bin/terraform /usr/local/bin/terraform
COPY --from=fetch --link --chmod=0755 /tmp/bin/terragrunt /usr/local/bin/terragrunt
COPY --from=fetch --link --chmod=0755 /tmp/bin/tflint /usr/local/bin/tflint
COPY --from=fetch --link --chmod=0755 /tmp/bin/sops /usr/local/bin/sops
COPY --from=fetch --link --chmod=0755 /tmp/bin/age /usr/local/bin/age
COPY --from=fetch --link --chmod=0755 /tmp/bin/age-keygen /usr/local/bin/age-keygen

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=${USER_UID}

RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME} \
    && cat > /etc/sudoers.d/${USERNAME} <<EOF
${USERNAME} ALL=(root) NOPASSWD: /usr/bin/apt-get, /usr/local/bin/uv, /usr/local/bin/uvx
EOF
    && chmod 0440 /etc/sudoers.d/${USERNAME} \
    && install -d -o ${USERNAME} -g ${USERNAME} ${WORKSPACE} \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.local/bin \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.local/share/uv \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.cache/uv \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.cache/pre-commit \
    && install -d -o ${USERNAME} -g ${USERNAME} /usr/local/share/devcontainer-skel/terraform

COPY --chown=${USERNAME}:${USERNAME} templates/pre-commit/terraform/.pre-commit-config.yaml /usr/local/share/devcontainer-skel/terraform/.pre-commit-config.yaml
COPY --chmod=0755 devcontainers/scripts/ensure-precommit.sh /usr/local/bin/ensure-precommit

ENV PATH="/home/${USERNAME}/.local/bin:${PATH}"

USER ${USERNAME}

RUN git config --global init.defaultBranch main

WORKDIR ${WORKSPACE}

CMD ["/bin/bash"]
