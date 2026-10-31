#!/usr/bin/env bash
# Check, inside a running dev container, that it can do the work its template
# promises: write to its named volumes, run an ssh client for git remotes,
# receive the user's .gitconfig, open a terminal in bash, and run the stack's
# tool.
#
# ci.yml runs this through `devcontainer exec` after `devcontainer up`, so it
# sees the template's remoteUser and remoteEnv. The only check there used to be
# an echo, and the published images failed most of these with the job green: a
# fresh volume the user could not write to failed postCreateCommand, the retry
# reused the container and reported success, and the echo passed.
#
# Usage: check-devcontainer-workload.sh STACK [VOLUME_TARGET...]
#   STACK           ansible, golang, latex or terraform
#   VOLUME_TARGET   absolute mount point of a named volume of the template
#
# Prints one line per check on stdout and an '::error' line on stderr for each
# failure. Runs every check, then exits 1 if any failed. Usage errors exit 2.
set -euo pipefail
shopt -s inherit_errexit 2>/dev/null || true

FAILURES=0
WORK_DIR=""

cleanup() {
  if [[ -n "${WORK_DIR}" ]]; then
    rm -rf -- "${WORK_DIR}"
  fi
}
trap cleanup EXIT

pass() {
  printf 'ok      %s\n' "$*"
}

fail() {
  printf 'FAILED  %s\n' "$*"
  printf '::error::%s\n' "$*" >&2
  FAILURES=$((FAILURES + 1))
}

usage() {
  printf 'usage: %s STACK [VOLUME_TARGET...]\n' "${0##*/}" >&2
  printf 'STACK is one of: ansible golang latex terraform\n' >&2
}

run_check() {
  local description="$1"
  local output
  shift
  if output="$("$@" 2>&1)"; then
    pass "${description}"
  else
    fail "${description}: ${output}"
  fi
}

check_volume_target() {
  local target="$1"
  local probe
  if [[ "${target}" != /* ]]; then
    fail "volume target is not an absolute path: '${target}'"
    return 0
  fi
  if probe="$(mktemp "${target}/.workload-probe.XXXXXX" 2>&1)" && rm -f -- "${probe}"; then
    pass "volume target ${target} is writable"
  else
    fail "volume target ${target} is not writable by $(id -un): ${probe}: $(ls -ld -- "${target}" 2>&1)"
  fi
}

# The test the Dev Containers extension runs before it copies the user's
# .gitconfig; true means it copies nothing (extension 0.471.0):
#   [ -e ~/.gitconfig ] && grep -e '^\[' ~/.gitconfig \
#     | grep -v -E '^\[(filter|safe)([[:blank:]]+|\])'
# A template's own `git config --global --add safe.directory` leaves it false.
check_gitconfig_copied() {
  local blocking=""
  if [[ -e "${HOME}/.gitconfig" ]]; then
    blocking="$(grep -e '^\[' "${HOME}/.gitconfig" \
      | grep -v -E '^\[(filter|safe)([[:blank:]]+|\])' || true)"
  fi
  if [[ -z "${blocking}" ]]; then
    pass "${HOME}/.gitconfig does not stop the extension copying the user's"
  else
    fail "${HOME}/.gitconfig stops the extension copying the user's: ${blocking//$'\n'/ }"
  fi
}

check_login_shell() {
  local user
  local shell
  user="$(id -un)"
  shell="$(awk -F: -v user="${user}" '$1 == user { print $7 }' /etc/passwd)"
  if [[ "${shell}" == "/bin/bash" ]]; then
    pass "login shell of ${user} is /bin/bash"
  else
    fail "login shell of ${user} is '${shell}', not /bin/bash"
  fi
}

check_lang() {
  if [[ "${LANG:-}" == "C.UTF-8" ]]; then
    pass "LANG is C.UTF-8"
  else
    fail "LANG is '${LANG:-}', not C.UTF-8"
  fi
}

# stdlib only, so it needs no network; fmt makes the build write to GOCACHE,
# which is one of the template's volumes.
check_go_build() {
  local output
  WORK_DIR="$(mktemp -d)"
  cat >"${WORK_DIR}/main.go" <<'EOF'
package main

import "fmt"

func main() {
	fmt.Println("workload ok")
}
EOF
  if output="$(cd "${WORK_DIR}" && go build -o workload main.go 2>&1 && ./workload 2>&1)" \
    && [[ "${output}" == "workload ok" ]]; then
    pass "go build of a stdlib-only program"
  else
    fail "go build of a stdlib-only program: ${output}"
  fi
}

# ping needs no root and the question is whether ansible runs. This repository's
# ansible.cfg sets become = True, and the images carry no sudo, so with that
# config alone this stops at `sudo: not found`.
check_ansible_ping() {
  run_check "ansible localhost -m ansible.builtin.ping" \
    env ANSIBLE_BECOME=false ansible localhost -m ansible.builtin.ping
}

check_stack() {
  case "$1" in
    ansible) check_ansible_ping ;;
    golang) check_go_build ;;
    latex) run_check "tectonic --version" tectonic --version ;;
    terraform) run_check "terraform version" terraform version ;;
    *) return 1 ;;
  esac
}

main() {
  local stack="${1:-}"
  case "${stack}" in
    ansible | golang | latex | terraform) shift ;;
    *)
      usage
      exit 2
      ;;
  esac

  local target
  for target in "$@"; do
    check_volume_target "${target}"
  done
  run_check "ssh -V" ssh -V
  check_gitconfig_copied
  check_login_shell
  check_lang
  check_stack "${stack}"

  if [[ "${FAILURES}" -gt 0 ]]; then
    printf '%s: %s check(s) failed\n' "${stack}" "${FAILURES}"
    exit 1
  fi
  printf '%s: all checks passed\n' "${stack}"
}

main "$@"
