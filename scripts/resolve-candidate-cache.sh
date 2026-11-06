#!/usr/bin/env bash
# The registry cache of an image's candidate build in ci.yml.
#
# Reads :buildcache, which candidate mode alone writes, and
# :buildcache-publish, which build-containers.yml alone writes, and writes
# :buildcache only. A cache export replaces the manifest at its tag, so each
# tag keeps one writer: this script must never name :buildcache-publish in
# `to`.
#
# :buildcache-publish comes first: build-containers.yml refreshes it every
# night from an uncached build, while :buildcache holds what earlier
# candidates reused, so where order matters the fresher layers win.
#
# Each ref is probed first: buildx aborts the whole build on a missing
# cache-from ref ('failed to configure registry cache importer: <ref>: not
# found'), and a new image has neither tag until a build writes the first.
# ignore-error, as build-containers.yml exports: a cache export problem must
# not fail the build.
#
# Usage: resolve-candidate-cache.sh IMAGE
#   IMAGE                    the image's name, devcontainer-<IMAGE> on GHCR
#   GITHUB_REPOSITORY_OWNER  the GHCR namespace
# Prints `from` (one ref a line, possibly none) and `to`, in the form
# $GITHUB_OUTPUT expects. Usage errors exit 2.
set -euo pipefail

usage() {
  echo "Usage: GITHUB_REPOSITORY_OWNER=owner $(basename "$0") IMAGE" >&2
  exit 2
}

main() {
  local REPOSITORY="ghcr.io/${GITHUB_REPOSITORY_OWNER}/devcontainer-$1"
  local DELIMITER CACHE_REF
  DELIMITER="cache_from_$(od -An -N8 -tx1 /dev/urandom | tr -d ' \n')"

  echo "from<<${DELIMITER}"
  for CACHE_REF in "${REPOSITORY}:buildcache-publish" "${REPOSITORY}:buildcache"; do
    if docker buildx imagetools inspect "${CACHE_REF}" >/dev/null 2>&1; then
      echo "type=registry,ref=${CACHE_REF}"
    else
      echo "::notice::No cache at ${CACHE_REF}; not reading it." >&2
    fi
  done
  echo "${DELIMITER}"
  echo "to=type=registry,ref=${REPOSITORY}:buildcache,mode=max,ignore-error=true"
}

if (($# != 1)) || [[ -z "$1" || -z "${GITHUB_REPOSITORY_OWNER:-}" ]]; then
  usage
fi
main "$1"
