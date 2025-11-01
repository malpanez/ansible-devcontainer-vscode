# syntax=docker/dockerfile:1.7
ARG TERRAFORM_VERSION=1.7.5
ARG TERRAGRUNT_VERSION=0.54.17
ARG TFLINT_VERSION=0.51.1

FROM --platform=$BUILDPLATFORM hashicorp/terraform:${TERRAFORM_VERSION} AS terraform-cli

FROM --platform=$BUILDPLATFORM debian:bookworm-slim AS terraform-tools
ARG TARGETPLATFORM
ARG TERRAGRUNT_VERSION
ARG TFLINT_VERSION

RUN --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache/apt \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        unzip \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    case "${TARGETPLATFORM}" in \
      "linux/amd64") ARCH="amd64" ;; \
      "linux/arm64") ARCH="arm64" ;; \
      *) echo "Unsupported TARGETPLATFORM: ${TARGETPLATFORM}" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/gruntwork-io/terragrunt/releases/download/v${TERRAGRUNT_VERSION}/terragrunt_linux_${ARCH}" \
      -o /usr/local/bin/terragrunt; \
    chmod +x /usr/local/bin/terragrunt; \
    curl -fsSL "https://github.com/terraform-linters/tflint/releases/download/v${TFLINT_VERSION}/tflint_linux_${ARCH}.zip" \
      -o /tmp/tflint.zip; \
    unzip /tmp/tflint.zip -d /usr/local/bin; \
    rm /tmp/tflint.zip; \
    chmod +x /usr/local/bin/tflint

ARG BASE_IMAGE=ghcr.io/malpanez/devcontainer-base:py312
FROM ${BASE_IMAGE}

LABEL maintainer="alpanez.alcalde@gmail.com"
LABEL description="Terraform + Ansible Development Environment 2025"

ENV DEBIAN_FRONTEND=noninteractive
ENV UV_INSTALL_DIR=/usr/local/bin
ENV UV_LINK_MODE=copy

USER root

COPY --from=terraform-cli /bin/terraform /usr/local/bin/terraform
COPY --from=terraform-tools /usr/local/bin/terragrunt /usr/local/bin/terragrunt
COPY --from=terraform-tools /usr/local/bin/tflint /usr/local/bin/tflint

ARG CHECKOV_CONSTRAINT="checkov>=3.0.0,<4.0.0"
RUN uv pip install --system "${CHECKOV_CONSTRAINT}"

USER vscode

RUN git config --global init.defaultBranch main

WORKDIR /workspace

CMD ["/bin/bash"]
