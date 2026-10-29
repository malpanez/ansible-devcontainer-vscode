#!/usr/bin/env bash
# Resolve one platform's manifest inside a multi-arch image index, so that
# platform can be scanned by its own digest.
#
# Given an index digest, grype scans only the runner's platform (amd64), so
# the arm64 half of every published image was attested, signed, tagged and
# released without ever being scanned. build-containers.yml (before tagging)
# and release.yml (before adding a version tag) resolve the arm64 manifest
# with this script and scan it on its own.
#
# It fails closed: an unreadable registry answer, a document that is not an
# index, more than one matching manifest or a malformed manifest digest exits
# 1 and never yields an empty ref a caller could read as "nothing to scan".
# Zero matches is an error when REQUIRED=true (the job built that platform);
# with REQUIRED=false (an amd64-only image such as latex) the ref is empty.
# Attestation manifests are listed as unknown/unknown and never match.
#
# Environment:
#   IMAGE     repository, e.g. ghcr.io/<owner>/devcontainer-base
#   DIGEST    digest of the index, sha256:<64 hex>
#   PLATFORM  <os>/<arch>, e.g. linux/arm64
#   REQUIRED  true or false
#
# Writes `ref=<IMAGE>@<manifest digest>`, or an empty `ref=`, to
# $GITHUB_OUTPUT (prints it when that is unset). Usage errors exit 2.
set -euo pipefail

SCRIPT_NAME="resolve-platform-manifest"

IMAGE="${IMAGE:-}"
DIGEST="${DIGEST:-}"
PLATFORM="${PLATFORM:-}"
REQUIRED="${REQUIRED:-}"

DIGEST_PATTERN='^sha256:[0-9a-f]{64}$'
PLATFORM_PATTERN='^[a-z0-9]+/[a-z0-9_]+$'
# `input` (with -n) fails on an empty answer instead of matching nothing, and
# the prefix keeps a match with an empty or missing digest from vanishing.
# shellcheck disable=SC2016 # $os and $arch are jq variables
MATCH_FILTER='input
  | if (.manifests | type) != "array" then error("not an image index") else . end
  | .manifests[]
  | select(.platform.os == $os and .platform.architecture == $arch)
  | "digest=\(.digest)"'

usage_error() {
  local message="$1"

  printf '::error::%s: %s\n' "${SCRIPT_NAME}" "${message}" >&2
  exit 2
}

fail() {
  local message="$1"

  printf '::error::%s: %s\n' "${SCRIPT_NAME}" "${message}" >&2
  exit 1
}

check_inputs() {
  if [[ -z "${IMAGE}" ]]; then
    usage_error "IMAGE is empty"
  fi
  if [[ ! "${DIGEST}" =~ ${DIGEST_PATTERN} ]]; then
    usage_error "DIGEST '${DIGEST}' is not sha256:<64 lowercase hex>"
  fi
  if [[ ! "${PLATFORM}" =~ ${PLATFORM_PATTERN} ]]; then
    usage_error "PLATFORM '${PLATFORM}' is not <os>/<arch>"
  fi
  case "${REQUIRED}" in
    true | false) ;;
    *) usage_error "REQUIRED must be true or false, not '${REQUIRED}'" ;;
  esac
}

write_ref() {
  local ref="$1"

  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    printf 'ref=%s\n' "${ref}" >>"${GITHUB_OUTPUT}"
  else
    printf 'ref=%s\n' "${ref}"
  fi
}

main() {
  local index
  local matches
  local digests=()

  check_inputs

  if ! index="$(docker buildx imagetools inspect --raw "${IMAGE}@${DIGEST}")"; then
    fail "could not read ${IMAGE}@${DIGEST} (error above)"
  fi
  if ! matches="$(jq -n -r --arg os "${PLATFORM%%/*}" --arg arch "${PLATFORM#*/}" \
    "${MATCH_FILTER}" <<<"${index}")"; then
    fail "${IMAGE}@${DIGEST} is not a readable image index"
  fi
  if [[ -n "${matches}" ]]; then
    mapfile -t digests <<<"${matches}"
    digests=("${digests[@]#digest=}")
  fi

  case "${#digests[@]}" in
    0)
      if [[ "${REQUIRED}" == "true" ]]; then
        fail "${IMAGE}@${DIGEST} was built for ${PLATFORM} but holds no ${PLATFORM} manifest"
      fi
      printf '::notice::%s@%s holds no %s manifest: nothing to scan for it.\n' \
        "${IMAGE}" "${DIGEST}" "${PLATFORM}"
      write_ref ""
      return 0
      ;;
    1) ;;
    *) fail "${IMAGE}@${DIGEST} holds ${#digests[@]} ${PLATFORM} manifests (${digests[*]}); expected one" ;;
  esac

  if [[ ! "${digests[0]}" =~ ${DIGEST_PATTERN} ]]; then
    fail "${IMAGE}@${DIGEST} lists a malformed ${PLATFORM} manifest digest '${digests[0]}'"
  fi

  write_ref "${IMAGE}@${digests[0]}"
  printf '%s: %s@%s\n' "${PLATFORM}" "${IMAGE}" "${digests[0]}"
}

main "$@"
