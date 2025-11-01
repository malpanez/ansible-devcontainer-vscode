#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TEMPLATE_ROOT="${REPO_ROOT}/devcontainers"

usage() {
  cat <<'EOF'
Usage: scripts/check-devcontainer.sh [devcontainer build options...]

Runs `devcontainer build --workspace-folder devcontainers/<stack>` for every
Dev Container template in this repository. Extra arguments are forwarded to
`devcontainer build`.

Examples:
  scripts/check-devcontainer.sh --no-cache
  scripts/check-devcontainer.sh --log-level trace
EOF
}

if ! command -v devcontainer >/dev/null 2>&1; then
  echo "Error: devcontainer CLI not found. Install @devcontainers/cli and retry." >&2
  exit 1
fi

if [[ ! -d "${TEMPLATE_ROOT}" ]]; then
  echo "Error: no devcontainers/ directory found at ${TEMPLATE_ROOT}." >&2
  exit 1
fi

mapfile -t stacks < <(find "${TEMPLATE_ROOT}" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)

if [[ "${#stacks[@]}" -eq 0 ]]; then
  echo "No Dev Container templates found under ${TEMPLATE_ROOT}." >&2
  exit 1
fi

FAILED_STACKS=()

prefer_local_build=${DEVCONTAINER_PREFER_LOCAL_BUILD:-true}

for stack in "${stacks[@]}"; do
  workspace_folder="${TEMPLATE_ROOT}/${stack}"
  echo ">> Building Dev Container for stack '${stack}' ..."

  temp_workspace=$(mktemp -d)
  trap 'rm -rf "${temp_workspace}"' EXIT
  cp "${workspace_folder}/devcontainer.json" "${temp_workspace}/devcontainer.json"

  if [[ "${prefer_local_build}" == "true" && -f "${workspace_folder}/Dockerfile" ]]; then
    if command -v jq >/dev/null 2>&1; then
      dockerfile_path="$(cd "${workspace_folder}" && pwd)/Dockerfile"
      build_context="$(cd "${workspace_folder}/.." && pwd)"
      if jq -e 'has("image") and (has("build") | not)' "${temp_workspace}/devcontainer.json" >/dev/null; then
        DOCKERFILE_PATH="${dockerfile_path}" BUILD_CONTEXT="${build_context}" \
          jq 'del(.image) + {build: {dockerfile: env.DOCKERFILE_PATH, context: env.BUILD_CONTEXT}}' \
            "${temp_workspace}/devcontainer.json" \
            > "${temp_workspace}/devcontainer.json.tmp"
        mv "${temp_workspace}/devcontainer.json.tmp" "${temp_workspace}/devcontainer.json"
      fi
    else
      echo "jq not found; cannot rewrite devcontainer.json for local build fallback." >&2
    fi
  fi

  if devcontainer build --workspace-folder "${temp_workspace}" "$@"; then
    echo ">> Stack '${stack}' built successfully."
  else
    echo "!! Stack '${stack}' build failed." >&2
    FAILED_STACKS+=("${stack}")
  fi

  rm -rf "${temp_workspace}"
  trap - EXIT
done

if [[ "${#FAILED_STACKS[@]}" -ne 0 ]]; then
  echo "Build failures detected for the following stacks: ${FAILED_STACKS[*]}" >&2
  exit 1
fi

echo "All Dev Container templates built successfully."
