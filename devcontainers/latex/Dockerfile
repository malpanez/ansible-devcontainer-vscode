# syntax=docker/dockerfile:1

ARG LATEX_IMAGE=miktex/miktex:latest
ARG LATEX_DISTRO=miktex

FROM ${LATEX_IMAGE}

# BuildKit platform arguments
ARG TARGETPLATFORM
ARG TARGETARCH
ARG TARGETOS

LABEL maintainer="malpanez"
LABEL description="LaTeX Development Container (MiKTeX or TeX Live)"

ENV DEBIAN_FRONTEND=noninteractive \
    LATEX_DISTRO=${LATEX_DISTRO}

# Install additional tooling required by both distributions
RUN apt-get update && apt-get install -y --no-install-recommends \
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

# Create non-root vscode user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

USER $USERNAME
WORKDIR /workspace

CMD ["/bin/bash"]
