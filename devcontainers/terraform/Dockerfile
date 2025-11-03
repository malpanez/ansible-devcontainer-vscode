# syntax=docker/dockerfile:1.7
ARG TERRAFORM_VERSION=1.13.4
ARG TERRAGRUNT_VERSION=0.54.17
ARG TFLINT_VERSION=0.51.1
ARG BASE_IMAGE=ghcr.io/malpanez/devcontainer-base:py312
ARG CHECKOV_CONSTRAINT="checkov>=3.0.0,<4.0.0"

FROM --platform=$BUILDPLATFORM hashicorp/terraform:${TERRAFORM_VERSION} AS terraform-cli

# BuildKit platform arguments
ARG TARGETARCH
ARG TARGETOS

FROM --platform=$BUILDPLATFORM debian:bookworm-slim AS terraform-tools

# BuildKit platform arguments
ARG TARGETPLATFORM
ARG TARGETARCH
ARG TARGETOS
ARG TERRAGRUNT_VERSION
ARG TFLINT_VERSION

RUN --mount=type=cache,target=/var/lib/apt/lists,id=apt-lists-${TARGETARCH},sharing=locked \
    --mount=type=cache,target=/var/cache/apt,id=apt-cache-${TARGETARCH},sharing=locked \
    apt-get update \
    && apt-get full-upgrade -y \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        unzip \
    && apt-get autoremove -y --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    case "${TARGETPLATFORM}" in \
      "linux/amd64") ARCH="amd64" ;; \
      "linux/arm64") ARCH="arm64" ;; \
      *) echo "Unsupported TARGETPLATFORM: ${TARGETPLATFORM}" >&2; exit 1 ;; \
    esac; \
    TERRAGRUNT_FILE="terragrunt_linux_${ARCH}"; \
    TFLINT_ARCH="${ARCH}"; \
    mkdir -p /tmp/downloads; \
    cd /tmp/downloads; \
    curl -fsSL "https://github.com/gruntwork-io/terragrunt/releases/download/v${TERRAGRUNT_VERSION}/${TERRAGRUNT_FILE}" \
      -o "${TERRAGRUNT_FILE}"; \
    curl -fsSL "https://github.com/gruntwork-io/terragrunt/releases/download/v${TERRAGRUNT_VERSION}/SHA256SUMS" \
      -o terragrunt_SHA256SUMS; \
    grep "  ${TERRAGRUNT_FILE}$" terragrunt_SHA256SUMS > terragrunt_SHA256SUMS.selected; \
    sha256sum --check terragrunt_SHA256SUMS.selected; \
    install -m 0755 "${TERRAGRUNT_FILE}" /usr/local/bin/terragrunt; \
    TFLINT_BASE_URL="https://github.com/terraform-linters/tflint/releases/download/v${TFLINT_VERSION}"; \
    if ! curl -fsSL "${TFLINT_BASE_URL}/tflint_checksums.txt" -o tflint_checksums.txt; then \
      curl -fsSL "${TFLINT_BASE_URL}/checksums.txt" -o tflint_checksums.txt; \
    fi; \
    curl -fsSL "${TFLINT_BASE_URL}/tflint_linux_${TFLINT_ARCH}.zip" \
      -o tflint_linux_${TFLINT_ARCH}.zip; \
    grep "  tflint_linux_${TFLINT_ARCH}.zip$" tflint_checksums.txt > tflint_linux_${TFLINT_ARCH}.zip.sha256; \
    sha256sum --check tflint_linux_${TFLINT_ARCH}.zip.sha256; \
    unzip tflint_linux_${TFLINT_ARCH}.zip -d /tmp/tflint-bin; \
    install -m 0755 /tmp/tflint-bin/tflint /usr/local/bin/tflint; \
    rm -rf /tmp/downloads /tmp/tflint-bin

FROM ${BASE_IMAGE}

# BuildKit platform arguments
ARG TARGETPLATFORM
ARG TARGETARCH
ARG TARGETOS
ARG CHECKOV_CONSTRAINT

LABEL maintainer="alpanez.alcalde@gmail.com"
LABEL description="Terraform + Ansible Development Environment 2025"

ENV DEBIAN_FRONTEND=noninteractive
ENV UV_INSTALL_DIR=/usr/local/bin
ENV UV_LINK_MODE=copy
ENV CHECKOV_CONSTRAINT=${CHECKOV_CONSTRAINT}

USER root

COPY --from=terraform-cli /bin/terraform /usr/local/bin/terraform
COPY --from=terraform-tools /usr/local/bin/terragrunt /usr/local/bin/terragrunt
COPY --from=terraform-tools /usr/local/bin/tflint /usr/local/bin/tflint

USER vscode

RUN git config --global init.defaultBranch main

WORKDIR /workspace

CMD ["/bin/bash"]
