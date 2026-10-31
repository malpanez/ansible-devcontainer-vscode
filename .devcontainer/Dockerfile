# syntax=docker/dockerfile:1.28
ARG DEBIAN_VERSION=trixie-slim
# renovate: datasource=github-releases depName=hashicorp/terraform
ARG TERRAFORM_VERSION=1.17.0
# renovate: datasource=github-releases depName=gruntwork-io/terragrunt
ARG TERRAGRUNT_VERSION=1.2.1
# renovate: datasource=github-releases depName=terraform-linters/tflint
ARG TFLINT_VERSION=0.65.0
# renovate: datasource=github-releases depName=getsops/sops
ARG SOPS_VERSION=3.13.3
# renovate: datasource=github-releases depName=FiloSottile/age
ARG AGE_VERSION=1.3.2
# renovate: datasource=github-releases depName=astral-sh/uv
ARG UV_VERSION=0.13.6

FROM --platform=$BUILDPLATFORM debian:${DEBIAN_VERSION}@sha256:f6b08b09a05725f9431502d3b5714f5c4576e82c1a84fa1debe0c24a7e0c3ec4 AS fetch
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
      amd64) ARCH="amd64"; AGE_SHA256="cbe24006683f8eb669266162894b9a522a1af52f2665fbc63a4bb032ed26ac10" ;; \
      arm64) ARCH="arm64"; AGE_SHA256="6b8dc4333c53a5a57c9e5834e3a48f92605d7154014cd07269ff3327db5d37f4" ;; \
      *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    mkdir -p /tmp/bin /tmp/dl; \
    cd /tmp/dl; \
    curl --proto '=https' --tlsv1.2 -fsSL --retry 5 --retry-delay 2 --retry-max-time 120 "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_${ARCH}.zip" \
      -o "terraform_${TERRAFORM_VERSION}_linux_${ARCH}.zip"; \
    curl --proto '=https' --tlsv1.2 -fsSL --retry 5 --retry-delay 2 --retry-max-time 120 "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_SHA256SUMS" \
      -o terraform_SHA256SUMS; \
    grep " terraform_${TERRAFORM_VERSION}_linux_${ARCH}.zip" terraform_SHA256SUMS | sha256sum -c -; \
    unzip -d /tmp/bin "terraform_${TERRAFORM_VERSION}_linux_${ARCH}.zip"; \
    curl --proto '=https' --tlsv1.2 -fsSL --retry 5 --retry-delay 2 --retry-max-time 120 "https://github.com/gruntwork-io/terragrunt/releases/download/v${TERRAGRUNT_VERSION}/terragrunt_linux_${ARCH}" \
      -o "terragrunt_linux_${ARCH}"; \
    curl --proto '=https' --tlsv1.2 -fsSL --retry 5 --retry-delay 2 --retry-max-time 120 "https://github.com/gruntwork-io/terragrunt/releases/download/v${TERRAGRUNT_VERSION}/SHA256SUMS" \
      -o terragrunt_SHA256SUMS; \
    grep -E " terragrunt_linux_${ARCH}\$" terragrunt_SHA256SUMS | sha256sum -c -; \
    install -m 0755 "terragrunt_linux_${ARCH}" /tmp/bin/terragrunt; \
    curl --proto '=https' --tlsv1.2 -fsSL --retry 5 --retry-delay 2 --retry-max-time 120 "https://github.com/terraform-linters/tflint/releases/download/v${TFLINT_VERSION}/tflint_linux_${ARCH}.zip" \
      -o "tflint_linux_${ARCH}.zip"; \
    curl --proto '=https' --tlsv1.2 -fsSL --retry 5 --retry-delay 2 --retry-max-time 120 "https://github.com/terraform-linters/tflint/releases/download/v${TFLINT_VERSION}/checksums.txt" \
      -o tflint_checksums.txt; \
    grep " tflint_linux_${ARCH}.zip" tflint_checksums.txt | sha256sum -c -; \
    unzip -d /tmp/bin "tflint_linux_${ARCH}.zip"; \
    curl --proto '=https' --tlsv1.2 -fsSL --retry 5 --retry-delay 2 --retry-max-time 120 "https://github.com/getsops/sops/releases/download/v${SOPS_VERSION}/sops-v${SOPS_VERSION}.linux.${ARCH}" \
      -o "sops-v${SOPS_VERSION}.linux.${ARCH}"; \
    curl --proto '=https' --tlsv1.2 -fsSL --retry 5 --retry-delay 2 --retry-max-time 120 "https://github.com/getsops/sops/releases/download/v${SOPS_VERSION}/sops-v${SOPS_VERSION}.checksums.txt" \
      -o sops_checksums.txt; \
    grep -E " sops-v${SOPS_VERSION}\.linux\.${ARCH}\$" sops_checksums.txt | sha256sum -c -; \
    install -m 0755 "sops-v${SOPS_VERSION}.linux.${ARCH}" /tmp/bin/sops; \
    /bin/bash /tmp/install_age.sh "${AGE_VERSION}" "${ARCH}" "${AGE_SHA256}"; \
    cd /; \
    rm -rf /tmp/dl

# devcontainer-terraform. Not the last stage: the empty one at the end of
# this file, which repeats it, is.
FROM debian:trixie-slim@sha256:f6b08b09a05725f9431502d3b5714f5c4576e82c1a84fa1debe0c24a7e0c3ec4 AS terraform

ARG IMAGE_VENDOR="malpanez"

LABEL org.opencontainers.image.source="https://github.com/malpanez/ansible-devcontainer-vscode" \
      org.opencontainers.image.description="Terraform devcontainer with Terragrunt, TFLint, SOPS, age, and uv-powered pre-commit" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="${IMAGE_VENDOR}"

# LANG: debian-slim sets none, so `locale charmap` printed ANSI_X3.4-1968 and
# tools that ask the locale treated everything as ASCII.
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    UV_INSTALL_DIR=/usr/local/bin \
    UV_LINK_MODE=copy \
    TF_PLUGIN_CACHE_DIR=/workspaces/.terraform.d/plugin-cache \
    WORKSPACE=/workspace \
    DEVCONTAINER_STACK=terraform \
    DEVCONTAINER_TEMPLATE_ROOT=/usr/local/share/devcontainer-skel

# Install system dependencies + GitHub CLI (gh) to avoid DevContainer features rebuild
# https://github.com/cli/cli/blob/trunk/docs/install_linux.md
# openssh-client: without it `git ls-remote git@...` stopped at "error: cannot
# run ssh" and `terraform init` could not fetch a git::ssh:// module.
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# hadolint ignore=DL3008,DL3015
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
      bash \
      ca-certificates \
      curl \
      git \
      openssh-client \
      unzip \
    && curl --proto '=https' --tlsv1.2 -fsSL --retry 5 --retry-delay 2 --retry-max-time 120 https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gh \
    # Upgrade AFTER the installs, never before: the stale packages here
    # arrive as dependencies of the list above (libpcre2-8-0 comes in with
    # git and grep), so an upgrade placed first never reaches them. On
    # Debian 12 that kept libpcre2-8-0 at 10.42-1 while the archive had
    # 10.42-1+deb12u1, which left 2 HIGH alerts open per image.
    && apt-get full-upgrade -y \
    && apt-get autoremove -y --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    # dpkg, apt and ldconfig write the wall-clock time into these files on
    # every run, and rewrite-timestamp clamps mtimes, not contents: kept,
    # they alone made two builds of one commit differ.
    && rm -f /var/log/dpkg.log /var/log/alternatives.log \
         /var/log/apt/history.log /var/log/apt/term.log \
         /var/cache/ldconfig/aux-cache

# Install uv package manager (versioned binary, no pipe-to-shell)
ARG UV_VERSION
RUN set -eux; \
    case "$(dpkg --print-architecture)" in \
      amd64) UV_ARCH="x86_64-unknown-linux-musl" ;; \
      arm64) UV_ARCH="aarch64-unknown-linux-musl" ;; \
      *) printf 'Unsupported arch: %s\n' "$(dpkg --print-architecture)" >&2; exit 1 ;; \
    esac; \
    curl --proto '=https' --tlsv1.2 -fsSL --retry 5 --retry-delay 2 --retry-max-time 120 "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${UV_ARCH}.tar.gz" \
      -o "/tmp/uv-${UV_ARCH}.tar.gz"; \
    curl --proto '=https' --tlsv1.2 -fsSL --retry 5 --retry-delay 2 --retry-max-time 120 "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${UV_ARCH}.tar.gz.sha256" \
      -o "/tmp/uv-${UV_ARCH}.tar.gz.sha256"; \
    echo "$(cut -d' ' -f1 "/tmp/uv-${UV_ARCH}.tar.gz.sha256")  /tmp/uv-${UV_ARCH}.tar.gz" | sha256sum -c -; \
    tar -xzf "/tmp/uv-${UV_ARCH}.tar.gz" -C /tmp; \
    install -m 755 "/tmp/uv-${UV_ARCH}/uv" /usr/local/bin/uv; \
    install -m 755 "/tmp/uv-${UV_ARCH}/uvx" /usr/local/bin/uvx; \
    rm -rf "/tmp/uv-${UV_ARCH}.tar.gz" "/tmp/uv-${UV_ARCH}.tar.gz.sha256" "/tmp/uv-${UV_ARCH}"

COPY --from=fetch --link --chmod=0755 /tmp/bin/terraform /usr/local/bin/terraform
COPY --from=fetch --link --chmod=0755 /tmp/bin/terragrunt /usr/local/bin/terragrunt
COPY --from=fetch --link --chmod=0755 /tmp/bin/tflint /usr/local/bin/tflint
COPY --from=fetch --link --chmod=0755 /tmp/bin/sops /usr/local/bin/sops
COPY --from=fetch --link --chmod=0755 /tmp/bin/age /usr/local/bin/age
COPY --from=fetch --link --chmod=0755 /tmp/bin/age-keygen /usr/local/bin/age-keygen

# pre-commit and yamllint at the versions and hashes uv.lock records
# (requirements-devcontainer-tools.txt, the export of its devcontainer-tools
# group), in a venv of their own under /opt/devcontainer-tools: owned by
# root, read-only to vscode, and apart from anything users install. Only the
# two entry points are linked onto PATH. ensure-precommit, which every
# template runs on create, uses this copy and installs nothing. The export is
# bind-mounted, so it never lands in a layer.
#
# The interpreter is the CPython version devcontainer-base runs, installed by
# the pinned uv, which carries the sha256 of every Python build it can
# install and refuses a download that does not match. Debian's python3 is not
# used: trixie's 3.13 meets the lock's requires-python (>=3.12), but it is not
# the version the base runs, and it would put a python3 on every user's PATH.
#
# Then it is trimmed of what nothing here loads: libpython3.14.so* (the
# python executable is linked statically) and Tcl/Tk with tkinter, idlelib
# and turtle (no display in a dev container). pip and ensurepip stay.
#
# --only-binary :all: works because every package in the export publishes
# wheels for both architectures (musllinux too). Bytecode as in
# devcontainers/base: checked-hash, -f, every directory touched afterwards.
# Here it covers the interpreter's standard library as well, which uv
# installs uncompiled: vscode cannot write under /opt, so every run
# recompiled it in memory and `pre-commit --version` took twice as long.
# chmod: uv creates its .lock files world-writable (0666).
# renovate: datasource=docker depName=python versioning=docker
ARG TOOLS_PYTHON_VERSION=3.14.10
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    --mount=type=bind,source=requirements-devcontainer-tools.txt,target=/tmp/requirements-devcontainer-tools.txt \
    UV_PYTHON_INSTALL_DIR=/opt/devcontainer-tools/python \
      uv python install --no-bin "${TOOLS_PYTHON_VERSION}" \
    && UV_PYTHON_INSTALL_DIR=/opt/devcontainer-tools/python \
      uv venv --managed-python --no-python-downloads --python "${TOOLS_PYTHON_VERSION}" \
        /opt/devcontainer-tools/venv \
    && CFLAGS=-g0 UV_COMPILE_BYTECODE=0 uv pip install --python /opt/devcontainer-tools/venv/bin/python \
         --require-hashes --only-binary :all: -r /tmp/requirements-devcontainer-tools.txt \
    && PY_PREFIX="$(/opt/devcontainer-tools/venv/bin/python -c 'import sys; print(sys.base_prefix)')" \
    && PY_STDLIB="$(/opt/devcontainer-tools/venv/bin/python -c 'import sysconfig; print(sysconfig.get_path("stdlib"))')" \
    && rm -rf "${PY_PREFIX}"/lib/libpython3*.so* \
         "${PY_PREFIX}"/lib/libtcl* "${PY_PREFIX}"/lib/libtk* "${PY_PREFIX}"/lib/tcl* "${PY_PREFIX}"/lib/tk* \
         "${PY_PREFIX}"/lib/itcl* "${PY_PREFIX}"/lib/tdbc* "${PY_PREFIX}"/lib/thread* "${PY_PREFIX}"/bin/idle3* \
         "${PY_STDLIB}"/lib-dynload/_tkinter.* "${PY_STDLIB}"/tkinter "${PY_STDLIB}"/idlelib \
         "${PY_STDLIB}"/turtledemo "${PY_STDLIB}"/turtle.py \
    && ln -s /opt/devcontainer-tools/venv/bin/pre-commit /usr/local/bin/pre-commit \
    && ln -s /opt/devcontainer-tools/venv/bin/yamllint /usr/local/bin/yamllint \
    && /opt/devcontainer-tools/venv/bin/python -m compileall -q -f -j 0 --invalidation-mode checked-hash \
         -x '/site-packages/pip/' /opt/devcontainer-tools \
    && chmod -R go-w /opt/devcontainer-tools \
    && find /opt/devcontainer-tools -type d -exec touch {} +

# DL3064 fires on the *name* containing USERNAME, not on any secret: the
# value is the fixed, public account the Dev Containers specification
# expects every image to provide, and renaming it would break the spec.
# hadolint ignore=DL3064
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=${USER_UID}

RUN groupadd --gid "${USER_GID}" "${USERNAME}" \
    # --shell: useradd's default is /bin/sh, and VS Code opens its terminals
    # in the account's login shell when SHELL is not set.
    && useradd --uid "${USER_UID}" --gid "${USER_GID}" --shell /bin/bash -m "${USERNAME}" \
    # useradd stamps today's day number into the shadow entry's
    # last-change field, so the image changed with the build date even
    # when nothing else did. An empty field disables password aging,
    # which a locked (!) account never uses.
    && sed -i "s/^\(${USERNAME}:[^:]*\):[0-9]*:/\1::/" /etc/shadow \
    && install -d -o "${USERNAME}" -g "${USERNAME}" "${WORKSPACE}" \
    # terraform init failed with "mkdir /workspaces: permission denied" while
    # this directory did not exist. Owned by vscode here, it is also the owner
    # Docker gives the empty terraform-plugin-cache volume mounted on it.
    # Sticky and open to everyone because that owner is not enough: on a host
    # whose uid is not 1000, updateRemoteUserUID gives vscode the host's uid and
    # chowns only its home, and this is outside it, so the volume stayed 1000's.
    && install -d -m 1777 -o "${USERNAME}" -g "${USERNAME}" "${TF_PLUGIN_CACHE_DIR}" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" "/home/${USERNAME}/.local/bin" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" "/home/${USERNAME}/.local/share/uv" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" "/home/${USERNAME}/.cache/uv" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" "/home/${USERNAME}/.cache/pre-commit" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" /usr/local/share/devcontainer-skel/terraform \
    # install -d creates parents as root; hand ~/.cache and ~/.local to vscode
    && chown "${USERNAME}:${USERNAME}" \
         "/home/${USERNAME}/.cache" \
         "/home/${USERNAME}/.local" \
         "/home/${USERNAME}/.local/share"

COPY --chmod=0444 templates/pre-commit/terraform/.pre-commit-config.yaml /usr/local/share/devcontainer-skel/terraform/.pre-commit-config.yaml
COPY --chmod=0555 devcontainers/scripts/ensure-precommit.sh /usr/local/bin/ensure-precommit

ENV PATH="/home/${USERNAME}/.local/bin:${PATH}"

# The system file, not ~/.gitconfig. The Dev Containers extension copies the
# user's .gitconfig into the container only when the one already there has
# nothing but [filter] and [safe] sections, so the [init] section this line
# wrote with --global kept the user's name, email and aliases out.
RUN git config --system init.defaultBranch main

USER ${USERNAME}

WORKDIR ${WORKSPACE}

CMD ["/bin/bash"]

# devcontainer-terraform-aws: the image above plus AWS CLI v2, built with
# --target terraform-aws. The plain image no longer carries the CLI.
FROM terraform AS terraform-aws

LABEL org.opencontainers.image.description="Terraform devcontainer with Terragrunt, TFLint, SOPS, age, AWS CLI v2 and uv-powered pre-commit"

# The stage above ends as vscode; the install writes to /usr/local. Numeric
# uid so the id resolves without /etc/passwd (DL3066).
USER 0

# The version and the per-architecture hashes are in the script, which
# devcontainer-ansible-aws runs too. Bind-mounted, so it never lands in a
# layer.
RUN --mount=type=bind,source=devcontainers/scripts/install-aws-cli.sh,target=/tmp/install-aws-cli.sh \
    bash /tmp/install-aws-cli.sh

# DL3064: see the terraform stage.
# hadolint ignore=DL3064
ARG USERNAME=vscode
USER ${USERNAME}

# The plain image again, as the LAST stage: a Dockerfile's default target is
# its last stage, and every build without --target must keep producing
# devcontainer-terraform (ci.yml, test-containers.yml, sbom-verification.yml,
# benchmark.yml, the local-build/ dev containers, and .devcontainer/, which
# is a copy of this file). Nothing goes below this line;
# tests/container-structure/no-aws.yaml fails if the AWS CLI reaches the
# default target.
FROM terraform
