# syntax=docker/dockerfile:1.7
ARG BASE_IMAGE=ghcr.io/malpanez/devcontainer-base:py312
FROM ${BASE_IMAGE}

LABEL maintainer="alpanez.alcalde@gmail.com"
LABEL description="Ansible Development Environment 2025"

ENV DEBIAN_FRONTEND=noninteractive
ENV UV_INSTALL_DIR=/usr/local/bin
ENV UV_LINK_MODE=copy

USER root

# Copiar definición de dependencias (solo stack Ansible)
COPY pyproject.toml uv.lock requirements-ansible.txt /tmp/

# Instalar paquetes Python con uv (aplicando el lock específico)
RUN uv pip install --system --requirement /tmp/requirements-ansible.txt

USER vscode

RUN git config --global init.defaultBranch main

WORKDIR /workspace

CMD ["/bin/bash"]
