#!/usr/bin/env bash
# Count the fixable high/critical Grype findings of every platform an image
# was published for: the scan gate's verdict in build-containers.yml.
#
# The images are multi-arch (linux/amd64 + linux/arm64). The gate used to scan
# the index digest, which grype resolves to the runner's platform, so the arm64
# half was attested, signed and tagged without ever being scanned. Each
# platform now gets its own scan, and this script is the one place that turns
# those SARIFs into a verdict for all three build jobs (build-single,
# build-base, build-all) instead of three inline copies that drift apart.
#
# The platform list decides what must be judged, not the SARIFs that happen to
# exist: a platform that was built but whose SARIF path is empty, whose file
# is missing or whose contents jq cannot read leaves the image unjudged. An
# unjudged image gets an empty `count=`, which every caller treats as "do not
# tag". Only results at `.level == "error"` are counted (severity-cutoff: high
# makes that high/critical), so the count does not rely on the SARIF filter
# step having run first.
#
# Environment:
#   IMAGE        image name, for messages
#   PLATFORMS    comma-separated, as passed to buildx
#   SARIF_AMD64  SARIF from the linux/amd64 scan
#   SARIF_ARM64  SARIF from the linux/arm64 scan
#
# Writes `count=<total>` to $GITHUB_OUTPUT (prints it when that is unset) and,
# for a non-zero total, the rules behind it to $GITHUB_STEP_SUMMARY. Exits 0
# whether or not the image was judged: the callers decide what to fail. An
# empty PLATFORMS or a platform with no SARIF input above is a usage error and
# exits 2, so a platform added to a build cannot be published unscanned.
set -euo pipefail

SCRIPT_NAME="count-fixable-findings"

IMAGE="${IMAGE:-}"
PLATFORMS="${PLATFORMS:-}"
SARIF_AMD64="${SARIF_AMD64:-}"
SARIF_ARM64="${SARIF_ARM64:-}"

COUNT_FILTER='if (.runs | type) != "array" or (.runs | length) == 0
  then error("no runs")
  else [.runs[].results[] | select(.level == "error")] | length
  end'
RULES_FILTER='[.runs[].results[] | select(.level == "error") | .ruleId] | unique | .[]'

EXPECTED=()
JUDGED=()
COUNTS=()
UNJUDGED=()
TOTAL=0

usage_error() {
  local message="$1"

  printf '::error::%s: %s\n' "${SCRIPT_NAME}" "${message}" >&2
  exit 2
}

sarif_for() {
  local platform="$1"

  case "${platform}" in
    linux/amd64) printf '%s' "${SARIF_AMD64}" ;;
    linux/arm64) printf '%s' "${SARIF_ARM64}" ;;
  esac
}

check_inputs() {
  if [[ -z "${IMAGE}" ]]; then
    usage_error "IMAGE is empty"
  fi
  if [[ -z "${PLATFORMS//[[:space:],]/}" ]]; then
    usage_error "PLATFORMS is empty: there is no platform to judge"
  fi
}

parse_platforms() {
  local raw
  local platform
  local seen
  local entries=()

  IFS=',' read -r -a entries <<<"${PLATFORMS}"
  for raw in "${entries[@]}"; do
    platform="${raw//[[:space:]]/}"
    if [[ -z "${platform}" ]]; then
      continue
    fi
    case "${platform}" in
      linux/amd64 | linux/arm64) ;;
      *) usage_error "unsupported platform '${platform}' in PLATFORMS='${PLATFORMS}': no SARIF input for it" ;;
    esac
    for seen in "${EXPECTED[@]}"; do
      if [[ "${seen}" == "${platform}" ]]; then
        continue 2
      fi
    done
    EXPECTED+=("${platform}")
  done
}

judge_platform() {
  local platform="$1"
  local sarif
  local count
  local reason=""

  sarif="$(sarif_for "${platform}")"
  if [[ -z "${sarif}" ]]; then
    reason="no SARIF path (the scan did not run or produced no output)"
  elif [[ ! -f "${sarif}" ]]; then
    reason="SARIF ${sarif} does not exist"
  elif ! count="$(jq "${COUNT_FILTER}" "${sarif}")" \
    || [[ ! "${count}" =~ ^[0-9]+$ ]]; then
    reason="SARIF ${sarif} is not a readable Grype report"
  fi

  if [[ -n "${reason}" ]]; then
    UNJUDGED+=("${platform}")
    printf 'Fixable high/critical findings in %s (%s): unknown\n' "${IMAGE}" "${platform}"
    printf '::warning::%s on %s could not be judged: %s. It will not be tagged.\n' \
      "${IMAGE}" "${platform}" "${reason}"
    return 0
  fi

  JUDGED+=("${platform}")
  COUNTS+=("${count}")
  TOTAL=$((TOTAL + count))
  printf 'Fixable high/critical findings in %s (%s): %s\n' "${IMAGE}" "${platform}" "${count}"
}

write_summary() {
  local index
  local platform
  local sarif
  local rule_ids=()

  {
    printf '### %s: %s fixable high/critical finding(s), not tagged\n' "${IMAGE}" "${TOTAL}"
    for index in "${!JUDGED[@]}"; do
      if [[ "${COUNTS[index]}" -eq 0 ]]; then
        continue
      fi
      platform="${JUDGED[index]}"
      sarif="$(sarif_for "${platform}")"
      mapfile -t rule_ids < <(jq -r "${RULES_FILTER}" "${sarif}")
      printf '\n**%s** (%s)\n\n' "${platform}" "${COUNTS[index]}"
      printf -- '- %s\n' "${rule_ids[@]}"
    done
    if [[ "${#UNJUDGED[@]}" -gt 0 ]]; then
      printf '\nNot judged: %s\n' "${UNJUDGED[*]}"
    fi
  } | tee -a "${GITHUB_STEP_SUMMARY:-/dev/null}"
}

write_count() {
  local count="$1"

  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    printf 'count=%s\n' "${count}" >>"${GITHUB_OUTPUT}"
  else
    printf 'count=%s\n' "${count}"
  fi
}

main() {
  local platform

  check_inputs
  parse_platforms
  for platform in "${EXPECTED[@]}"; do
    judge_platform "${platform}"
  done

  if [[ "${TOTAL}" -gt 0 ]]; then
    write_summary
  fi

  if [[ "${#UNJUDGED[@]}" -gt 0 ]]; then
    write_count ""
  else
    write_count "${TOTAL}"
  fi
}

main "$@"
