#!/usr/bin/env bash
# Install pinned Ansible collections from Galaxy, checksum-verified.
#
#   install-collections.sh <site-packages> <list> [<list>...]
#
# Each list line is "<namespace.name> <version> <sha256>" (see
# collections.txt). Every artifact is downloaded and checked against its
# pinned sha256 before anything is installed, then all of them go in with
# one offline ansible-galaxy run, so a dependency missing from the lists
# fails the build instead of being fetched unpinned. They land in
# <site-packages>/ansible_collections, where the ansible package used to put
# its bundle: ansible-core finds them there whatever collections_path a
# project's ansible.cfg sets, and anything the user installs into
# ~/.ansible/collections takes precedence.
set -euo pipefail

GALAXY_ARTIFACTS="https://galaxy.ansible.com/api/v3/plugin/ansible/content/published/collections/artifacts"

usage() {
  printf 'usage: %s <site-packages> <list> [<list>...]\n' "${0##*/}" >&2
  exit 2
}

# --retry-all-errors: Galaxy resets connections mid-handshake now and then
# (curl exit 35), which plain --retry does not count as transient; it killed
# a build on 2026-10-29. The sha256 check below still guards the result.
download_verified() {
  local NAME="$1" VERSION="$2" SHA256="$3" DEST_DIR="$4"
  local ARTIFACT="${NAME/./-}-${VERSION}.tar.gz"
  curl --proto '=https' --tlsv1.2 -fsSL --retry 5 --retry-delay 2 --retry-max-time 120 --retry-all-errors \
    "${GALAXY_ARTIFACTS}/${ARTIFACT}" -o "${DEST_DIR}/${ARTIFACT}"
  echo "${SHA256}  ${DEST_DIR}/${ARTIFACT}" | sha256sum --check --strict -
}

read_list() {
  local LIST="$1" DEST_DIR="$2"
  local NAME VERSION SHA256 EXTRA
  while read -r NAME VERSION SHA256 EXTRA || [ -n "${NAME}" ]; do
    case "${NAME}" in
      '' | '#'*) continue ;;
    esac
    if [[ ! "${NAME}" =~ ^[a-z0-9_]+\.[a-z0-9_]+$ ]] \
      || [[ ! "${VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+([-+][0-9A-Za-z.-]+)?$ ]] \
      || [[ ! "${SHA256}" =~ ^[a-f0-9]{64}$ ]] \
      || [ -n "${EXTRA}" ]; then
      printf '%s: malformed line: %s %s %s %s\n' "${LIST}" "${NAME}" "${VERSION}" "${SHA256}" "${EXTRA}" >&2
      exit 1
    fi
    download_verified "${NAME}" "${VERSION}" "${SHA256}" "${DEST_DIR}"
  done < "${LIST}"
}

main() {
  [ "$#" -ge 2 ] || usage
  local SITE="$1"
  shift
  [ -d "${SITE}" ] || { printf '%s is not a directory\n' "${SITE}" >&2; exit 1; }

  WORK="$(mktemp -d)"
  trap 'rm -rf "${WORK}"' EXIT

  local LIST
  for LIST in "$@"; do
    read_list "${LIST}" "${WORK}"
  done

  local ARTIFACTS=("${WORK}"/*.tar.gz)
  [ -e "${ARTIFACTS[0]}" ] || { echo "no collections listed in: $*" >&2; exit 1; }

  ANSIBLE_COLLECTIONS_PATH="${SITE}" ansible-galaxy collection install \
    --offline --collections-path "${SITE}" "${ARTIFACTS[@]}"
}

main "$@"
