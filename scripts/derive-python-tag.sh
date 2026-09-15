#!/usr/bin/env bash
# Derive the Python stream tag for devcontainer-base from the image it is
# actually built FROM, instead of typing it by hand in the workflows.
#
# It was hardcoded `py313` in three places (build-containers.yml twice,
# ci.yml once) while devcontainers/base/Dockerfile built FROM
# python:3.14.7-slim-bookworm. The published ghcr.io/<owner>/devcontainer-base
# :py313 therefore shipped Python 3.14.7 -- a tag asserting a version it did
# not have, protected under that name in cleanup-ghcr.yml and documented as a
# "Python 3.13 base layer". Deriving it means a base bump renames the tag
# instead of silently invalidating it.
set -euo pipefail

DOCKERFILE="${1:-devcontainers/base/Dockerfile}"

if [ ! -f "${DOCKERFILE}" ]; then
  printf 'derive-python-tag: no such file: %s\n' "${DOCKERFILE}" >&2
  exit 1
fi

VERSION="$(sed -n 's/^FROM python:\([0-9]\{1,\}\.[0-9]\{1,\}\).*/\1/p' "${DOCKERFILE}" | head -1)"

if [ -z "${VERSION}" ]; then
  printf 'derive-python-tag: no "FROM python:<major>.<minor>" line in %s\n' "${DOCKERFILE}" >&2
  exit 1
fi

printf 'py%s\n' "${VERSION//./}"
