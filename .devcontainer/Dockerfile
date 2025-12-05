# syntax=docker/dockerfile:1.7

# renovate: datasource=github-releases depName=hashicorp/terraform
ARG TERRAFORM_VERSION=1.9.6
# renovate: datasource=github-releases depName=gruntwork-io/terragrunt
ARG TERRAGRUNT_VERSION=0.67.1
# renovate: datasource=github-releases depName=terraform-linters/tflint
ARG TFLINT_VERSION=0.54.0

FROM --platform=$BUILDPLATFORM hashicorp/terraform:${TERRAFORM_VERSION} AS terraform-cli

FROM --platform=$BUILDPLATFORM debian:bookworm-slim AS terraform-tools
ARG TARGETPLATFORM
ARG TERRAGRUNT_VERSION
ARG TFLINT_VERSION

# Install dependencies for downloading and verifying tools
# hadolint ignore=DL3008
RUN --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache/apt \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        unzip \
    && rm -rf /var/lib/apt/lists/*

# Download Terragrunt and TFLint with platform-specific architecture
# Note: SHA256 verification would require updating checksums on every version bump
# For security, we rely on HTTPS and GitHub's integrity guarantees
# TODO: Consider implementing checksum verification with dynamic lookup
RUN set -eux; \
    case "${TARGETPLATFORM}" in \
      "linux/amd64") ARCH="amd64" ;; \
      "linux/arm64") ARCH="arm64" ;; \
      *) echo "Unsupported TARGETPLATFORM: ${TARGETPLATFORM}" >&2; exit 1 ;; \
    esac; \
    echo "Downloading Terragrunt ${TERRAGRUNT_VERSION} for ${ARCH}..."; \
    curl -fsSL "https://github.com/gruntwork-io/terragrunt/releases/download/v${TERRAGRUNT_VERSION}/terragrunt_linux_${ARCH}" \
      -o /usr/local/bin/terragrunt; \
    chmod +x /usr/local/bin/terragrunt; \
    /usr/local/bin/terragrunt --version; \
    echo "Downloading TFLint ${TFLINT_VERSION} for ${ARCH}..."; \
    curl -fsSL "https://github.com/terraform-linters/tflint/releases/download/v${TFLINT_VERSION}/tflint_linux_${ARCH}.zip" \
      -o /tmp/tflint.zip; \
    unzip /tmp/tflint.zip -d /usr/local/bin; \
    rm /tmp/tflint.zip; \
    chmod +x /usr/local/bin/tflint; \
    /usr/local/bin/tflint --version

ARG BASE_IMAGE=ghcr.io/malpanez/devcontainer-base:py312
FROM ${BASE_IMAGE}

LABEL maintainer="alpanez.alcalde@gmail.com"
LABEL description="Terraform + Ansible Development Environment 2025"
LABEL org.opencontainers.image.source="https://github.com/malpanez/ansible-devcontainer-vscode"
LABEL org.opencontainers.image.description="TOP 0.1% DevContainer for Terraform, Ansible, and Infrastructure as Code"
LABEL org.opencontainers.image.licenses="Apache-2.0"

ENV DEBIAN_FRONTEND=noninteractive
ENV UV_INSTALL_DIR=/usr/local/bin
ENV UV_LINK_MODE=copy

USER root

# Copy tools from build stages
COPY --from=terraform-cli /bin/terraform /usr/local/bin/terraform
COPY --from=terraform-tools /usr/local/bin/terragrunt /usr/local/bin/terragrunt
COPY --from=terraform-tools /usr/local/bin/tflint /usr/local/bin/tflint

# Install common CLI tools that were previously in postCreateCommand
# This improves devcontainer startup performance significantly
# hadolint ignore=DL3008
RUN --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        gh \
        make \
        yamllint \
        jq \
        git-lfs \
        vim \
        ripgrep && \
    rm -rf /var/lib/apt/lists/*

# Install Python security and quality tools
# Pin checkov to specific version for reproducibility
# renovate: datasource=pypi depName=checkov
ARG CHECKOV_VERSION="3.2.331"
RUN uv pip install --system "checkov==${CHECKOV_VERSION}"

# Verify all tools are installed correctly
RUN terraform version && \
    terragrunt --version && \
    tflint --version && \
    checkov --version && \
    gh --version && \
    make --version && \
    jq --version

USER vscode

# Configure git defaults
RUN git config --global init.defaultBranch main && \
    git config --global pull.rebase false && \
    git config --global core.editor "vim" && \
    git lfs install

WORKDIR /workspace

CMD ["/bin/bash"]
