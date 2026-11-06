#!/usr/bin/env bash
# Fail unless a local image still has the ID its build gave it.
#
# ci.yml's image jobs build each image once and run every check on that build,
# by tag. A step that rebuilt or retagged the tag in between (a script run in its
# build mode, say) would leave the checks after it judging another image while
# the job went green, so each check runs this first.
#
# Usage: assert-image-id.sh IMAGE EXPECTED_ID
#   IMAGE        a reference in the local Docker image store
#   EXPECTED_ID  the ID `docker image inspect` gave right after the build
#
# Exits 1 if the image is not there or has another ID. Usage errors exit 2.
set -euo pipefail

usage() {
  echo "Usage: $(basename "$0") IMAGE EXPECTED_ID" >&2
  exit 2
}

if (($# != 2)) || [[ -z "$1" || -z "$2" ]]; then
  usage
fi
IMAGE="$1"
EXPECTED_ID="$2"

if ! ACTUAL_ID="$(docker image inspect --format '{{.Id}}' -- "${IMAGE}")"; then
  echo "::error::${IMAGE} is not in the local image store" >&2
  exit 1
fi
if [[ "${ACTUAL_ID}" != "${EXPECTED_ID}" ]]; then
  echo "::error::${IMAGE} is ${ACTUAL_ID}, not the image this job built (${EXPECTED_ID})" >&2
  exit 1
fi
echo "${IMAGE} is ${ACTUAL_ID}, the image this job built"
