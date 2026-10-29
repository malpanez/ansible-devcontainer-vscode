#!/usr/bin/env bash
# Derive SOURCE_DATE_EPOCH for an image build from the commit being built.
#
# BuildKit writes the SOURCE_DATE_EPOCH build-arg as the `created` time of
# the image config and of every history entry, and the exporter's
# rewrite-timestamp=true clamps every later file mtime in the layers the
# build adds to it. The commit time, not the clock: two builds of one commit
# against unchanged package mirrors then produce the same per-platform
# manifest digest (docs/IMAGE_PUBLISHING.md, "Reproducible builds"). The
# org.opencontainers.image.created label takes the same instant, or
# metadata-action would stamp the clock into the config again.
#
# It is passed as a build-arg only, never declared with ARG in a Dockerfile.
# Undeclared, it never reaches a RUN and changes no cache key; declared, its
# new value on every commit would rebuild every layer below it, in the CI
# cache and the publish cache alike.
#
# Reads the committer time of HEAD in the current directory's repository
# and prints two key=value lines, in the form $GITHUB_OUTPUT expects:
#   epoch=<seconds since 1970-01-01, UTC>
#   created=<YYYY-MM-DDTHH:MM:SSZ>   the same instant, in UTC
# Nothing is printed unless both values resolve.
set -euo pipefail

SCRIPT_NAME="derive-source-date-epoch"

fail() {
  printf '%s: %s\n' "${SCRIPT_NAME}" "$1" >&2
  exit 1
}

main() {
  local epoch
  local created

  if ! epoch="$(git log -1 --format=%ct 2>/dev/null)"; then
    fail "git log found no commit in $(pwd) (not a repository, or no commits yet)"
  fi
  if [[ ! "${epoch}" =~ ^[0-9]+$ ]]; then
    fail "git log returned no numeric commit time: '${epoch}'"
  fi
  if ! created="$(date -u -d "@${epoch}" +%Y-%m-%dT%H:%M:%SZ)"; then
    fail "date could not format epoch ${epoch}"
  fi

  printf 'epoch=%s\ncreated=%s\n' "${epoch}" "${created}"
  return 0
}

main "$@"
