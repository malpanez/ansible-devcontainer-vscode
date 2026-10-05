#!/usr/bin/env bash
# Derive the toolchain versions CI tests with from the Dockerfiles that ship
# them, instead of pinning them a second time in the workflow.
#
# ci.yml carried PYTHON_VERSION "3.13", GO_VERSION "1.25" and
# TERRAFORM_VERSION "1.15.7" in its env block. None had a Renovate
# annotation, so they never moved, while the images went on to ship Python
# 3.14.7, Go 1.27.1 and Terraform 1.16.4: CI was validating a toolchain the
# product did not contain. Reading the versions from the Dockerfiles leaves
# one place to bump, and Renovate already bumps it.
#
# Prints three key=value lines, in the form $GITHUB_OUTPUT expects:
#   python_version=<major>.<minor>          FROM python:           (base)
#   go_version=<major>.<minor>              FROM golang:           (golang)
#   terraform_version=<major>.<minor>.<patch>  ARG TERRAFORM_VERSION= (terraform)
#
# Every value is resolved before anything is printed, so a failure never
# leaves a partial set behind. BASE_DOCKERFILE, GOLANG_DOCKERFILE and
# TERRAFORM_DOCKERFILE point the script at other files (the tests use them).
set -euo pipefail

SCRIPT_NAME="derive-toolchain-versions"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BASE_DOCKERFILE="${BASE_DOCKERFILE:-${REPO_ROOT}/devcontainers/base/Dockerfile}"
GOLANG_DOCKERFILE="${GOLANG_DOCKERFILE:-${REPO_ROOT}/devcontainers/golang/Dockerfile}"
TERRAFORM_DOCKERFILE="${TERRAFORM_DOCKERFILE:-${REPO_ROOT}/devcontainers/terraform/Dockerfile}"

fail() {
  printf '%s: %s\n' "${SCRIPT_NAME}" "$1" >&2
  exit 1
}

extract_version() {
  local FILE="$1"
  local PATTERN="$2"
  local EXPECTED="$3"
  local VALUE

  if [ ! -f "${FILE}" ]; then
    fail "no such file: ${FILE}"
  fi

  VALUE="$(sed -n "/${PATTERN}/{s//\\1/p;q;}" "${FILE}")"

  if [ -z "${VALUE}" ]; then
    fail "no \"${EXPECTED}\" line in ${FILE}"
  fi

  printf '%s\n' "${VALUE}"
}

main() {
  local PYTHON_VERSION
  local GO_VERSION
  local TERRAFORM_VERSION

  PYTHON_VERSION="$(extract_version "${BASE_DOCKERFILE}" \
    '^FROM python:\([0-9]\{1,\}\.[0-9]\{1,\}\).*' \
    'FROM python:<major>.<minor>')"
  GO_VERSION="$(extract_version "${GOLANG_DOCKERFILE}" \
    '^FROM golang:\([0-9]\{1,\}\.[0-9]\{1,\}\).*' \
    'FROM golang:<major>.<minor>')"
  TERRAFORM_VERSION="$(extract_version "${TERRAFORM_DOCKERFILE}" \
    '^ARG TERRAFORM_VERSION=\([0-9]\{1,\}\.[0-9]\{1,\}\.[0-9]\{1,\}\)[[:space:]]*$' \
    'ARG TERRAFORM_VERSION=<major>.<minor>.<patch>')"

  printf 'python_version=%s\n' "${PYTHON_VERSION}"
  printf 'go_version=%s\n' "${GO_VERSION}"
  printf 'terraform_version=%s\n' "${TERRAFORM_VERSION}"
}

main "$@"
