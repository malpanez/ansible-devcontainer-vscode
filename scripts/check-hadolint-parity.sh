#!/usr/bin/env bash
# Fail when the places that pin hadolint disagree on its version.
#
# hadolint is invoked by version from four files:
#   .github/workflows/ci.yml       HADOLINT_VERSION      Dockerfile Lint, the merge gate
#   .github/workflows/release.yml  HADOLINT_VERSION      release preflight lint
#   Makefile                       hadolint/hadolint:<tag>  validate-docker
#   .pre-commit-config.yaml        rev: of AleksaC/hadolint-py
# Renovate tracks only the two workflows (the '# renovate:' annotation above
# HADOLINT_VERSION); the Makefile and the pre-commit rev are bumped by hand.
#
# They drifted once without anything noticing: the gate, the release lint and
# the Makefile sat at v2.14.0 while pre-commit and the code-scanning action
# ran 2.15.1. 2.15.1 knows DL3064 and 2.14.0 does not, so the same Dockerfile
# produced a finding locally and none at the gate. This script turns the next
# drift into a red check instead.
#
# Not covered: quality.yml runs hadolint through hadolint/hadolint-action,
# which bundles its own hadolint (v3.5.0 ships 2.15.1). That version is not
# written anywhere in this repository, and the job is report-only.
#
# The gate (ci.yml) is the reference: every other file is compared with it.
# hadolint-py revs may carry a fourth component (v2.12.0.3) and Docker tags a
# variant suffix (v2.15.1-alpine); only <major>.<minor>.<patch> is compared.
# A file that is missing, carries no pin, carries an unparseable one or
# carries two different ones fails the check: an unreadable pin is not parity.
#
# Prints one "<file> <version>" line per file on stdout, '::error' lines on
# stderr, and exits 1 on any problem. HADOLINT_CI_WORKFLOW,
# HADOLINT_RELEASE_WORKFLOW, HADOLINT_MAKEFILE and HADOLINT_PRE_COMMIT_CONFIG
# point the script at other files (the tests use them).
set -euo pipefail

SCRIPT_NAME="check-hadolint-parity"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

HADOLINT_CI_WORKFLOW="${HADOLINT_CI_WORKFLOW:-${REPO_ROOT}/.github/workflows/ci.yml}"
HADOLINT_RELEASE_WORKFLOW="${HADOLINT_RELEASE_WORKFLOW:-${REPO_ROOT}/.github/workflows/release.yml}"
HADOLINT_MAKEFILE="${HADOLINT_MAKEFILE:-${REPO_ROOT}/Makefile}"
HADOLINT_PRE_COMMIT_CONFIG="${HADOLINT_PRE_COMMIT_CONFIG:-${REPO_ROOT}/.pre-commit-config.yaml}"

LABELS=()
VERSIONS=()
FAILED=0

report_error() {
  local label="$1"
  local message="$2"

  printf '::error file=%s::%s: %s\n' "${label}" "${SCRIPT_NAME}" "${message}" >&2
  FAILED=1
}

image_tags() {
  local file="$1"

  sed -n \
    -e '/^[[:space:]]*#/d' \
    -e 's/.*hadolint\/hadolint:\(v\{0,1\}[0-9][0-9A-Za-z._-]*\).*/\1/p' \
    "${file}"
}

workflow_pins() {
  local file="$1"

  sed -n \
    -e 's/^[[:space:]]*HADOLINT_VERSION:[[:space:]]*\([^[:space:]]\{1,\}\).*/\1/p' \
    "${file}"
  image_tags "${file}"
}

makefile_pins() {
  local file="$1"

  image_tags "${file}"
}

pre_commit_pins() {
  local file="$1"

  awk '
    /^[[:space:]]*-[[:space:]]*repo:/ {
      in_hadolint = ($0 ~ /\/hadolint-py[^A-Za-z0-9_-]*$/)
      next
    }
    in_hadolint && /^[[:space:]]*rev:/ { print $2 }
  ' "${file}"
}

normalise_version() {
  local raw="$1"

  if [[ "${raw}" =~ ^v?([0-9]+\.[0-9]+\.[0-9]+)([.-][0-9A-Za-z.-]*)?$ ]]; then
    printf '%s\n' "${BASH_REMATCH[1]}"
    return 0
  fi
  return 1
}

record_pin() {
  local label="$1"
  local version="$2"

  LABELS+=("${label}")
  VERSIONS+=("${version}")
  printf '%-32s %s\n' "${label}" "${version:-<not found>}"
}

resolve_pin() {
  local file="$1"
  local extractor="$2"
  local expected="$3"
  local label="${file#"${REPO_ROOT}/"}"
  local found
  local raw
  local version
  local resolved=""

  if [[ ! -f "${file}" ]]; then
    report_error "${label}" "no such file"
    record_pin "${label}" ""
    return 0
  fi

  if ! found="$("${extractor}" "${file}")"; then
    report_error "${label}" "could not be read"
    record_pin "${label}" ""
    return 0
  fi

  while IFS= read -r raw; do
    raw="${raw//[\"\']/}"
    if [[ -z "${raw}" ]]; then
      continue
    fi
    if ! version="$(normalise_version "${raw}")"; then
      report_error "${label}" "cannot read a hadolint version from \"${raw}\""
      record_pin "${label}" ""
      return 0
    fi
    if [[ -n "${resolved}" && "${resolved}" != "${version}" ]]; then
      report_error "${label}" "pins hadolint twice, at ${resolved} and at ${version}"
      record_pin "${label}" ""
      return 0
    fi
    resolved="${version}"
  done <<<"${found}"

  if [[ -z "${resolved}" ]]; then
    report_error "${label}" "no hadolint pin found (expected ${expected})"
  fi
  record_pin "${label}" "${resolved}"
}

compare_pins() {
  local reference_label="${LABELS[0]}"
  local reference="${VERSIONS[0]}"
  local index

  if [[ -z "${reference}" ]]; then
    return 0
  fi

  for index in "${!LABELS[@]}"; do
    if [[ -n "${VERSIONS[index]}" && "${VERSIONS[index]}" != "${reference}" ]]; then
      report_error "${LABELS[index]}" \
        "pins hadolint ${VERSIONS[index]}, but the merge gate (${reference_label}) runs ${reference}. Bump every call site together."
    fi
  done
}

main() {
  resolve_pin "${HADOLINT_CI_WORKFLOW}" workflow_pins \
    'HADOLINT_VERSION: "v<major>.<minor>.<patch>"'
  resolve_pin "${HADOLINT_RELEASE_WORKFLOW}" workflow_pins \
    'HADOLINT_VERSION: "v<major>.<minor>.<patch>"'
  resolve_pin "${HADOLINT_MAKEFILE}" makefile_pins \
    'hadolint/hadolint:v<major>.<minor>.<patch>'
  resolve_pin "${HADOLINT_PRE_COMMIT_CONFIG}" pre_commit_pins \
    'a rev: under the AleksaC/hadolint-py repo'

  compare_pins

  if [[ "${FAILED}" -ne 0 ]]; then
    exit 1
  fi
  printf '%s: all %s call sites pin hadolint %s\n' \
    "${SCRIPT_NAME}" "${#LABELS[@]}" "${VERSIONS[0]}"
}

main "$@"
