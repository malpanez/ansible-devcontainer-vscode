# syntax=docker/dockerfile:1

ARG LATEX_IMAGE=miktex/miktex:latest
ARG LATEX_DISTRO=miktex

FROM ${LATEX_IMAGE}

ARG LATEX_DISTRO

# BuildKit platform arguments
ARG TARGETPLATFORM
ARG TARGETARCH
ARG TARGETOS

LABEL maintainer="malpanez"
LABEL description="LaTeX Development Container (MiKTeX or TeX Live)"

ENV DEBIAN_FRONTEND=noninteractive \
    LATEX_DISTRO=${LATEX_DISTRO} \
    QT_QPA_PLATFORM=offscreen

# Install additional tooling required by both distributions
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libx11-xcb1 \
        libxcb1 \
        libxcb-render0 \
        libxcb-shape0 \
        libxcb-xfixes0 \
        libxcb-randr0 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-icccm4 \
        libxcb-util1 \
        libxcb-xkb1 \
        libxkbcommon-x11-0 \
        libsm6 \
        libice6 \
        libglu1-mesa \
        libopengl0 \
        git \
        make \
        latexmk \
        biber \
        ghostscript \
        sudo \
    && rm -rf /var/lib/apt/lists/*

# Configure distribution-specific behaviour
RUN if [ "${LATEX_DISTRO}" = "miktex" ]; then \
        miktexsetup --shared=yes --verbose=false finish && \
        initexmf --set-config-value="[MPM]AutoInstall=1" --admin && \
        initexmf --update-fndb --admin; \
    else \
        tlmgr option repository https://mirrors.ctan.org/systems/texlive/tlnet && \
        tlmgr install latexmk biber; \
    fi

# Create non-root vscode user (reuse existing gid/uid if present)
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN if ! getent group "${USER_GID}" >/dev/null; then \
        groupadd --gid "${USER_GID}" "${USERNAME}"; \
    fi \
    && if ! id -u "${USERNAME}" >/dev/null 2>&1; then \
        useradd --uid "${USER_UID}" --gid "${USER_GID}" -m "${USERNAME}"; \
    else \
        usermod --gid "${USER_GID}" "${USERNAME}" \
          && mkdir -p "/home/${USERNAME}"; \
    fi \
    && echo "${USERNAME} ALL=(root) NOPASSWD:ALL" > "/etc/sudoers.d/${USERNAME}" \
    && chmod 0440 "/etc/sudoers.d/${USERNAME}" \
    && chown -R "${USERNAME}:${USER_GID}" "/home/${USERNAME}"

USER $USERNAME
WORKDIR /workspace

CMD ["/bin/bash"]
