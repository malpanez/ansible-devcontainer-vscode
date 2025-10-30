#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROLE_DIR="${REPO_ROOT}/roles"

# Run ansible-test sanity across every role in the repository by creating a
# temporary collection skeleton for each role (ansible-test expects the
# ansible_collections/<namespace>/<collection> layout).

if ! command -v ansible-test >/dev/null 2>&1; then
  echo "ansible-test command not found. Install ansible-core to continue." >&2
  exit 1
fi

if [[ ! -d "${ROLE_DIR}" ]]; then
  echo "No roles directory found at ${ROLE_DIR}; skipping ansible-test sanity checks."
  exit 0
fi

mapfile -t ROLES < <(find "${ROLE_DIR}" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)

if [[ "${#ROLES[@]}" -eq 0 ]]; then
  echo "No roles detected under ${ROLE_DIR}; nothing to test."
  exit 0
fi

PY_VERSION="${ANSIBLE_TEST_PYTHON_VERSION:-3.12}"
NAMESPACE="${ANSIBLE_TEST_NAMESPACE:-local}"
COLLECTION_NAME="${ANSIBLE_TEST_COLLECTION_NAME:-devcontainer_workspace}"

if locale -a 2>/dev/null | grep -qi '^en_US\.utf8$'; then
  export LC_ALL="en_US.UTF-8"
  export LANG="en_US.UTF-8"
else
  export LC_ALL="${LC_ALL:-C.UTF-8}"
  export LANG="${LANG:-C.UTF-8}"
fi

WORK_ROOT="$(mktemp -d)"
trap 'rm -rf "${WORK_ROOT}"' EXIT

use_rsync=false
if command -v rsync >/dev/null 2>&1; then
  use_rsync=true
fi

for ROLE_NAME in "${ROLES[@]}"; do
  COLLECTION_ROOT="${WORK_ROOT}/${ROLE_NAME}/ansible_collections/${NAMESPACE}/${COLLECTION_NAME}"
  ROLE_DEST="${COLLECTION_ROOT}/roles/${ROLE_NAME}"
  mkdir -p "${ROLE_DEST}"

  if [[ "${use_rsync}" == true ]]; then
    rsync -a --delete "${ROLE_DIR}/${ROLE_NAME}/" "${ROLE_DEST}/"
  else
    cp -a "${ROLE_DIR}/${ROLE_NAME}/." "${ROLE_DEST}/"
  fi

  cat <<EOF >"${COLLECTION_ROOT}/galaxy.yml"
namespace: ${NAMESPACE}
name: ${COLLECTION_NAME}
version: 0.0.1
description: Temporary collection wrapper for ansible-test sanity on role ${ROLE_NAME}
EOF

  touch "${COLLECTION_ROOT}/README.md"

  echo ">> Running ansible-test sanity for role '${ROLE_NAME}' (Python ${PY_VERSION})"
  pushd "${COLLECTION_ROOT}" >/dev/null
  ansible-test sanity \
    --python "${PY_VERSION}" \
    --color yes \
    --local \
    "$@"
  popd >/dev/null
done
