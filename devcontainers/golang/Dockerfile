# syntax=docker/dockerfile:1

FROM golang:1.22-bookworm

# BuildKit platform arguments
ARG TARGETPLATFORM
ARG TARGETARCH
ARG TARGETOS

LABEL maintainer="malpanez"
LABEL description="Golang Development Container"

ENV DEBIAN_FRONTEND=noninteractive

# Install base packages commonly needed for Go development
RUN apt-get update \
    && apt-get full-upgrade -y \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        openssh-client \
        bash-completion \
        make \
        build-essential \
        pkg-config \
        sudo \
        ripgrep \
    && apt-get autoremove -y --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user to match VS Code expectations
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Enable Go module proxy caching location
ENV GOPATH=/go
ENV PATH="/go/bin:${PATH}"

USER $USERNAME
WORKDIR /workspace

CMD ["/bin/bash"]
