#!/usr/bin/env bash
# Ensure a usable pre-commit configuration for the current stack.
set -Eeuo pipefail

STACK="${DEVCONTAINER_STACK:-}"
if [[ -z "${STACK}" ]]; then
  echo "DEVCONTAINER_STACK environment variable is not defined; cannot select template" >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not available on PATH; unable to bootstrap pre-commit" >&2
  exit 1
fi

WORKSPACE_DIR="${WORKSPACE:-${WORKSPACE_FOLDER:-/workspace}}"
TEMPLATE_ROOT="${DEVCONTAINER_TEMPLATE_ROOT:-/usr/local/share/devcontainer-skel}"
TEMPLATE_PATH="${TEMPLATE_ROOT}/${STACK}/.pre-commit-config.yaml"
CONFIG_PATH="${WORKSPACE_DIR}/.pre-commit-config.yaml"

if [[ ! -d "${WORKSPACE_DIR}" ]]; then
  echo "Workspace directory ${WORKSPACE_DIR} does not exist yet; skipping ensure-precommit" >&2
  exit 0
fi

if [[ ! -f "${CONFIG_PATH}" && -f "${TEMPLATE_PATH}" ]]; then
  mkdir -p "$(dirname "${CONFIG_PATH}")"
  cp "${TEMPLATE_PATH}" "${CONFIG_PATH}"
  echo "Copied ${STACK} pre-commit template into workspace"
fi

export PATH="${HOME}/.local/bin:${PATH}"
export PRE_COMMIT_HOME="${PRE_COMMIT_HOME:-${WORKSPACE_DIR}/.cache/pre-commit}"
mkdir -p "${PRE_COMMIT_HOME}"

# Ensure pre-commit is installed via uv toolchain (idempotent).
uv tool install pre-commit >/dev/null 2>&1

cd "${WORKSPACE_DIR}"
uvx pre-commit install -f
uvx pre-commit autoupdate || true
