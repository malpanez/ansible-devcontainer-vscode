#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
EXAMPLES_DIR="${REPO_ROOT}/docs/scenarios/examples"

if [[ ! -d "${EXAMPLES_DIR}" ]]; then
  echo "Examples directory ${EXAMPLES_DIR} missing; skipping LaTeX scenario." >&2
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required for the LaTeX scenario." >&2
  exit 1
fi

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

echo "==> Compiling resume.tex inside LaTeX image"
docker run --rm \
  -v "${EXAMPLES_DIR}:/workspace/examples" \
  --workdir /workspace/examples \
  "${LATEX_IMAGE}" \
  bash -lc 'latexmk -pdf -interaction=nonstopmode resume.tex'

rm -f "${EXAMPLES_DIR}"/resume.{pdf,aux,log,fdb_latexmk,fls} 2>/dev/null || true

echo "LaTeX resume compiled successfully."
