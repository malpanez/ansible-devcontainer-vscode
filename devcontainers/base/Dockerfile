# syntax=docker/dockerfile:1.28
FROM python:3.14.10-slim-bookworm@sha256:516b51cb9db2ef061e465c803e50f64361b82cefd91e525b889b967b83e83527

# BuildKit platform arguments
ARG TARGETPLATFORM
ARG TARGETARCH
ARG TARGETOS

LABEL maintainer="alpanez.alcalde@gmail.com" \
      description="Shared Python base layer for infrastructure devcontainers" \
      org.opencontainers.image.description="Shared Python base layer for infrastructure devcontainers" \
      org.opencontainers.image.source="https://github.com/malpanez/ansible-devcontainer-vscode" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="malpanez"

ENV DEBIAN_FRONTEND=noninteractive
# LANG: the python base sets it on some digests only (3.14.8 did not, 3.14.10
# does), so a digest bump could turn it off.
ENV LANG=C.UTF-8
ENV UV_INSTALL_DIR=/usr/local/bin
ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1
# renovate: datasource=github-releases depName=astral-sh/uv
ARG UV_VERSION=0.13.6

# Common system packages used across Python-based stacks.
# hadolint ignore=DL3008,DL3015
RUN --mount=type=cache,target=/var/lib/apt/lists,id=apt-lists-${TARGETARCH},sharing=locked \
    --mount=type=cache,target=/var/cache/apt,id=apt-cache-${TARGETARCH},sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        gnupg \
        jq \
        openssh-client \
        rsync \
        sshpass \
        sudo \
        unzip \
        vim-tiny \
    # full-upgrade AFTER the install, not before: libssh2-1 is not present
    # in python:*-slim, it arrives as a dependency of curl/git, so an
    # upgrade running first never touched it and the image kept shipping
    # 1.10.0-3+b1 while bookworm-security had 1.10.0-3+deb12u1
    # (CRITICAL CVE-2026-7598). Upgrading last covers pulled-in deps too.
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

# Install GitHub CLI (gh) to avoid DevContainer features rebuild
# https://github.com/cli/cli/blob/trunk/docs/install_linux.md
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# hadolint ignore=DL3008
RUN --mount=type=cache,target=/var/lib/apt/lists,id=apt-lists-${TARGETARCH},sharing=locked \
    --mount=type=cache,target=/var/cache/apt,id=apt-cache-${TARGETARCH},sharing=locked \
    curl --proto '=https' --tlsv1.2 -fsSL --retry 5 --retry-delay 2 --retry-max-time 120 https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gh \
    && apt-get autoremove -y --purge \
    && apt-get clean \
    && rm -f /var/log/dpkg.log /var/log/alternatives.log \
         /var/log/apt/history.log /var/log/apt/term.log \
         /var/cache/ldconfig/aux-cache

# Configure non-root workspace user.
# DL3064 fires on the *name* containing USERNAME, not on any secret: the
# value is the fixed, public account the Dev Containers specification
# expects every image to provide, and renaming it would break the spec.
# hadolint ignore=DL3064
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# The uv cache lives in a cache mount, as the apt caches above do, so the
# downloaded wheels never land in a layer: written to /root/.cache/uv they
# shipped in every image built on this one, and scanners catalogued those
# archived copies as installed packages. The export is bind-mounted, not
# copied, so it never lands in a layer either; the build context is the
# repository root.
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    --mount=type=bind,source=requirements-devcontainer-tools.txt,target=/tmp/requirements-devcontainer-tools.txt \
    groupadd --gid "${USER_GID}" "${USERNAME}" \
    # --shell: useradd's default is /bin/sh, and VS Code opens its terminals
    # in the account's login shell when SHELL is not set.
    && useradd --uid "${USER_UID}" --gid "${USER_GID}" --shell /bin/bash -m "${USERNAME}" \
    # useradd stamps today's day number into the shadow entry's
    # last-change field, so the image changed with the build date even
    # when nothing else did. An empty field disables password aging,
    # which a locked (!) account never uses.
    && sed -i "s/^\(${USERNAME}:[^:]*\):[0-9]*:/\1::/" /etc/shadow \
    && install -d -m 755 "/home/${USERNAME}/.cache/pre-commit" \
    && install -d -m 700 "/home/${USERNAME}/.ansible/tmp" \
    && install -d -m 755 "/home/${USERNAME}/.ansible/galaxy_cache" \
    && chown -R "${USERNAME}:${USERNAME}" "/home/${USERNAME}/.cache" \
    && chown -R "${USERNAME}:${USERNAME}" "/home/${USERNAME}/.ansible" \
    && case "$(dpkg --print-architecture)" in \
         amd64) UV_ARCH="x86_64-unknown-linux-musl" ;; \
         arm64) UV_ARCH="aarch64-unknown-linux-musl" ;; \
         *) printf 'Unsupported arch: %s\n' "$(dpkg --print-architecture)" >&2; exit 1 ;; \
       esac \
    && curl --proto '=https' --tlsv1.2 -fsSL --retry 5 --retry-delay 2 --retry-max-time 120 "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${UV_ARCH}.tar.gz" \
         -o "/tmp/uv-${UV_ARCH}.tar.gz" \
    && curl --proto '=https' --tlsv1.2 -fsSL --retry 5 --retry-delay 2 --retry-max-time 120 "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${UV_ARCH}.tar.gz.sha256" \
         -o "/tmp/uv-${UV_ARCH}.tar.gz.sha256" \
    && echo "$(cut -d' ' -f1 "/tmp/uv-${UV_ARCH}.tar.gz.sha256")  /tmp/uv-${UV_ARCH}.tar.gz" | sha256sum -c - \
    && tar -xzf "/tmp/uv-${UV_ARCH}.tar.gz" -C /tmp \
    && install -m 755 "/tmp/uv-${UV_ARCH}/uv" /usr/local/bin/uv \
    && install -m 755 "/tmp/uv-${UV_ARCH}/uvx" /usr/local/bin/uvx \
    && rm -rf "/tmp/uv-${UV_ARCH}.tar.gz" "/tmp/uv-${UV_ARCH}.tar.gz.sha256" "/tmp/uv-${UV_ARCH}" \
    # pre-commit and yamllint come from requirements-devcontainer-tools.txt,
    # the uv.lock export of the devcontainer-tools group: every package,
    # dependencies included, at the lock's version and hash. A pin on
    # pre-commit alone left its dependencies to whatever PyPI served that
    # day, and Debian's yamllint (1.29.0, which pulled in Debian's own
    # python3.11) shipped beside the lock's.
    #
    # --only-binary :all: refuses sdists, so no setup.py from a
    # dependency runs at build time (docker:S8541). Safe here because
    # every package in that export publishes wheels for amd64 and arm64;
    # the ansible install sites cannot use it (they pull onigurumacffi,
    # which has no aarch64 wheel).
    #
    # Bytecode is compiled here in checked-hash mode, not by uv. uv writes
    # timestamp .pyc files, which record each source's mtime; the
    # exporter's rewrite-timestamp then clamps that mtime to
    # SOURCE_DATE_EPOCH and every .pyc goes stale, and since vscode cannot
    # write to /usr/local/lib, each import recompiles in memory on every
    # run. A checked-hash .pyc records the source's hash, which survives
    # the clamp and is the same in every build; -f converts any timestamp
    # .pyc already present too. The ENV above stays 1 for what users
    # install later, into directories they own.
    #
    # pip (from the python image) is skipped: uv never compiled it, users
    # install with uv, and its bytecode cost about 6 MiB for nothing.
    #
    # The final touch: when parallel workers copy up sibling directories
    # through overlayfs at once, their parent sometimes ends with the
    # build's time and sometimes keeps its old mtime, so the clamp moved
    # it in one build and not the next (a directory under pip, two podman
    # builds). Touched, every directory ends past SOURCE_DATE_EPOCH and is
    # clamped alike.
    && CFLAGS=-g0 UV_COMPILE_BYTECODE=0 uv pip install --system --require-hashes --only-binary :all: \
         -r /tmp/requirements-devcontainer-tools.txt \
    # uv locks a system environment through /tmp/uv-<hash>.lock, mode 0666, and
    # leaves it behind: a world-writable file in this image and in the ansible
    # images built on it. Their builder stages leave one too, but only
    # /usr/local is copied out of those.
    && rm -f /tmp/uv-*.lock \
    && SITE="$(python3 -c 'import sysconfig; print(sysconfig.get_path("purelib"))')" \
    && python3 -m compileall -q -f -j 0 --invalidation-mode checked-hash \
         -x '/site-packages/pip/' "${SITE}" \
    && find "$(dirname "${SITE}")" -type d -exec touch {} + \
    # /usr/bin/python3 came from Debian's python3.11, which Debian's yamllint
    # pulled in. Inventories that set ansible_python_interpreter to that path
    # keep working: it now points at this image's Python, the one the ansible
    # images install their stack into. ln fails if a package ships the path.
    && ln -s /usr/local/bin/python3 /usr/bin/python3 \
    && mkdir -p /workspace \
    && chown "${USERNAME}:${USERNAME}" /workspace
ENV PATH="/usr/local/bin:${PATH}"
WORKDIR /workspace

# Drop root. This image is published under its own tags and is therefore
# runnable on its own, not only as a FROM for the stacks -- and it defaulted
# to uid 0 while every derived image correctly ran as vscode. Images that
# build on it must re-enter root explicitly for their apt work, which makes
# the privileged section of each Dockerfile visible instead of implicit.
USER ${USERNAME}
