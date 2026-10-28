#!/usr/bin/env bash
# Pass docker/metadata-action's labels on without
# org.opencontainers.image.description.
#
# metadata-action always emits that label with the repository description, and
# a build-time label replaces the Dockerfile LABEL with the same key. Every
# published image therefore carried the same generic repository text instead of
# the per-stack description its Dockerfile sets (seen on devcontainer-golang:main
# and devcontainer-terraform:main, 2026-10-28).
#
# Reads the newline-separated list from LABELS. Writes it as the `labels`
# output when GITHUB_OUTPUT is set, otherwise prints it.
set -euo pipefail

LABELS="${LABELS:-}"

if [[ -z "${LABELS//[[:space:]]/}" ]]; then
  printf 'strip-description-label: LABELS is empty; metadata-action produced no labels\n' >&2
  exit 1
fi

FILTERED="$(grep -v '^org\.opencontainers\.image\.description=' <<<"${LABELS}" || true)"

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  DELIMITER="labels_$(od -An -N8 -tx1 /dev/urandom | tr -d ' \n')"
  {
    printf 'labels<<%s\n' "${DELIMITER}"
    printf '%s\n' "${FILTERED}"
    printf '%s\n' "${DELIMITER}"
  } >>"${GITHUB_OUTPUT}"
else
  printf '%s\n' "${FILTERED}"
fi
