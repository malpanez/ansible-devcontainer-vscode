#!/usr/bin/env bash
# Bring up a Docker profile of a template on the image built from this commit,
# and check that its remoteUser reaches a Docker daemon.
#
# A profile pins a published image, so running it as it ships tests the last
# release: a change that breaks a profile showed up only when Renovate moved the
# pin, after the release it broke. The config brought up here is the profile
# with its "image" replaced by the "build" of the stack's
# local-build/devcontainer.json. Lifecycle commands, mounts, features and users
# stay the profile's.
#
# `devcontainer up` is not the check: it reports success on a profile with no
# daemon and no access to one, and the CLI does not look at how a feature's
# entrypoint exits. Hence the check, as the remoteUser, after it.
#
# The container is left running. ci.yml relies on the runner to clean up.
#
# Usage: [BASE_IMAGE=image] test-devcontainer-profile.sh STACK PROFILE CHECK
#   STACK       a directory under devcontainers/
#   PROFILE     a config file in that directory
#   CHECK       the Docker command that must succeed, such as 'docker version'
#   BASE_IMAGE  build argument for a Dockerfile that takes one (ansible)
#
# Run from the repository root: the build context is ${localWorkspaceFolder}.
# Exits 1 if the container does not come up or the check keeps failing. Usage
# errors exit 2.
set -euo pipefail

UP_ATTEMPTS=3
CHECK_ATTEMPTS=30
CHECK_DELAY_SECONDS=2
CONFIG_DIR=""

cleanup() {
  if [[ -n "${CONFIG_DIR}" ]]; then
    rm -rf -- "${CONFIG_DIR}"
  fi
}
trap cleanup EXIT

usage() {
  echo "Usage: [BASE_IMAGE=image] $(basename "$0") STACK PROFILE CHECK" >&2
  exit 2
}

render_config() {
  local template_dir="$1"
  local profile="$2"
  local local_build="${template_dir}/local-build/devcontainer.json"
  local dockerfile

  # Absolute, because the config moves: the CLI takes no other file name than
  # devcontainer.json, so a profile can only run from a directory of its own.
  dockerfile="$(realpath "${template_dir}/local-build/$(jq -r '.build.dockerfile' "${local_build}")")"
  jq --slurpfile local_build "${local_build}" \
    --arg dockerfile "${dockerfile}" \
    --arg base_image "${BASE_IMAGE:-}" \
    'del(.image)
    | .build = $local_build[0].build
    | .build.dockerfile = $dockerfile
    | if $base_image == "" then . else .build.args.BASE_IMAGE = $base_image end' \
    "${template_dir}/${profile}"
}

# Retried, with --remove-existing-container, for the reasons in ci.yml's "Test
# devcontainer up" step; a feature adds a pull and an apt-get to what can fail.
bring_up() {
  local attempt

  for ((attempt = 1; attempt <= UP_ATTEMPTS; attempt++)); do
    if devcontainer up --remove-existing-container "${DEVCONTAINER_ARGS[@]}"; then
      return 0
    fi
    if ((attempt == UP_ATTEMPTS)); then
      echo "::error::devcontainer up of ${PROFILE} failed after ${UP_ATTEMPTS} attempts" >&2
      return 1
    fi
    echo "::warning::devcontainer up attempt ${attempt} failed; retrying" >&2
    sleep "$((attempt * 20))"
  done
}

# A bounded wait, because the CLI goes on as soon as the container prints that it
# started, which is before a feature's entrypoint runs: dockerd takes seconds to
# answer, and the socket's group changes a moment later.
wait_for_check() {
  local attempt

  for ((attempt = 1; attempt <= CHECK_ATTEMPTS; attempt++)); do
    if devcontainer exec "${DEVCONTAINER_ARGS[@]}" -- \
      bash -c "id -un | grep -qx vscode && ${CHECK}"; then
      return 0
    fi
    echo "'${CHECK}' failed as vscode (attempt ${attempt} of ${CHECK_ATTEMPTS})"
    sleep "${CHECK_DELAY_SECONDS}"
  done
  echo "::error::'${CHECK}' did not succeed as vscode in ${PROFILE} after ${CHECK_ATTEMPTS} attempts" >&2
  return 1
}

(($# == 3)) || usage
STACK="$1"
PROFILE="$2"
CHECK="$3"
TEMPLATE_DIR="devcontainers/${STACK}"
if [[ ! -f "${TEMPLATE_DIR}/${PROFILE}" ]]; then
  echo "::error::${TEMPLATE_DIR}/${PROFILE} does not exist" >&2
  usage
fi

CONFIG_DIR="$(mktemp -d)"
render_config "${TEMPLATE_DIR}" "${PROFILE}" > "${CONFIG_DIR}/devcontainer.json"
DEVCONTAINER_ARGS=(--workspace-folder . --config "${CONFIG_DIR}/devcontainer.json")

bring_up
wait_for_check
