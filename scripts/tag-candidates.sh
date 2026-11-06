#!/usr/bin/env bash
# Tag every digest a candidate run tested candidate-<first 12 of the tree>.
#
# ci.yml's candidate mode pushes each image untagged, by digest, and tests that
# digest on every platform. Only once every leg passed does this give it a tag:
# the name of the tree it was built from, which 2d's publish looks up, and
# which keeps cleanup-ghcr.yml (untagged only) from deleting it.
#
# The planned-digest check is build-containers.yml's "Tag the gated digest":
# one source and no --annotation, so buildx pushes the tested index bytes
# unchanged under the tag; anything else would write a new index that nothing
# tested. The dry run (it prints the index plus a newline) proves that for
# every image before the first tag is written, and the read-back after proves
# each tag serves the digest the legs judged. A re-run of the same tree writes
# the same tag again, on that run's digest.
#
# Usage: tag-candidates.sh RECORD
#   RECORD                   tested-digests.json (scripts/tested-digests.py write)
#   GITHUB_REPOSITORY_OWNER  the GHCR namespace
# Exits 1 when a tag would not be the tested digest or does not resolve to it.
# Usage errors, a record without a tree among them, exit 2.
set -euo pipefail
# A docker error inside $(...) must stop the script, not hash an empty answer.
shopt -s inherit_errexit

usage() {
  echo "Usage: GITHUB_REPOSITORY_OWNER=owner $(basename "$0") RECORD" >&2
  exit 2
}

planned_digest() {
  local IMAGE="$1" DIGEST="$2" TAG="$3" SUM
  SUM="$(docker buildx imagetools create --dry-run --tag "${IMAGE}:${TAG}" "${IMAGE}@${DIGEST}" \
    | head -c -1 | sha256sum)"
  echo "sha256:${SUM%% *}"
}

resolved_digest() {
  local IMAGE="$1" TAG="$2" SUM
  SUM="$(docker buildx imagetools inspect --raw "${IMAGE}:${TAG}" | sha256sum)"
  echo "sha256:${SUM%% *}"
}

main() {
  local RECORD="$1" TREE TAG ROWS_TSV NAME DIGEST IMAGE PLANNED RESOLVED ROW
  local -a ROWS=()

  TREE="$(jq -r '.tree // ""' "${RECORD}")"
  if [[ ! "${TREE}" =~ ^[0-9a-f]{40}$ ]]; then
    echo "tag-candidates: ${RECORD} names no tree ('${TREE}')" >&2
    usage
  fi
  TAG="candidate-${TREE:0:12}"
  ROWS_TSV="$(jq -r '.images | to_entries[] | [.key, .value] | @tsv' "${RECORD}")"
  if [[ -z "${ROWS_TSV}" ]]; then
    echo "No image was built in this run, so none is tagged ${TAG}."
    return 0
  fi
  mapfile -t ROWS <<<"${ROWS_TSV}"

  for ROW in "${ROWS[@]}"; do
    IFS=$'\t' read -r NAME DIGEST <<<"${ROW}"
    IMAGE="ghcr.io/${GITHUB_REPOSITORY_OWNER}/devcontainer-${NAME}"
    PLANNED="$(planned_digest "${IMAGE}" "${DIGEST}" "${TAG}")"
    if [[ "${PLANNED}" != "${DIGEST}" ]]; then
      echo "::error::imagetools would tag a new index ${PLANNED} as ${IMAGE}:${TAG}, not the tested" \
        "${DIGEST}; no tag was written."
      exit 1
    fi
  done
  for ROW in "${ROWS[@]}"; do
    IFS=$'\t' read -r NAME DIGEST <<<"${ROW}"
    IMAGE="ghcr.io/${GITHUB_REPOSITORY_OWNER}/devcontainer-${NAME}"
    docker buildx imagetools create --tag "${IMAGE}:${TAG}" "${IMAGE}@${DIGEST}"
  done
  for ROW in "${ROWS[@]}"; do
    IFS=$'\t' read -r NAME DIGEST <<<"${ROW}"
    IMAGE="ghcr.io/${GITHUB_REPOSITORY_OWNER}/devcontainer-${NAME}"
    RESOLVED="$(resolved_digest "${IMAGE}" "${TAG}")"
    if [[ "${RESOLVED}" != "${DIGEST}" ]]; then
      echo "::error::${IMAGE}:${TAG} resolves to ${RESOLVED}, not the tested ${DIGEST}."
      exit 1
    fi
    echo "${IMAGE}:${TAG} -> ${DIGEST}"
  done
}

if (($# != 1)) || [[ ! -f "${1:-}" || -z "${GITHUB_REPOSITORY_OWNER:-}" ]]; then
  usage
fi
main "$1"
