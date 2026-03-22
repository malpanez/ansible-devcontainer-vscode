#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TEMPLATE_ROOT="${REPO_ROOT}/devcontainers"
TARGET_DIR="${REPO_ROOT}/.devcontainer"
CONTAINER_CLI=""

usage() {
  cat <<'EOF'
Usage: scripts/use-devcontainer.sh [options] <stack>

Options:
  -p, --prune     Remove stopped containers and volumes tied to this workspace.
  -h, --help      Show this message.

Stacks available under devcontainers/:
  - ansible
  - golang
  - latex
  - terraform

Copies the selected template into .devcontainer/.
EOF
  return 0
}

STACK=""
PRUNE_WORKSPACE_ARTIFACTS=false

if command -v docker >/dev/null 2>&1; then
  CONTAINER_CLI="docker"
elif command -v podman >/dev/null 2>&1; then
  CONTAINER_CLI="podman"
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--prune)
      PRUNE_WORKSPACE_ARTIFACTS=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
    *)
      if [[ -z "${STACK}" ]]; then
        STACK="$1"
        shift
      else
        echo "Unexpected argument: $1" >&2
        usage
        exit 1
      fi
      ;;
  esac
done

if [[ -z "${STACK}" ]]; then
  usage
  exit 1
fi
TEMPLATE_DIR="${TEMPLATE_ROOT}/${STACK}"

if [[ ! -d "${TEMPLATE_DIR}" ]]; then
  echo "Unknown stack '${STACK}'. Available:" >&2
  ls "${TEMPLATE_ROOT}" >&2
  exit 1
fi

echo ">> Switching Dev Container to '${STACK}' ..."
rm -rf "${TARGET_DIR}"
mkdir -p "${TARGET_DIR}"

if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete "${TEMPLATE_DIR}/" "${TARGET_DIR}/"
else
  cp -R "${TEMPLATE_DIR}/." "${TARGET_DIR}/"
fi

echo ">> .devcontainer now matches '${STACK}'. Reopen in Container from VS Code to apply."

cleanup_workspace_artifacts() {
  if [[ "${PRUNE_WORKSPACE_ARTIFACTS}" != true ]]; then
    return 0
  fi

  if [[ -z "${CONTAINER_CLI}" ]]; then
    echo ">> Container CLI not found; skipping optional clean-up." >&2
    return 0
  fi

  local workspace_path="${REPO_ROOT}"

  echo ">> Pruning Dev Container resources for '${workspace_path}' using ${CONTAINER_CLI} ..."

  local container_ids=""
  container_ids="$(${CONTAINER_CLI} ps -aq --filter "label=devcontainer.local_folder=${workspace_path}")"
  if [[ -n "${container_ids}" ]]; then
    while IFS= read -r container_id; do
      [[ -z "${container_id}" ]] && continue
      ${CONTAINER_CLI} rm -f "${container_id}" >/dev/null
    done <<< "${container_ids}"
  fi

  local volume_names=""
  volume_names="$(${CONTAINER_CLI} volume ls --filter "label=devcontainer.local_folder=${workspace_path}" --format '{{.Name}}')"
  if [[ -n "${volume_names}" ]]; then
    while IFS= read -r volume_name; do
      [[ -z "${volume_name}" ]] && continue
      ${CONTAINER_CLI} volume rm "${volume_name}" >/dev/null
    done <<< "${volume_names}"
  fi

  echo ">> Clean-up complete."
  return 0
}

cleanup_workspace_artifacts
