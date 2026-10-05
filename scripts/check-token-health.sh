#!/usr/bin/env bash
set -euo pipefail

API_URL="https://api.github.com/rate_limit"
RUNBOOK="docs/MAINTENANCE.md (section: Automation Token)"
REQUIRED_SCOPES=(repo workflow)
WARN_DAYS="${WARN_DAYS:-14}"
HEADERS_FILE=""
STATUS=""
NOW=""
TMP_HEADERS=""
FAILED=0

usage() {
  cat <<'EOF'
Usage: BOT_TOKEN=<token> scripts/check-token-health.sh [--headers FILE --status CODE] [--now EPOCH]

Canary for the BOT_TOKEN personal access token the repository automation runs on.
Exits 1 (red run) when the token is missing, rejected, short of a required scope,
or within WARN_DAYS (default 14) of its expiry. Exits 0 otherwise.

Environment:
  BOT_TOKEN   token to check (required)
  WARN_DAYS   days before expiry at which the check turns red (default 14)

Test seams (no network call is made):
  --headers FILE   evaluate these canned response headers
  --status CODE    HTTP status to pair with --headers
  --now EPOCH      use this Unix time instead of the clock
EOF
  return 0
}

fail_usage() {
  echo "$1" >&2
  usage >&2
  exit 2
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    local arg="$1"
    case "${arg}" in
      --headers|--status|--now)
        if [[ $# -lt 2 ]]; then
          fail_usage "Option ${arg} needs a value."
        fi
        case "${arg}" in
          --headers) HEADERS_FILE="$2" ;;
          --status) STATUS="$2" ;;
          --now) NOW="$2" ;;
          *) fail_usage "Unknown option: ${arg}" ;;
        esac
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        fail_usage "Unknown option: ${arg}"
        ;;
    esac
  done
}

validate_args() {
  if [[ -n "${HEADERS_FILE}" && -z "${STATUS}" ]] || [[ -z "${HEADERS_FILE}" && -n "${STATUS}" ]]; then
    fail_usage "--headers and --status must be given together."
  fi
  if [[ -n "${HEADERS_FILE}" && ! -r "${HEADERS_FILE}" ]]; then
    fail_usage "Cannot read headers file: ${HEADERS_FILE}"
  fi
  if [[ -n "${STATUS}" && ! "${STATUS}" =~ ^[0-9]{3}$ ]]; then
    fail_usage "--status must be a three-digit HTTP status."
  fi
  if [[ -n "${NOW}" && ! "${NOW}" =~ ^[0-9]+$ ]]; then
    fail_usage "--now must be a Unix timestamp."
  fi
  if [[ ! "${WARN_DAYS}" =~ ^[0-9]+$ ]]; then
    fail_usage "WARN_DAYS must be a non-negative integer."
  fi
}

cleanup() {
  if [[ -n "${TMP_HEADERS}" ]]; then
    rm -f "${TMP_HEADERS}"
  fi
  return 0
}

require_token() {
  if [[ -z "${BOT_TOKEN:-}" ]]; then
    echo "::error::BOT_TOKEN is empty: the Actions secret is missing or not passed to this job. See ${RUNBOOK}." >&2
    exit 1
  fi
  if [[ "${BOT_TOKEN}" =~ [[:space:][:cntrl:]] ]]; then
    echo "::error::BOT_TOKEN contains whitespace or control characters; store it again. See ${RUNBOOK}." >&2
    exit 1
  fi
}

fetch_headers() {
  local curl_exit=0
  TMP_HEADERS="$(mktemp)"
  HEADERS_FILE="${TMP_HEADERS}"
  # The token reaches curl on stdin (-H @-), never as an argument: argv is
  # world-readable through ps, stdin is not.
  STATUS="$(
    printf 'Authorization: Bearer %s\n' "${BOT_TOKEN}" \
      | curl --proto '=https' --tlsv1.2 -sS --retry 3 --max-time 30 \
        -H @- -D "${HEADERS_FILE}" -o /dev/null -w '%{http_code}' "${API_URL}"
  )" || curl_exit=$?
  if [[ "${curl_exit}" -ne 0 ]]; then
    echo "::error::Could not reach ${API_URL} (curl exit ${curl_exit}); BOT_TOKEN was not checked." >&2
    exit 1
  fi
}

header_value() {
  local name="$1"
  awk -v name="${name}" '
    BEGIN { name = tolower(name) }
    {
      sub(/\r$/, "")
      idx = index($0, ":")
      if (idx == 0) next
      if (tolower(substr($0, 1, idx - 1)) == name) {
        value = substr($0, idx + 1)
        found = 1
      }
    }
    END {
      if (!found) exit 1
      gsub(/^[ \t]+|[ \t]+$/, "", value)
      print value
    }
  ' "${HEADERS_FILE}"
}

check_status() {
  case "${STATUS}" in
    200)
      return 0
      ;;
    401)
      echo "::error::BOT_TOKEN was rejected by GitHub (HTTP 401): it is expired or revoked. Renew it: ${RUNBOOK}." >&2
      exit 1
      ;;
    *)
      echo "::error::Unexpected HTTP ${STATUS} from ${API_URL}; BOT_TOKEN could not be checked." >&2
      exit 1
      ;;
  esac
}

check_scopes() {
  local scopes normalised scope
  local -a missing=()
  if ! scopes="$(header_value x-oauth-scopes)"; then
    return 0
  fi
  normalised=",${scopes//[[:space:]]/},"
  for scope in "${REQUIRED_SCOPES[@]}"; do
    if [[ "${normalised}" != *",${scope},"* ]]; then
      missing+=("${scope}")
    fi
  done
  if [[ "${#missing[@]}" -gt 0 ]]; then
    echo "::error::BOT_TOKEN is missing required scope(s): ${missing[*]}. Recreate it with: ${REQUIRED_SCOPES[*]}. See ${RUNBOOK}." >&2
    FAILED=1
  fi
}

check_expiry() {
  local expiry expiry_epoch expiry_date days_left
  if ! expiry="$(header_value github-authentication-token-expiration)"; then
    echo "::notice::BOT_TOKEN is accepted and has no expiry set."
    return 0
  fi
  if ! expiry_epoch="$(date -u -d "${expiry}" +%s 2>/dev/null)"; then
    echo "::error::BOT_TOKEN expiry header could not be parsed; the expiry date is unknown." >&2
    FAILED=1
    return 0
  fi
  expiry_date="$(date -u -d "@${expiry_epoch}" '+%Y-%m-%d %H:%M UTC')"
  days_left=$(((expiry_epoch - NOW) / 86400))
  if [[ "${days_left}" -le "${WARN_DAYS}" ]]; then
    echo "::error::BOT_TOKEN expires in ${days_left} days (on ${expiry_date}). Renew it: ${RUNBOOK}." >&2
    FAILED=1
    return 0
  fi
  echo "::notice::BOT_TOKEN is accepted and expires on ${expiry_date} (${days_left} days left)."
}

main() {
  parse_args "$@"
  validate_args
  trap cleanup EXIT
  require_token
  if [[ -z "${NOW}" ]]; then
    NOW="$(date -u +%s)"
  fi
  if [[ -z "${HEADERS_FILE}" ]]; then
    fetch_headers
  fi
  check_status
  check_scopes
  check_expiry
  return "${FAILED}"
}

main "$@"
