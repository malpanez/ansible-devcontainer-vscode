#!/usr/bin/env bash
set -euo pipefail

# Simple smoke test harness for devcontainer images.
# Builds (optionally) and runs minimal verification commands per stack.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STACK=""
IMAGE_TAG=""
BUILD_IMAGE=false
BASE_IMAGE_ARG=""
BASE_IMAGE_DEFAULT="devcontainer-base:ci"

usage() {
  cat <<'EOF'
Usage: scripts/smoke-devcontainer-image.sh --stack <name> [options]

Options:
  --stack <name>           Required. One of: base, ansible, terraform, golang, latex.
  --image <tag>            Tag/name to assign to the locally built image (default: devcontainer-<stack>:ci).
  --build                  Build the image before running the smoke test (default: reuse existing tag).
  --base-image <ref>       Base image reference passed via BASE_IMAGE build arg for Python stacks
                           (default: python:3.12-slim-bookworm).
  -h, --help               Show this message.

Examples:
  scripts/smoke-devcontainer-image.sh --stack ansible --build
  scripts/smoke-devcontainer-image.sh --stack terraform --image test/terraform:latest --build
EOF
  return 0
}

parse_args() {
  local arg
  local value
  while [[ $# -gt 0 ]]; do
    arg="$1"
    value="${2:-}"
    case "${arg}" in
      --stack)
        STACK="${value}"
        shift 2
        ;;
      --image)
        IMAGE_TAG="${value}"
        shift 2
        ;;
      --build)
        BUILD_IMAGE=true
        shift
        ;;
      --base-image)
        BASE_IMAGE_ARG="${value}"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "Unknown option: ${arg}" >&2
        usage
        exit 1
        ;;
    esac
  done
  return 0
}

ensure_args() {
  if [[ -z "${STACK}" ]]; then
    echo "Error: --stack is required." >&2
    usage
    exit 1
  fi

  if [[ -z "${IMAGE_TAG}" ]]; then
    IMAGE_TAG="devcontainer-${STACK}:ci"
  fi

  if [[ -z "${BASE_IMAGE_ARG}" ]]; then
    BASE_IMAGE_ARG="${BASE_IMAGE_DEFAULT}"
  fi
  return 0
}

ensure_base_image() {
  if [[ "${STACK}" != "ansible" && "${STACK}" != "terraform" ]]; then
    return 0
  fi

  if [[ "${BASE_IMAGE_ARG}" != "${BASE_IMAGE_DEFAULT}" ]]; then
    return 0
  fi

  if docker image inspect "${BASE_IMAGE_ARG}" >/dev/null 2>&1; then
    return 0
  fi

  echo ">> Building shared base image (${BASE_IMAGE_ARG}) ..."
  docker build --progress plain -t "${BASE_IMAGE_ARG}" -f "${REPO_ROOT}/devcontainers/base/Dockerfile" "${REPO_ROOT}"
  return 0
}

build_image() {
  local dockerfile=""
  local context="."
  local extra_args=()

  case "${STACK}" in
    base)
      dockerfile="${REPO_ROOT}/devcontainers/base/Dockerfile"
      ;;
    ansible)
      dockerfile="${REPO_ROOT}/devcontainers/ansible/Dockerfile"
      extra_args+=("--build-arg" "BASE_IMAGE=${BASE_IMAGE_ARG}")
      ;;
    terraform)
      dockerfile="${REPO_ROOT}/devcontainers/terraform/Dockerfile"
      extra_args+=("--build-arg" "BASE_IMAGE=${BASE_IMAGE_ARG}")
      ;;
    golang)
      dockerfile="${REPO_ROOT}/devcontainers/golang/Dockerfile"
      ;;
    latex)
      dockerfile="${REPO_ROOT}/devcontainers/latex/Dockerfile"
      ;;
    *)
      echo "Unsupported stack '${STACK}'." >&2
      exit 1
      ;;
  esac

  echo ">> Building ${STACK} image (${IMAGE_TAG}) ..."
  docker build --progress plain -t "${IMAGE_TAG}" -f "${dockerfile}" "${extra_args[@]}" "${context}"
  return 0
}

run_smoke() {
  echo ">> Running smoke checks for stack '${STACK}' ..."
  case "${STACK}" in
    base)
      docker run --rm "${IMAGE_TAG}" bash -lc "whoami | grep -q vscode && uv --version"
      ;;
    ansible)
      docker run --rm \
        --mount type=bind,src="${REPO_ROOT}/requirements-ansible.txt",target=/tmp/requirements-ansible.txt,readonly \
        "${IMAGE_TAG}" \
        bash -lc "sudo uv pip install --system --requirement /tmp/requirements-ansible.txt && ansible --version && ansible-lint --version && uv --version"
      ;;
    terraform)
      docker run --rm "${IMAGE_TAG}" \
        bash -lc "sudo --preserve-env=CHECKOV_CONSTRAINT uv pip install --system \"\${CHECKOV_CONSTRAINT}\" && terraform version && terragrunt --version && tflint --version && checkov --version"
      ;;
    golang)
      docker run --rm "${IMAGE_TAG}" bash -lc "go version && goimports -h >/dev/null && golangci-lint --version"
      ;;
    latex)
      docker run --rm "${IMAGE_TAG}" bash -lc "kpsewhich latex.fmt >/dev/null && latexmk -v"
      ;;
    *)
      echo "No smoke test defined for '${STACK}'." >&2
      exit 1
      ;;
  esac
  return 0
}

main() {
  parse_args "$@"
  ensure_args

  if [[ "${BUILD_IMAGE}" == true ]]; then
    ensure_base_image
    build_image
  fi

  run_smoke
  echo ">> Smoke test for '${STACK}' completed successfully."
  return 0
}

main "$@"
