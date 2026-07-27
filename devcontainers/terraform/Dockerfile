# syntax=docker/dockerfile:1.25
ARG DEBIAN_VERSION=bookworm-slim
# renovate: datasource=github-releases depName=hashicorp/terraform
ARG TERRAFORM_VERSION=1.15.8
# renovate: datasource=github-releases depName=gruntwork-io/terragrunt
ARG TERRAGRUNT_VERSION=1.1.1
# renovate: datasource=github-releases depName=terraform-linters/tflint
ARG TFLINT_VERSION=0.64.0
# renovate: datasource=github-releases depName=getsops/sops
ARG SOPS_VERSION=3.13.3
# renovate: datasource=github-releases depName=FiloSottile/age
ARG AGE_VERSION=1.3.1
# renovate: datasource=github-releases depName=astral-sh/uv
ARG UV_VERSION=0.11.32

FROM --platform=$BUILDPLATFORM debian:${DEBIAN_VERSION}@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818 AS fetch
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
    && rm -rf /var/lib/apt/lists/*

# Every artifact is verified against its upstream checksum manifest;
# age publishes no manifest, so its hash is pinned per release.
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# hadolint ignore=DL3003
RUN set -eux; \
    case "$TARGETARCH" in \
      amd64) ARCH="amd64"; AGE_SHA256="bdc69c09cbdd6cf8b1f333d372a1f58247b3a33146406333e30c0f26e8f51377" ;; \
      arm64) ARCH="arm64"; AGE_SHA256="c6878a324421b69e3e20b00ba17c04bc5c6dab0030cfe55bf8f68fa8d9e9093a" ;; \
      *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    mkdir -p /tmp/bin /tmp/dl; \
    cd /tmp/dl; \
    curl -fsSL "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_${ARCH}.zip" \
      -o "terraform_${TERRAFORM_VERSION}_linux_${ARCH}.zip"; \
    curl -fsSL "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_SHA256SUMS" \
      -o terraform_SHA256SUMS; \
    grep " terraform_${TERRAFORM_VERSION}_linux_${ARCH}.zip" terraform_SHA256SUMS | sha256sum -c -; \
    unzip -d /tmp/bin "terraform_${TERRAFORM_VERSION}_linux_${ARCH}.zip"; \
    curl -fsSL "https://github.com/gruntwork-io/terragrunt/releases/download/v${TERRAGRUNT_VERSION}/terragrunt_linux_${ARCH}" \
      -o "terragrunt_linux_${ARCH}"; \
    curl -fsSL "https://github.com/gruntwork-io/terragrunt/releases/download/v${TERRAGRUNT_VERSION}/SHA256SUMS" \
      -o terragrunt_SHA256SUMS; \
    grep -E " terragrunt_linux_${ARCH}\$" terragrunt_SHA256SUMS | sha256sum -c -; \
    install -m 0755 "terragrunt_linux_${ARCH}" /tmp/bin/terragrunt; \
    curl -fsSL "https://github.com/terraform-linters/tflint/releases/download/v${TFLINT_VERSION}/tflint_linux_${ARCH}.zip" \
      -o "tflint_linux_${ARCH}.zip"; \
    curl -fsSL "https://github.com/terraform-linters/tflint/releases/download/v${TFLINT_VERSION}/checksums.txt" \
      -o tflint_checksums.txt; \
    grep " tflint_linux_${ARCH}.zip" tflint_checksums.txt | sha256sum -c -; \
    unzip -d /tmp/bin "tflint_linux_${ARCH}.zip"; \
    curl -fsSL "https://github.com/getsops/sops/releases/download/v${SOPS_VERSION}/sops-v${SOPS_VERSION}.linux.${ARCH}" \
      -o "sops-v${SOPS_VERSION}.linux.${ARCH}"; \
    curl -fsSL "https://github.com/getsops/sops/releases/download/v${SOPS_VERSION}/sops-v${SOPS_VERSION}.checksums.txt" \
      -o sops_checksums.txt; \
    grep -E " sops-v${SOPS_VERSION}\.linux\.${ARCH}\$" sops_checksums.txt | sha256sum -c -; \
    install -m 0755 "sops-v${SOPS_VERSION}.linux.${ARCH}" /tmp/bin/sops; \
    /bin/bash /tmp/install_age.sh "${AGE_VERSION}" "${ARCH}" "${AGE_SHA256}"; \
    cd /; \
    rm -rf /tmp/dl

FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

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

# Install system dependencies + GitHub CLI (gh) to avoid DevContainer features rebuild
# https://github.com/cli/cli/blob/trunk/docs/install_linux.md
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
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
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gh \
    && apt-get autoremove -y --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager (versioned binary, no pipe-to-shell)
ARG UV_VERSION
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

# Install AWS CLI v2 to avoid DevContainer features rebuild
# https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
ARG TARGETARCH
# renovate: datasource=github-tags depName=aws/aws-cli
ARG AWS_CLI_VERSION=2.36.8
# AWS publishes no sha256 manifest (only GPG sigs), so hashes are pinned
# per release; recompute them when bumping AWS_CLI_VERSION.
RUN set -eux; \
    case "$TARGETARCH" in \
      amd64) AWS_ARCH="x86_64"; AWS_SHA256="829a2bbad5b4821a8d006a133c34fa5ce2f362ae003ac39aa0865a6d1e1711f2" ;; \
      arm64) AWS_ARCH="aarch64"; AWS_SHA256="fedb42aaa0f4e9623c626008139a0e4741cfa3f7ea3067c5a479390126e09f58" ;; \
      *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-${AWS_ARCH}-${AWS_CLI_VERSION}.zip" -o /tmp/awscliv2.zip \
    && echo "${AWS_SHA256}  /tmp/awscliv2.zip" | sha256sum -c - \
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
    && install -d -o ${USERNAME} -g ${USERNAME} ${WORKSPACE} \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.local/bin \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.local/share/uv \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.cache/uv \
    && install -d -o ${USERNAME} -g ${USERNAME} /home/${USERNAME}/.cache/pre-commit \
    && install -d -o ${USERNAME} -g ${USERNAME} /usr/local/share/devcontainer-skel/terraform

COPY --chmod=0444 templates/pre-commit/terraform/.pre-commit-config.yaml /usr/local/share/devcontainer-skel/terraform/.pre-commit-config.yaml
COPY --chmod=0555 devcontainers/scripts/ensure-precommit.sh /usr/local/bin/ensure-precommit

ENV PATH="/home/${USERNAME}/.local/bin:${PATH}"

USER ${USERNAME}

RUN git config --global init.defaultBranch main

WORKDIR ${WORKSPACE}

CMD ["/bin/bash"]
