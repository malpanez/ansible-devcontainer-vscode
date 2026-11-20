# syntax=docker/dockerfile:1.28
# The builder and the runtime stage both start from the hardened
# devcontainer-base layer (apt tools, gh, checksum-verified uv, pre-commit
# and yamllint, vscode user), so the two stages and the base pulled beside
# them share it. The digest below is NOT what published or gated images
# are built on: build-containers.yml overrides BASE_IMAGE with the base
# built in the same run, and ci.yml's Build Devcontainer and test-containers.yml
# with a base built from the pull request. The pin is what local builds resolve, and the
# workflows that build this file without gating it (sbom-verification,
# benchmark). Renovate refreshes it, so it never needs bumping by hand.
#
# BASE_IMAGE deliberately carries BOTH the :main tag and the @sha256
# digest. The digest is what actually resolves (Docker ignores the tag
# when a digest is present), so the pin stays immutable for Scorecard's
# Pinned-Dependencies; the tag is what tells Renovate which stream to
# track — drop it and Renovate falls back to :latest, stops refreshing
# this digest, and the pin rots until GHCR prunes it and the build dies
# (that is exactly what broke main on 2026-07-24). Linters that want
# "tag or digest, not both" are false positives here: hadolint DL3006 is
# suppressed below; SonarCloud docker:S8431 has no in-repo suppression
# (Dockerfiles allow no trailing NOSONAR comment, and automatic analysis
# ignores sonar.issue.ignore.*), so it must be deactivated in the
# project's quality profile instead.
ARG BASE_IMAGE=ghcr.io/malpanez/devcontainer-base:main@sha256:5595df5ee9ca25e537a4d18974d2f8b56baf81578d26b3db126ae1f22975f33b

# Stage 1: install the locked Python stack. Build tools live only in this
# stage: arm64 needs gcc + libonig-dev because onigurumacffi (pulled in by
# ansible-navigator) publishes no aarch64 wheel.
# hadolint ignore=DL3006
FROM ${BASE_IMAGE} AS python-builder

# devcontainer-base ends as vscode; apt and a --system install need root.
# Numeric uid so the id resolves without /etc/passwd (DL3066). DL3002 is
# suppressed because this is a builder stage: it is never the final image,
# only /usr/local is copied out of it.
# hadolint ignore=DL3002
USER 0

# hadolint ignore=DL3008
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
      gcc \
      libc6-dev \
      libffi-dev \
      libonig-dev \
    && rm -rf /var/lib/apt/lists/*

# The hashed uv.lock export, not pyproject.toml: resolving pyproject at
# build time picked whatever PyPI served that day, so the cached CI layer
# and the uncached nightly publish shipped different versions, neither of
# them the lock's (certifi, 2026-10-26).
COPY requirements-ansible.txt /tmp/requirements-ansible.txt

# CFLAGS=-g0 because arm64 compiles onigurumacffi here from its sdist, and
# the -g in Python's own CFLAGS wrote uv's randomly named build directory
# into the .so's debug info, so the file differed in every build.
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    CFLAGS=-g0 UV_COMPILE_BYTECODE=0 uv pip install --system --require-hashes -r /tmp/requirements-ansible.txt

# ansible-core plus the collections pinned with their sha256 in
# collections.txt, instead of the ansible package's bundle of 92.
COPY devcontainers/ansible/collections.txt devcontainers/ansible/install-collections.sh /tmp/ansible-collections/
RUN SITE="$(python3 -c 'import sysconfig; print(sysconfig.get_path("purelib"))')" \
    && bash /tmp/ansible-collections/install-collections.sh "${SITE}" /tmp/ansible-collections/collections.txt

# Checked-hash bytecode instead of uv's timestamp .pyc, which the
# exporter's rewrite-timestamp would leave stale, pip left uncompiled, and
# every directory touched afterwards: see devcontainers/base for all three.
# ansible_collections gets none: ansible-core imports collection code
# through its own loader, which compiles the source in memory and never
# reads __pycache__, so bytecode there is dead weight (160 MiB of it in
# v1.4.0, for the 92 bundled collections).
RUN SITE="$(python3 -c 'import sysconfig; print(sysconfig.get_path("purelib"))')" \
    && python3 -m compileall -q -f -j 0 --invalidation-mode checked-hash \
         -x '/site-packages/(pip|ansible_collections)/' "${SITE}" \
    && find "$(dirname "${SITE}")" -type d -exec touch {} +

# Stage 1b: what devcontainer-ansible-aws adds to the Python stack, on top
# of stage 1, so the ansible-aws stage below syncs only the difference.
FROM python-builder AS python-builder-aws

# boto3 and botocore with their dependencies: requirements-aws.txt is the
# hashed export of the lock's aws group, bind-mounted so it never lands in a
# layer. Every package in it publishes a pure-Python wheel, so
# --only-binary :all: holds on arm64 too and no setup.py runs. CFLAGS and
# UV_COMPILE_BYTECODE as in stage 1.
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    --mount=type=bind,source=requirements-aws.txt,target=/tmp/requirements-aws.txt \
    CFLAGS=-g0 UV_COMPILE_BYTECODE=0 uv pip install --system --require-hashes --only-binary :all: \
      -r /tmp/requirements-aws.txt

# amazon.aws, pinned with its sha256 in collections-aws.txt. The installer
# is the one stage 1 copied in.
RUN --mount=type=bind,source=devcontainers/ansible/collections-aws.txt,target=/tmp/ansible-collections/collections-aws.txt \
    SITE="$(python3 -c 'import sysconfig; print(sysconfig.get_path("purelib"))')" \
    && bash /tmp/ansible-collections/install-collections.sh "${SITE}" /tmp/ansible-collections/collections-aws.txt

# Bytecode exactly as in stage 1. It recompiles stage 1's packages too, to
# the same bytes, which the --checksum sync below then leaves alone.
RUN SITE="$(python3 -c 'import sysconfig; print(sysconfig.get_path("purelib"))')" \
    && python3 -m compileall -q -f -j 0 --invalidation-mode checked-hash \
         -x '/site-packages/(pip|ansible_collections)/' "${SITE}" \
    && find "$(dirname "${SITE}")" -type d -exec touch {} +

# Stage 1c: ansible-core 2.16 side by side with the default core, for
# targets on Python 2.7 and 3.6 (RHEL 7 and 8), which ansible-core 2.17
# removed. The ansible stage copies /opt/ansible-core-2.16 whole and links
# the <tool>-2.16 commands; plain ansible* stays the default core.
#
# 2.16 needs Python >= 3.10 and the base runs 3.14, which 2.16 predates, so
# it runs on its own CPython 3.12, installed and verified by the pinned uv
# exactly as devcontainers/terraform installs TOOLS_PYTHON_VERSION, trimmed
# the same way and further: the interpreter's own pip and the C headers
# (13 MiB), since the venv has no pip and nothing is compiled against it,
# and nobody runs that interpreter but the venv. The hashed export of its own lock
# (devcontainers/ansible/legacy/ansible-core-2.16), not the root uv.lock,
# which pins the default core. Its collections go into the venv's
# site-packages through the 2.16 ansible-galaxy (PATH), so they are checked
# against 2.16 and the default core never sees them. Bytecode as in
# devcontainers/terraform, stdlib included (vscode cannot write under /opt),
# none for ansible_collections (stage 1).
# hadolint ignore=DL3006
FROM ${BASE_IMAGE} AS python-builder-legacy

# hadolint ignore=DL3002
USER 0

# renovate: datasource=docker depName=python versioning=docker
ARG LEGACY_ANSIBLE_PYTHON_VERSION=3.12.16
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    --mount=type=bind,source=devcontainers/ansible/legacy/ansible-core-2.16/requirements.txt,target=/tmp/requirements-legacy.txt \
    --mount=type=bind,source=devcontainers/ansible/collections-legacy-2.16.txt,target=/tmp/collections-legacy.txt \
    --mount=type=bind,source=devcontainers/ansible/install-collections.sh,target=/tmp/install-collections.sh \
    UV_PYTHON_INSTALL_DIR=/opt/ansible-core-2.16/python \
      uv python install --no-bin "${LEGACY_ANSIBLE_PYTHON_VERSION}" \
    && UV_PYTHON_INSTALL_DIR=/opt/ansible-core-2.16/python \
      uv venv --managed-python --no-python-downloads --python "${LEGACY_ANSIBLE_PYTHON_VERSION}" \
        /opt/ansible-core-2.16/venv \
    && CFLAGS=-g0 UV_COMPILE_BYTECODE=0 uv pip install --python /opt/ansible-core-2.16/venv/bin/python \
         --require-hashes --only-binary :all: -r /tmp/requirements-legacy.txt \
    && PY_PREFIX="$(/opt/ansible-core-2.16/venv/bin/python -c 'import sys; print(sys.base_prefix)')" \
    && PY_STDLIB="$(/opt/ansible-core-2.16/venv/bin/python -c 'import sysconfig; print(sysconfig.get_path("stdlib"))')" \
    && SITE="$(/opt/ansible-core-2.16/venv/bin/python -c 'import sysconfig; print(sysconfig.get_path("purelib"))')" \
    && rm -rf "${PY_PREFIX}"/lib/libpython3*.so* \
         "${PY_PREFIX}"/lib/libtcl* "${PY_PREFIX}"/lib/libtk* "${PY_PREFIX}"/lib/tcl* "${PY_PREFIX}"/lib/tk* \
         "${PY_PREFIX}"/lib/itcl* "${PY_PREFIX}"/lib/tdbc* "${PY_PREFIX}"/lib/thread* "${PY_PREFIX}"/bin/idle3* \
         "${PY_STDLIB}"/lib-dynload/_tkinter.* "${PY_STDLIB}"/tkinter "${PY_STDLIB}"/idlelib \
         "${PY_STDLIB}"/turtledemo "${PY_STDLIB}"/turtle.py \
         "${PY_STDLIB}"/__pycache__/turtle.* \
         "${PY_PREFIX}"/include "${PY_PREFIX}"/bin/pip* \
         "${PY_STDLIB}"/site-packages/pip "${PY_STDLIB}"/site-packages/pip-*.dist-info \
    && PATH="/opt/ansible-core-2.16/venv/bin:${PATH}" \
      bash /tmp/install-collections.sh "${SITE}" /tmp/collections-legacy.txt \
    && /opt/ansible-core-2.16/venv/bin/python -m compileall -q -f -j 0 --invalidation-mode checked-hash \
         -x '/site-packages/(pip|ansible_collections)/' /opt/ansible-core-2.16 \
    && chmod -R go-w /opt/ansible-core-2.16 \
    && find /opt/ansible-core-2.16 -type d -exec touch {} +

# Stage 2: runtime image without any build toolchain. devcontainer-ansible,
# but not the last stage: the empty one at the end of this file, which
# repeats it, is.
# hadolint ignore=DL3006
FROM ${BASE_IMAGE} AS ansible

# devcontainer-base ends as vscode; everything below until the USER switch
# at the end of this stage needs root (apt, install -d, COPY into /usr/local).
# Numeric uid so the id resolves without /etc/passwd (DL3066).
USER 0

ARG IMAGE_VENDOR="malpanez"

LABEL org.opencontainers.image.source="https://github.com/malpanez/ansible-devcontainer-vscode" \
      org.opencontainers.image.description="Ansible devcontainer with uv-managed Python toolchain and hardened defaults" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="${IMAGE_VENDOR}"

ENV DEBIAN_FRONTEND=noninteractive \
    WORKSPACE=/workspace \
    DEVCONTAINER_STACK=ansible \
    DEVCONTAINER_TEMPLATE_ROOT=/usr/local/share/devcontainer-skel

# Published builds get their base from the same run (build-containers.yml),
# but PR and local builds resolve the BASE_IMAGE pin, which can trail the
# published base by days; this upgrade closes that gap without waiting for
# Renovate.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update \
    && apt-get full-upgrade -y \
    && apt-get autoremove -y --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    # Wall-clock timestamps in the contents: see devcontainers/base.
    && rm -f /var/log/dpkg.log /var/log/alternatives.log \
         /var/log/apt/history.log /var/log/apt/term.log \
         /var/cache/ldconfig/aux-cache

# Bring /usr/local/lib and /usr/local/bin to the builder's state, writing
# only what differs from this stage's base. The builder started from the
# same base, so the Python stdlib, uv and the site-packages base already
# ships are byte-identical and stay in the base's layers: base installs
# pre-commit, yamllint and their dependencies from
# requirements-devcontainer-tools.txt, the same uv.lock as
# requirements-ansible.txt, so the builder's install leaves them alone.
# Copying both trees whole, as this stage used to, stored all of that a
# second time.
# --delete removes what the builder removed. That happens only when this
# base and the lock disagree, such as a pinned BASE_IMAGE that trails a lock
# bump: uv replaces the package and the base's old dist-info would
# otherwise stay beside the new one, both reported by scanners (pre-commit
# 4.6.2 next to 4.7.0, 2026-10-28). --checksum and no -t: a file is
# rewritten only when its content differs. Syncing an mtime alone would
# copy the whole file up into this layer, and the builder rewrote every
# .pyc of the base.
RUN --mount=type=bind,from=python-builder,source=/usr/local,target=/mnt/python-builder \
    rsync -rlpgoD --checksum --delete /mnt/python-builder/lib/ /usr/local/lib/ \
    && rsync -rlpgoD --checksum --delete /mnt/python-builder/bin/ /usr/local/bin/

# ansible-core 2.16 (stage 1c). The commands go through wrapper.sh, which
# gives 2.16 its own ANSIBLE_HOME: see the script. After the rsync above,
# whose --delete would remove the links.
COPY --from=python-builder-legacy --link /opt/ansible-core-2.16 /opt/ansible-core-2.16
COPY --link --chmod=0555 devcontainers/ansible/legacy/ansible-core-2.16/wrapper.sh /opt/ansible-core-2.16/bin/wrapper
RUN for TOOL in ansible ansible-config ansible-console ansible-doc ansible-galaxy \
      ansible-inventory ansible-playbook ansible-pull ansible-vault; do \
      ln -s /opt/ansible-core-2.16/bin/wrapper "/usr/local/bin/${TOOL}-2.16"; \
    done

# DL3064 fires on the *name* containing USERNAME, not on any secret: the
# value is the fixed, public account the Dev Containers specification
# expects every image to provide, and renaming it would break the spec.
# hadolint ignore=DL3064
ARG USERNAME=vscode

# devcontainer-base already creates the user; add the stack directories
RUN install -d -o "${USERNAME}" -g "${USERNAME}" "/home/${USERNAME}/.local/share/uv" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" "/home/${USERNAME}/.cache/uv" \
    && install -d -o "${USERNAME}" -g "${USERNAME}" /usr/local/share/devcontainer-skel/ansible \
    && chown "${USERNAME}:${USERNAME}" \
         "/home/${USERNAME}/.local" \
         "/home/${USERNAME}/.local/share"

COPY --link --chmod=0444 templates/pre-commit/ansible/.pre-commit-config.yaml /usr/local/share/devcontainer-skel/ansible/.pre-commit-config.yaml
COPY --link --chmod=0555 devcontainers/scripts/ensure-precommit.sh /usr/local/bin/ensure-precommit

ENV PATH="/home/${USERNAME}/.local/bin:${PATH}"

# The system file, not ~/.gitconfig. The Dev Containers extension copies the
# user's .gitconfig into the container only when the one already there has
# nothing but [filter] and [safe] sections, so the [init] section this line
# wrote with --global kept the user's name, email and aliases out.
RUN git config --system init.defaultBranch main

USER ${USERNAME}

WORKDIR ${WORKSPACE}

CMD ["/bin/bash"]

# devcontainer-ansible-aws: the image above plus amazon.aws, boto3 and
# botocore (stage 1b) and AWS CLI v2, built with --target ansible-aws.
# build-containers.yml builds it on the base from the same run, as it does
# devcontainer-ansible.
FROM ansible AS ansible-aws

LABEL org.opencontainers.image.description="Ansible devcontainer with amazon.aws, boto3, AWS CLI v2, a uv-managed Python toolchain and hardened defaults"

# The stage above ends as vscode. Numeric uid (DL3066).
USER 0

# Stage 1b's additions only, as the stage above syncs stage 1's. lib/ with
# --delete, which the stage above made identical to stage 1's lib/; bin/
# without it, because the stage above added ensure-precommit there after
# its own sync. The AWS CLI goes in afterwards: a sync of bin/ with --delete
# would remove it.
RUN --mount=type=bind,from=python-builder-aws,source=/usr/local,target=/mnt/python-builder \
    rsync -rlpgoD --checksum --delete /mnt/python-builder/lib/ /usr/local/lib/ \
    && rsync -rlpgoD --checksum /mnt/python-builder/bin/ /usr/local/bin/

# The version and the per-architecture hashes are in the script, which
# devcontainer-terraform-aws runs too. Bind-mounted, so it never lands in a
# layer.
RUN --mount=type=bind,source=devcontainers/scripts/install-aws-cli.sh,target=/tmp/install-aws-cli.sh \
    bash /tmp/install-aws-cli.sh

# DL3064: see the ansible stage.
# hadolint ignore=DL3064
ARG USERNAME=vscode
USER ${USERNAME}

# The plain image again, as the LAST stage: a Dockerfile's default target is
# its last stage, and every build without --target must keep producing
# devcontainer-ansible (ci.yml, test-containers.yml, sbom-verification.yml,
# benchmark.yml, the local-build/ dev containers). Nothing goes below this
# line; tests/container-structure/no-aws.yaml fails if the AWS CLI reaches
# the default target.
FROM ansible
