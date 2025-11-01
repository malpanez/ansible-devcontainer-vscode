#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TEMPLATE_ROOT="${REPO_ROOT}/devcontainers"

STACK="ansible"
USER_COMMAND=""
BUILD_ARGS=()
PREFER_BUILD=false

usage() {
  cat <<'EOF'
Usage: scripts/debug-devcontainer.sh [options] [-- <command>]

Options:
  -s, --stack <name>       Dev Container stack under devcontainers/ (default: ansible)
  -b, --build-arg A=B      Additional build arguments passed to devcontainer build/up (repeatable)
  --prefer-build           Rewrite devcontainer.json to build from the local Dockerfile instead of the published image.
  -h, --help               Show this help.

Stacks available today: ansible, golang, latex, terraform.

Examples:
  scripts/debug-devcontainer.sh --stack golang
  scripts/debug-devcontainer.sh --stack latex -- ./scripts/run-smoke-tests.sh
  scripts/debug-devcontainer.sh -b LATEX_DISTRO=texlive --stack latex

The script performs:
  1. devcontainer build --workspace-folder devcontainers/<stack>
  2. devcontainer up --workspace-folder devcontainers/<stack>
  3. devcontainer exec --workspace-folder devcontainers/<stack> <command>
If no command is supplied, the shell for the container is opened.
EOF
}

ensure_cli() {
  if ! command -v devcontainer >/dev/null 2>&1; then
    echo "Error: devcontainer CLI not found. Install @devcontainers/cli (npm install -g @devcontainers/cli)." >&2
    exit 1
  fi
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -s|--stack)
        STACK="$2"
        shift 2
        ;;
      -b|--build-arg)
        BUILD_ARGS+=("--build-arg" "$2")
        shift 2
        ;;
      --prefer-build)
        PREFER_BUILD=true
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      --)
        shift
        USER_COMMAND="$*"
        break
        ;;
      *)
        echo "Unknown option: $1" >&2
        usage
        exit 1
        ;;
    esac
  done
}

prepare_workspace() {
  local source_folder="$1"
  local prefer_build="$2"

  if [[ "${prefer_build}" != "true" || ! -f "${source_folder}/devcontainer.json" ]]; then
    echo "${source_folder}"
    return
  fi

  if ! command -v jq >/dev/null 2>&1; then
    echo "${source_folder}"
    return
  fi

  local temp_dir
  temp_dir=$(mktemp -d)
  cp "${source_folder}/devcontainer.json" "${temp_dir}/devcontainer.json"

  if jq -e 'has("image") and (has("build") | not)' "${temp_dir}/devcontainer.json" >/dev/null; then
    local dockerfile_path
    local build_context
    dockerfile_path="$(cd "${source_folder}" && pwd)/Dockerfile"
    build_context="$(cd "${source_folder}/.." && pwd)"
    DOCKERFILE_PATH="${dockerfile_path}" BUILD_CONTEXT="${build_context}" \
      jq 'del(.image) + {build: {dockerfile: env.DOCKERFILE_PATH, context: env.BUILD_CONTEXT}}' \
        "${temp_dir}/devcontainer.json" \
        > "${temp_dir}/devcontainer.json.tmp"
    mv "${temp_dir}/devcontainer.json.tmp" "${temp_dir}/devcontainer.json"
  fi

  echo "${temp_dir}"
}

main() {
  parse_args "$@"
  ensure_cli

  local workspace_folder="${TEMPLATE_ROOT}/${STACK}"
  if [[ ! -d "${workspace_folder}" ]]; then
    echo "Error: stack '${STACK}' not found under ${TEMPLATE_ROOT}." >&2
    exit 1
  fi

  local prepared_workspace
  prepared_workspace=$(prepare_workspace "${workspace_folder}" "${PREFER_BUILD}")
  local cleanup=false
  if [[ "${prepared_workspace}" != "${workspace_folder}" ]]; then
    cleanup=true
  fi

  if [[ "${cleanup}" == "true" ]]; then
    trap 'rm -rf "${prepared_workspace}"' EXIT
  fi

  echo ">> Building Dev Container stack '${STACK}' ..."
  devcontainer build --workspace-folder "${prepared_workspace}" "${BUILD_ARGS[@]}"

  echo ">> Bringing up Dev Container stack '${STACK}' ..."
  devcontainer up --workspace-folder "${prepared_workspace}" "${BUILD_ARGS[@]}"

  if [[ -n "${USER_COMMAND}" ]]; then
    echo ">> Executing command inside '${STACK}': ${USER_COMMAND}"
    devcontainer exec --workspace-folder "${prepared_workspace}" -- bash -lc "${USER_COMMAND}"
  else
    echo ">> Launching interactive shell inside '${STACK}' ..."
    devcontainer exec --workspace-folder "${prepared_workspace}" -- bash
  fi

  if [[ "${cleanup}" == "true" ]]; then
    rm -rf "${prepared_workspace}"
    trap - EXIT
  fi
}

main "$@"
