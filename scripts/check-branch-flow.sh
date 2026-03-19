#!/usr/bin/env bash
set -euo pipefail

BASE_REF=""
HEAD_REF=""

usage() {
  cat <<'EOF'
Usage: scripts/check-branch-flow.sh --base <branch> --head <branch>

Validates whether a pull request source branch is allowed to target the given base
branch according to the repository branching strategy.
EOF
  return 0
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --base)
        BASE_REF="$2"
        shift 2
        ;;
      --head)
        HEAD_REF="$2"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "Unknown option: $1" >&2
        usage
        exit 1
        ;;
    esac
  done
}

require_args() {
  if [[ -z "${BASE_REF}" || -z "${HEAD_REF}" ]]; then
    echo "Both --base and --head are required." >&2
    usage
    exit 1
  fi
}

check_main_flow() {
  case "${HEAD_REF}" in
    develop|hotfix/*)
      echo "Source branch '${HEAD_REF}' is allowed to target main."
      return 0
      ;;
    *)
      echo "Pull requests into main must come from 'develop' or 'hotfix/*'. Current source: '${HEAD_REF}'." >&2
      return 1
      ;;
  esac
}

check_develop_flow() {
  case "${HEAD_REF}" in
    main)
      echo "Sync from main to develop is allowed."
      ;;
    feature/*|fix/*|docs/*|chore/*|refactor/*|test/*|ci/*|perf/*|hotfix/*)
      echo "Source branch '${HEAD_REF}' is allowed to target develop."
      ;;
    *)
      echo "Source branch '${HEAD_REF}' does not follow the documented naming convention." >&2
      ;;
  esac
  return 0
}

main() {
  parse_args "$@"
  require_args

  case "${BASE_REF}" in
    main)
      check_main_flow
      ;;
    develop)
      check_develop_flow
      ;;
    *)
      echo "No branch-flow rules defined for base branch '${BASE_REF}'." >&2
      return 0
      ;;
  esac
}

main "$@"
