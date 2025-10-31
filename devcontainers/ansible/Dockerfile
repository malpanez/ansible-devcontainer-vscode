# syntax=docker/dockerfile:1.7
ARG BASE_IMAGE=ghcr.io/malpanez/devcontainer-base:py312
FROM ${BASE_IMAGE}

# BuildKit platform arguments
ARG TARGETPLATFORM
ARG TARGETARCH
ARG TARGETOS

LABEL maintainer="alpanez.alcalde@gmail.com"
LABEL description="Ansible Development Environment 2025"

ENV DEBIAN_FRONTEND=noninteractive
ENV UV_INSTALL_DIR=/usr/local/bin
ENV UV_LINK_MODE=copy

USER root

USER vscode

RUN git config --global init.defaultBranch main

WORKDIR /workspace

CMD ["/bin/bash"]
