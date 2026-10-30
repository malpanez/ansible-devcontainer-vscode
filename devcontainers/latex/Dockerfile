# syntax=docker/dockerfile:1.28
# renovate: datasource=github-releases depName=tectonic-typesetting/tectonic
ARG TECTONIC_VERSION=0.17.0
FROM debian:bookworm-slim@sha256:7ff6ba31527b9e336162fa061746c366c4b2032f4d2cff2078bea43f78efe3f8

ARG TECTONIC_VERSION
ARG TARGETARCH
ARG IMAGE_VENDOR="malpanez"

LABEL org.opencontainers.image.source="https://github.com/malpanez/ansible-devcontainer-vscode" \
      org.opencontainers.image.description="Lightweight LaTeX devcontainer powered by Tectonic and uv pre-commit tooling" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="${IMAGE_VENDOR}"

ENV DEBIAN_FRONTEND=noninteractive \
    UV_INSTALL_DIR=/usr/local/bin \
    UV_LINK_MODE=copy \
    WORKSPACE=/workspace \
    DEVCONTAINER_STACK=latex \
    DEVCONTAINER_TEMPLATE_ROOT=/usr/local/share/devcontainer-skel \
    TECTONIC_CACHE_DIR=/home/vscode/.cache/Tectonic

# hadolint ignore=DL3008
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
      bash \
      ca-certificates \
      curl \
      fontconfig \
      git \
      perl \
      sudo \
      unzip \
    # Upgrade AFTER the installs, never before: the stale packages here
    # arrive as dependencies of the list above (libpcre2-8-0 comes in with
    # git and grep), so an upgrade placed first never reaches them. The
    # pinned bookworm digest ships libpcre2-8-0 10.42-1 while bookworm
    # has 10.42-1+deb12u1, which left 2 HIGH alerts open per image.
    && apt-get full-upgrade -y \
    && apt-get autoremove -y --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    # dpkg, apt and ldconfig write the wall-clock time into these files on
    # every run, and rewrite-timestamp clamps mtimes, not contents: kept,
    # they alone made two builds of one commit differ.
    && rm -f /var/log/dpkg.log /var/log/alternatives.log \
         /var/log/apt/history.log /var/log/apt/term.log \
         /var/cache/ldconfig/aux-cache \
    # fontconfig's postinst caches each font directory with its mtime, so
    # the cache differed in every build, and once rewrite-timestamp clamps
    # those mtimes it no longer matches: fontconfig ignored it and built a
    # per-user cache anyway (about 10 ms for these fonts, once per home).
    && rm -f /var/cache/fontconfig/*.cache-*

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# Tectonic publishes no checksum manifest; hashes pinned per release.
# musl artifacts on both arches: they are static, so they keep working
# regardless of the base image's glibc (the gnu builds broke on 0.16.9).
RUN set -eux; \
    ARCH="${TARGETARCH:-$(dpkg --print-architecture)}"; \
    case "${ARCH}" in \
      amd64|x86_64) TECTONIC_ARCH="x86_64-unknown-linux-musl"; \
        TECTONIC_SHA256="8533d07f9ccbd7a65824b9e0459041bca34af1eb33daba48f59215593753a3b7" ;; \
      arm64|aarch64) TECTONIC_ARCH="aarch64-unknown-linux-musl"; \
        TECTONIC_SHA256="b10954a95404f3ab2328d2fa59a5ebab8e657f893fab096f98be8db7c0c979b8" ;; \
      *) echo "Unsupported architecture ${ARCH}" >&2; exit 1 ;; \
    esac; \
    curl --proto '=https' --tlsv1.2 -fsSL --retry 5 --retry-delay 2 --retry-max-time 120 "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%40${TECTONIC_VERSION}/tectonic-${TECTONIC_VERSION}-${TECTONIC_ARCH}.tar.gz" \
      -o /tmp/tectonic.tar.gz; \
    echo "${TECTONIC_SHA256}  /tmp/tectonic.tar.gz" | sha256sum -c -; \
    TMP_DIR="$(mktemp -d /tmp/tectonic.XXXXXX)"; \
    tar -xzf /tmp/tectonic.tar.gz -C "${TMP_DIR}"; \
    SRC="$(find "${TMP_DIR}" -type f -name tectonic -perm -u+x | head -n1 || true)"; \
    if [ -z "${SRC}" ] || [ ! -f "${SRC}" ]; then \
      echo "Unable to locate tectonic binary" >&2; exit 1; \
    fi; \
    install -m 0755 "${SRC}" /usr/local/bin/tectonic; \
    rm -rf /tmp/tectonic.tar.gz "${TMP_DIR}"

# renovate: datasource=github-releases depName=astral-sh/uv
ARG UV_VERSION=0.13.6
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
# install and refuses a download that does not match. Debian's python3 is no
# option: bookworm ships 3.11, below the lock's requires-python (>=3.12), so
# the export has no wheel it could verify.
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
    && useradd --uid "${USER_UID}" --gid "${USER_GID}" -m "${USERNAME}" \
    # useradd stamps today's day number into the shadow entry's
    # last-change field, so the image changed with the build date even
    # when nothing else did. An empty field disables password aging,
    # which a locked (!) account never uses.
    && sed -i "s/^\(${USERNAME}:[^:]*\):[0-9]*:/\1::/" /etc/shadow \
    && install -d -o "${USERNAME}" -g "${USERNAME}" "${WORKSPACE}" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" "/home/${USERNAME}/.local/bin" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" "/home/${USERNAME}/.cache/uv" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" "/home/${USERNAME}/.cache/Tectonic" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" /usr/local/share/devcontainer-skel/latex \
    # install -d creates parents as root; hand ~/.cache and ~/.local to vscode
    && chown "${USERNAME}:${USERNAME}" \
         "/home/${USERNAME}/.cache" \
         "/home/${USERNAME}/.local"

COPY --link --chmod=0444 templates/pre-commit/latex/.pre-commit-config.yaml /usr/local/share/devcontainer-skel/latex/.pre-commit-config.yaml
COPY --link --chmod=0555 devcontainers/scripts/ensure-precommit.sh /usr/local/bin/ensure-precommit

ENV PATH="/home/${USERNAME}/.local/bin:${PATH}"

USER ${USERNAME}

RUN git config --global init.defaultBranch main

WORKDIR ${WORKSPACE}

CMD ["/bin/bash"]
