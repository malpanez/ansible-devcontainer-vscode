#!/usr/bin/env bash
# Compile docs/scenarios/examples/resume.tex with tectonic in the latex image.
#
# Usage: run-latex-cv.sh [--image IMAGE]
#   (no option)    build base and latex from this checkout, smoke-test both,
#                  compile, and remove both images afterwards
#   --image IMAGE  use IMAGE, a latex image already in the local Docker image
#                  store, as it is: nothing is built, pulled or removed. ci.yml
#                  passes the image its latex job built.
#
# Run from the repository root. Exits 1 if a build, a smoke test or the compile
# fails. Usage errors, an IMAGE that is not in the local image store among
# them, exit 2.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
EXAMPLES_DIR="${REPO_ROOT}/docs/scenarios/examples"
EXISTING_IMAGE=""

usage() {
  echo "Usage: $(basename "$0") [--image IMAGE]" >&2
  exit 2
}

while (($#)); do
  case "$1" in
    --image)
      if (($# < 2)) || [[ -z "$2" ]]; then
        usage
      fi
      EXISTING_IMAGE="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      ;;
  esac
done

if [[ ! -d "${EXAMPLES_DIR}" ]]; then
  echo "Examples directory ${EXAMPLES_DIR} missing; skipping LaTeX scenario." >&2
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required for the LaTeX scenario." >&2
  exit 1
fi

if [[ -n "${EXISTING_IMAGE}" ]]; then
  # Never pulled: a name that is not here would otherwise come from a registry,
  # and the scenario would pass or fail on an image nobody built.
  if ! docker image inspect -- "${EXISTING_IMAGE}" >/dev/null 2>&1; then
    echo "${EXISTING_IMAGE} is not in the local image store." >&2
    exit 2
  fi
  LATEX_IMAGE="${EXISTING_IMAGE}"
  ./scripts/smoke-devcontainer-image.sh --stack latex --image "${LATEX_IMAGE}"
else
  BASE_IMAGE="scenario-base:${RANDOM}"
  LATEX_IMAGE="scenario-latex:${RANDOM}"

  cleanup() {
    docker image rm --force "${LATEX_IMAGE}" >/dev/null 2>&1 || true
    docker image rm --force "${BASE_IMAGE}" >/dev/null 2>&1 || true
    return 0
  }
  trap cleanup EXIT

  ./scripts/smoke-devcontainer-image.sh --stack base --build --image "${BASE_IMAGE}"
  ./scripts/smoke-devcontainer-image.sh --stack latex --build --image "${LATEX_IMAGE}" --base-image "${BASE_IMAGE}"
fi

echo "==> Compiling resume.tex inside LaTeX image"
# Read-only mount + container-local build dir: the runner checkout is
# owned by a different UID than the container user, so writing the PDF
# into the bind mount fails on CI.
docker run --rm \
  -v "${EXAMPLES_DIR}:/workspace/examples:ro" \
  --workdir /tmp \
  "${LATEX_IMAGE}" \
  bash -lc 'cp /workspace/examples/resume.tex . && tectonic resume.tex && test -s resume.pdf'

echo "LaTeX resume compiled successfully."
