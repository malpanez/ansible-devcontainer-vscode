#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_DIR="${REPO_ROOT}/.devcontainer"
TEMPLATES_DIR="${REPO_ROOT}/devcontainers"

strict=false

usage() {
  cat <<'EOF'
Usage: scripts/doctor-devcontainer.sh [options]

Options:
  --target <path>      Path to the active .devcontainer directory.
  --templates <path>   Path to the devcontainers template root.
  --strict             Treat missing local tooling as an error.
  -h, --help           Show this help.

Checks:
  - active .devcontainer exists
  - devcontainer.json is present
  - template metadata matches the selected stack
  - .devcontainer contents are in sync with the template
  - local container/devcontainer CLIs are available
EOF
  return 0
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --target)
        TARGET_DIR="$2"
        shift 2
        ;;
      --templates)
        TEMPLATES_DIR="$2"
        shift 2
        ;;
      --strict)
        strict=true
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "Unknown option: $1" >&2
        usage
        exit 1
        ;;
    esac
  done
}

status_ok() {
  echo "[ok] $1"
}

status_warn() {
  echo "[warn] $1"
}

status_fail() {
  echo "[fail] $1" >&2
}

check_binary() {
  local binary="$1"
  local required="$2"

  if command -v "${binary}" >/dev/null 2>&1; then
    status_ok "${binary} available"
    return 0
  fi

  if [[ "${required}" == "true" ]]; then
    status_fail "${binary} not found"
    if [[ "${binary}" == "devcontainer" ]]; then
      echo "       install it with: npm install --global @devcontainers/cli" >&2
    fi
    return 1
  fi

  status_warn "${binary} not found"
  if [[ "${binary}" == "devcontainer" ]]; then
    echo "       install it with: npm install --global @devcontainers/cli"
  fi
  return 0
}

check_container_runtime() {
  local required="$1"

  if command -v docker >/dev/null 2>&1; then
    status_ok "docker available"
    return 0
  fi

  if command -v podman >/dev/null 2>&1; then
    status_ok "podman available"
    return 0
  fi

  if [[ "${required}" == "true" ]]; then
    status_fail "neither docker nor podman is available"
    return 1
  fi

  status_warn "neither docker nor podman is available"
  return 0
}

main() {
  local failure=0
  parse_args "$@"

  TARGET_DIR="$(realpath "${TARGET_DIR}")"
  TEMPLATES_DIR="$(realpath "${TEMPLATES_DIR}")"

  echo "Devcontainer doctor"
  echo "  target: ${TARGET_DIR}"
  echo "  templates: ${TEMPLATES_DIR}"

  if [[ ! -d "${TARGET_DIR}" ]]; then
    status_fail "target directory not found"
    return 1
  fi
  status_ok "target directory exists"

  if [[ ! -f "${TARGET_DIR}/devcontainer.json" ]]; then
    status_fail "devcontainer.json missing from target"
    return 1
  fi
  status_ok "devcontainer.json present"

  for script in "devcontainer-metadata.py" "devcontainer-diff.py"; do
    if [[ ! -f "${SCRIPT_DIR}/${script}" ]]; then
      status_fail "${script} not found at ${SCRIPT_DIR}/${script}"
      return 1
    fi
  done

  if ! python3 "${SCRIPT_DIR}/devcontainer-metadata.py" --target "${TARGET_DIR}" --templates "${TEMPLATES_DIR}"; then
    status_fail "template metadata check failed"
    failure=1
  else
    status_ok "template metadata matches"
  fi

  if ! python3 "${SCRIPT_DIR}/devcontainer-diff.py" --target "${TARGET_DIR}" --templates "${TEMPLATES_DIR}"; then
    status_fail "target differs from template"
    failure=1
  else
    status_ok "target matches template"
  fi

  if ! check_container_runtime "${strict}"; then
    failure=1
  fi

  if ! check_binary devcontainer "${strict}"; then
    failure=1
  fi

  if [[ "${failure}" -ne 0 ]]; then
    status_fail "doctor found actionable issues"
    return 1
  fi

  status_ok "devcontainer state is healthy"
  return 0
}

main "$@"
