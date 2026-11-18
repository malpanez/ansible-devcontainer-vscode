#!/usr/bin/env bash
# /usr/local/bin/<tool>-2.16 links here: run that tool from the ansible-core
# 2.16 venv. ANSIBLE_HOME moves the user collections path off
# ~/.ansible/collections, where ansible-galaxy (2.21) installs collections
# 2.16 cannot load (community.general 12+), and which ansible-core searches
# before the venv's own pinned collections. Inside ~/.ansible, so the
# template's ansible-galaxy-cache volume keeps it. An ANSIBLE_HOME already
# set wins.
set -euo pipefail

LEGACY_VENV=/opt/ansible-core-2.16/venv

main() {
  local TOOL="${0##*/}"
  TOOL="${TOOL%-2.16}"
  export ANSIBLE_HOME="${ANSIBLE_HOME:-${HOME}/.ansible/core-2.16}"
  exec "${LEGACY_VENV}/bin/${TOOL}" "$@"
}

main "$@"
