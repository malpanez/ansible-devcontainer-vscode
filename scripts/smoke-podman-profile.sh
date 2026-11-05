#!/usr/bin/env bash
# Run podman-smoke-test --ee in a devcontainer-ansible-podman image the way
# devcontainers/ansible/devcontainer.podman.json runs it on Docker, without
# building anything: release.yml's gate does this to the digest it is about to
# tag, on amd64 and on arm64.
#
# smoke-devcontainer-image.sh has no podman stack and gives this image the
# ansible checks only, so a release could tag an image in which podman cannot
# run a container. ci.yml's "Test the podman profile" proves the profile on an
# image it builds, for amd64; its podman smoke test uses --privileged, which is
# not what the template does.
#
# runArgs come from the profile, so the check follows it. As the template does,
# the container runs as vscode with a named volume on the podman storage and a
# host directory on /workspace. The profile's other mounts are caches and stay
# out: they would share state with whatever else uses those volume names.
#
# The check pulls from quay.io and ghcr.io, so it gets three attempts, as
# ci.yml's podman smoke test does. Every attempt starts from a new volume and a new
# directory: an attempt that passes only because an earlier one left something
# behind has proved nothing. Both are removed afterwards.
#
# Usage: smoke-podman-profile.sh IMAGE_REF
#   IMAGE_REF  any reference docker run takes; the gate passes <image>@<digest>
#
# Exits 1 if runArgs cannot be read or the check keeps failing. Usage errors
# exit 2.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="${REPO_ROOT}/devcontainers/ansible/devcontainer.podman.json"
STORAGE_TARGET="/home/vscode/.local/share/containers"
WORKSPACE_TARGET="/workspace"
ATTEMPTS=3
IMAGE_REF=""
RUN_ARGS=()
VOLUME=""
WORKSPACE=""

usage() {
  echo "Usage: $(basename "$0") IMAGE_REF" >&2
  exit 2
}

read_run_args() {
  local run_args

  if ! run_args="$(jq -er '.runArgs | arrays | select(length > 0) | .[]' "${PROFILE}")"; then
    echo "::error::${PROFILE} has no readable runArgs" >&2
    return 1
  fi
  mapfile -t RUN_ARGS <<<"${run_args}"
}

# Never fails: a leftover is worth a warning, not a verdict on the image. The
# files in the directory belong to vscode and to the subuids of its podman, so
# only root in a container can delete them on a host with another uid.
remove_attempt_state() {
  if [[ -n "${VOLUME}" ]]; then
    docker volume rm --force "${VOLUME}" >/dev/null \
      || echo "::warning::could not remove the volume ${VOLUME}" >&2
    VOLUME=""
  fi
  if [[ -n "${WORKSPACE}" ]]; then
    docker run --rm --user root --mount "type=bind,source=${WORKSPACE},target=/scratch" \
      "${IMAGE_REF}" find /scratch -mindepth 1 -delete \
      || echo "::warning::could not empty ${WORKSPACE} as root" >&2
    rm -rf -- "${WORKSPACE}" \
      || echo "::warning::could not remove ${WORKSPACE}" >&2
    WORKSPACE=""
  fi
}
trap remove_attempt_state EXIT

run_attempt() {
  local attempt="$1"
  local status=0

  VOLUME="podman-smoke-$$-${attempt}"
  WORKSPACE="$(mktemp -d)" || return 1
  # Writable by vscode, whose uid in the image is not the runner's. The Dev
  # Containers extension solves this by changing vscode's uid; nothing here does.
  chmod 0777 "${WORKSPACE}" || return 1
  docker run --rm "${RUN_ARGS[@]}" --user vscode \
    --mount "type=volume,source=${VOLUME},target=${STORAGE_TARGET}" \
    --mount "type=bind,source=${WORKSPACE},target=${WORKSPACE_TARGET}" \
    --workdir "${WORKSPACE_TARGET}" \
    "${IMAGE_REF}" podman-smoke-test --ee || status=$?
  remove_attempt_state
  return "${status}"
}

main() {
  local attempt

  if (($# != 1)) || [[ -z "$1" ]]; then
    usage
  fi
  IMAGE_REF="$1"
  read_run_args

  for ((attempt = 1; attempt <= ATTEMPTS; attempt++)); do
    if run_attempt "${attempt}"; then
      echo "podman-smoke-test --ee passed on ${IMAGE_REF} (attempt ${attempt})."
      return 0
    fi
    if ((attempt < ATTEMPTS)); then
      echo "::warning::podman smoke test attempt ${attempt} of ${IMAGE_REF} failed; retrying" >&2
      sleep "$((attempt * 20))"
    fi
  done
  echo "::error::podman smoke test of ${IMAGE_REF} failed after ${ATTEMPTS} attempts" >&2
  return 1
}

main "$@"
