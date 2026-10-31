# syntax=docker/dockerfile:1.28
FROM golang:1.27.3-alpine3.23@sha256:754d5200fc3edae76d3b6598a9a3fac7e74981ee6a5413ab955025f185753ef2

# Upgrade every package the pinned base ships, not a named list. The FROM
# digest freezes the Alpine package set at the moment it was cut, so every
# fix Alpine publishes afterwards is missing here until the base is rebuilt
# and bumped. A named list only carries the fixes someone already knew
# about -- this line used to name libcrypto3 and libssl3 alone -- while the
# plain form covers whatever the base ships next. Same rule as the
# full-upgrade in devcontainers/ansible/Dockerfile.podman.
#
# It reaches the base's own packages only. Whatever `apk add` pulls in
# below (pcre2 arrives with git) is not installed yet at this point and is
# fetched at its current version when that layer is built.
#
# apk appends the wall-clock time of every run to /var/log/apk.log, and
# rewrite-timestamp clamps mtimes, not contents: kept, it alone made two
# builds of one commit differ.
RUN apk upgrade --no-cache \
    && rm -f /var/log/apk.log

ARG IMAGE_VENDOR="malpanez"
# renovate: datasource=github-releases depName=astral-sh/uv
ARG UV_VERSION=0.13.6

LABEL org.opencontainers.image.source="https://github.com/malpanez/ansible-devcontainer-vscode" \
      org.opencontainers.image.description="Golang devcontainer with uv-driven pre-commit workflow" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="${IMAGE_VENDOR}"

# LANG: the golang base sets none. musl itself is UTF-8 regardless; tools that
# read LANG are not.
ENV LANG=C.UTF-8 \
    UV_INSTALL_DIR=/usr/local/bin \
    UV_LINK_MODE=copy \
    WORKSPACE=/workspace \
    DEVCONTAINER_STACK=golang \
    DEVCONTAINER_TEMPLATE_ROOT=/usr/local/share/devcontainer-skel \
    GOPATH=/home/vscode/go

# libstdc++ (it brings libgcc) is on VS Code's list of prerequisites for
# Alpine; without it the Dev Containers extension runs `apk update && apk add
# libstdc++` itself when it starts. openssh-client-default is the package
# behind Alpine's virtual openssh-client: without it `git ls-remote git@...`
# stopped at "error: cannot run ssh".
RUN apk add --no-cache \
      bash=~5 \
      curl=~8 \
      git=~2 \
      libstdc++=~15 \
      openssh-client-default=~10 \
      sudo=~1 \
    && rm -f /var/log/apk.log

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN set -eux; \
    case "$(uname -m)" in \
      x86_64) UV_ARCH="x86_64-unknown-linux-musl" ;; \
      aarch64) UV_ARCH="aarch64-unknown-linux-musl" ;; \
      *) printf 'Unsupported arch: %s\n' "$(uname -m)" >&2; exit 1 ;; \
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
# install and refuses a download that does not match. Alpine's python3 would
# be smaller, but it is 3.12, a different Python from every other image, and
# it moves with apk instead of a pin.
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

RUN addgroup -g "${USER_GID}" "${USERNAME}" \
    && adduser -D -u "${USER_UID}" -G "${USERNAME}" -s /bin/bash "${USERNAME}" \
    # adduser stamps today's day number into the shadow entry's
    # last-change field, so the image changed with the build date even
    # when nothing else did. An empty field disables password aging,
    # which a locked (!) account never uses.
    && sed -i "s/^\(${USERNAME}:[^:]*\):[0-9]*:/\1::/" /etc/shadow \
    && install -d -o "${USERNAME}" -g "${USERNAME}" "${WORKSPACE}" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" "/home/${USERNAME}/.local/bin" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" "/home/${USERNAME}/.cache/uv" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" "/home/${USERNAME}/.cache/pre-commit" \
    # The template mounts named volumes on these two. A new volume takes the
    # owner of the directory it lands on, and a directory the image does not
    # have is created for root: `go build` and `go get` both died with
    # permission denied.
    && install -d -o "${USERNAME}" -g "${USERNAME}" "/home/${USERNAME}/.cache/go-build" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" "/home/${USERNAME}/go/pkg/mod" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" /usr/local/share/devcontainer-skel/golang \
    # install -d creates parents as root; hand ~/.cache, ~/.local and the Go
    # tree above the module cache to vscode
    && chown "${USERNAME}:${USERNAME}" \
         "/home/${USERNAME}/.cache" \
         "/home/${USERNAME}/.local" \
         "/home/${USERNAME}/go" \
         "/home/${USERNAME}/go/pkg"

COPY --link --chmod=0444 templates/pre-commit/golang/.pre-commit-config.yaml /usr/local/share/devcontainer-skel/golang/.pre-commit-config.yaml
COPY --link --chmod=0555 devcontainers/scripts/ensure-precommit.sh /usr/local/bin/ensure-precommit

ENV PATH="/home/${USERNAME}/.local/bin:/home/${USERNAME}/go/bin:${PATH}"

# The system file, not ~/.gitconfig. The Dev Containers extension copies the
# user's .gitconfig into the container only when the one already there has
# nothing but [filter] and [safe] sections, so the [init] section this line
# wrote with --global kept the user's name, email and aliases out.
RUN git config --system init.defaultBranch main

USER ${USERNAME}

WORKDIR ${WORKSPACE}

CMD ["/bin/bash"]
