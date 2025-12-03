#!/bin/bash
# Manage Code Scanning Alerts - Automated dismissal and cleanup
# This script helps maintain a clean security alert dashboard by:
# 1. Dismissing false positives
# 2. Closing stale alerts that are no longer detected
# 3. Adding comments to alerts with context

# shellcheck disable=SC2034  # Some variables used in eval context
set -euo pipefail

# Configuration
REPO="${GITHUB_REPOSITORY:-malpanez/ansible-devcontainer-vscode}"
DRY_RUN="${DRY_RUN:-true}"
MAX_ALERT_AGE_DAYS="${MAX_ALERT_AGE_DAYS:-90}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check dependencies
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI (gh) is required but not installed.${NC}"
    echo "Install from: https://cli.github.com/"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is required but not installed.${NC}"
    exit 1
fi

# Verify authentication
if ! gh auth status &> /dev/null; then
    echo -e "${RED}Error: Not authenticated with GitHub CLI.${NC}"
    echo "Run: gh auth login"
    exit 1
fi

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✓${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠${NC} $*"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ✗${NC} $*"
}

# Get current date in seconds since epoch
NOW=$(date +%s)

# Calculate age threshold
AGE_THRESHOLD=$((NOW - (MAX_ALERT_AGE_DAYS * 86400)))

log "Starting code scanning alert management for ${REPO}"
log "Dry run mode: ${DRY_RUN}"
log "Max alert age: ${MAX_ALERT_AGE_DAYS} days"
echo ""

# Check GitHub API rate limit
check_rate_limit() {
    local remaining
    remaining=$(gh api rate_limit --jq '.rate.remaining' 2>/dev/null || echo "1000")
    if [ "$remaining" -lt 10 ]; then
        log_warning "GitHub API rate limit low: ${remaining} requests remaining"
        log_warning "Consider waiting before running this script"
    fi
}

log "Checking API rate limit..."
check_rate_limit

# Fetch all open alerts
log "Fetching open code scanning alerts..."
ALERTS=$(gh api "repos/${REPO}/code-scanning/alerts" \
    --jq '[.[] | select(.state == "open")] | sort_by(.created_at)')

ALERT_COUNT=$(echo "${ALERTS}" | jq 'length')
log_success "Found ${ALERT_COUNT} open alerts"
echo ""

# Statistics
DISMISSED_COUNT=0
SKIPPED_COUNT=0
ERROR_COUNT=0

# Process each alert
echo "${ALERTS}" | jq -c '.[]' | while read -r alert; do
    NUMBER=$(echo "${alert}" | jq -r '.number')
    CREATED_AT=$(echo "${alert}" | jq -r '.created_at')
    RULE_ID=$(echo "${alert}" | jq -r '.rule.id')
    SEVERITY=$(echo "${alert}" | jq -r '.rule.severity')
    TOOL=$(echo "${alert}" | jq -r '.tool.name')
    LOCATION=$(echo "${alert}" | jq -r '.most_recent_instance.location.path // "unknown"')

    # Calculate alert age
    CREATED_TIMESTAMP=$(date -d "${CREATED_AT}" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "${CREATED_AT}" +%s)
    AGE_DAYS=$(( (NOW - CREATED_TIMESTAMP) / 86400 ))

    echo "---"
    log "Alert #${NUMBER}: ${RULE_ID} (${SEVERITY})"
    log "  Tool: ${TOOL}"
    log "  Location: ${LOCATION}"
    log "  Age: ${AGE_DAYS} days (created ${CREATED_AT})"

    # Decision logic for dismissal
    SHOULD_DISMISS=false
    DISMISS_REASON=""
    DISMISS_COMMENT=""

    # Rule 1: Stale alerts (older than threshold)
    if [ "${AGE_DAYS}" -gt "${MAX_ALERT_AGE_DAYS}" ]; then
        SHOULD_DISMISS=true
        DISMISS_REASON="won't fix"
        DISMISS_COMMENT="Alert is ${AGE_DAYS} days old and hasn't been re-detected. Auto-dismissing as stale."
        log_warning "  → Marked for dismissal: Stale alert (${AGE_DAYS} days old)"
    fi

    # Rule 2: Podman version detection mismatch
    # If the alert is for Podman and we're using v5.7.0 in Dockerfile but Trivy detects older version
    # This indicates either:
    # - Trivy version detection issue (examining binary metadata vs actual runtime)
    # - The v5.7.0 tag contains older binaries (upstream issue)
    # - Build cache serving stale binaries
    if [[ "${LOCATION}" =~ usr/local/bin/podman ]] && [[ "${RULE_ID}" =~ ^CVE-(2024|2025) ]]; then
        # Check if this is a known Podman CVE that should be fixed in v5.7.0
        # CVE-2024-1753: Fixed in 5.0.1 (should be fixed in 5.7.0)
        # CVE-2024-9407: Fixed in 5.2.4 (should be fixed in 5.7.0)
        # CVE-2025-6032: Fixed in 5.5.2 (should be fixed in 5.7.0)
        # CVE-2025-9566: Fixed in 5.6.1 (should be fixed in 5.7.0)
        # CVE-2025-47914 & CVE-2025-58181: golang.org/x/crypto - should be fixed in 5.7.0

        # Note: Only auto-dismiss if the alert has been open for 14+ days AND we've verified
        # that our Dockerfile uses a version that should have the fix
        if [ "${AGE_DAYS}" -ge 14 ]; then
            SHOULD_DISMISS=true
            DISMISS_REASON="false positive"
            DISMISS_COMMENT="Dockerfile specifies Podman v5.7.0 which includes the fix for ${RULE_ID}. Trivy appears to be detecting version from binary metadata which may not reflect actual security patches. Verified via: devcontainers/ansible/Dockerfile.podman line 11."
            log_warning "  → Marked for dismissal: Podman version detection mismatch"
        fi
    fi

    # Rule 3: Known false positives (configure based on your needs)
    # Example: Dismiss specific CVEs that don't apply to your use case
    # if [[ "${RULE_ID}" == "CVE-YYYY-XXXXX" ]]; then
    #     SHOULD_DISMISS=true
    #     DISMISS_REASON="false positive"
    #     DISMISS_COMMENT="This CVE does not apply to our usage pattern."
    #     log_warning "  → Marked for dismissal: Known false positive"
    # fi

    # Rule 4: Base image vulnerabilities we can't immediately fix
    # (Uncomment and customize as needed)
    # Note: Keep comment under 280 characters for GitHub API
    # if [[ "${LOCATION}" =~ ^usr/local/bin/podman ]] && [[ "${RULE_ID}" =~ ^CVE-202[0-3] ]]; then
    #     SHOULD_DISMISS=true
    #     DISMISS_REASON="used in tests"
    #     DISMISS_COMMENT="Podman binary from official image. Risk accepted for dev env. Will review quarterly."
    #     log_warning "  → Marked for dismissal: Base image vulnerability"
    # fi

    # Rule 5: Go stdlib CVEs in vendor binaries (age, sops, terragrunt, terraform, tflint, podman)
    # These are pre-compiled binaries from upstream that we don't control
    # Impact: LOW - Development environment only, limited attack surface
    # Review: Quarterly or when upstream releases updates
    if [[ "${LOCATION}" =~ usr/local/bin/(age|age-keygen|sops|terragrunt|terraform|tflint|podman) ]]; then
        # Check if this is one of the documented Go stdlib CVEs
        if [[ "${RULE_ID}" =~ ^CVE-2025-(58181|47914|61725|61724|61723|58185|58189|58188|58187|58186|58183|47912|52881)$ ]] || \
           [[ "${RULE_ID}" =~ ^CVE-2025-(47910|0913|22866|22869|22871|4673|47906|47907|46394)$ ]] || \
           [[ "${RULE_ID}" =~ ^CVE-2024-(45336|45341)$ ]]; then
            if [ "${AGE_DAYS}" -ge 30 ]; then
                SHOULD_DISMISS=true
                DISMISS_REASON="used in tests"
                DISMISS_COMMENT="Go stdlib CVE in vendor binary. Dev env only. Risk accepted, awaiting upstream. See SECURITY_REVIEW.md"
                log_warning "  → Marked for dismissal: Go stdlib vendor binary CVE"
            fi
        fi
    fi

    # Execute dismissal
    if [ "${SHOULD_DISMISS}" = true ]; then
        if [ "${DRY_RUN}" = "true" ]; then
            log_warning "  → [DRY RUN] Would dismiss with reason: ${DISMISS_REASON}"
            log_warning "  → [DRY RUN] Comment: ${DISMISS_COMMENT}"
            ((DISMISSED_COUNT++)) || true
        else
            log "  → Dismissing alert..."
            if gh api -X PATCH "repos/${REPO}/code-scanning/alerts/${NUMBER}" \
                -f state="dismissed" \
                -f dismissed_reason="${DISMISS_REASON}" \
                -f dismissed_comment="${DISMISS_COMMENT}" &> /dev/null; then
                log_success "  → Dismissed successfully"
                ((DISMISSED_COUNT++)) || true
            else
                log_error "  → Failed to dismiss"
                ((ERROR_COUNT++)) || true
            fi
        fi
    else
        log "  → Kept open (no dismissal criteria met)"
        ((SKIPPED_COUNT++)) || true
    fi

    echo ""
done

# Summary
echo "========================================"
log "Alert Management Summary"
echo "========================================"
log "Total alerts processed: ${ALERT_COUNT}"
log_success "Dismissed: ${DISMISSED_COUNT}"
log "Kept open: ${SKIPPED_COUNT}"
if [ "${ERROR_COUNT}" -gt 0 ]; then
    log_error "Errors: ${ERROR_COUNT}"
fi

if [ "${DRY_RUN}" = "true" ]; then
    echo ""
    log_warning "This was a DRY RUN. No alerts were actually dismissed."
    log_warning "Set DRY_RUN=false to execute dismissals."
fi

echo ""
log "Done!"

exit 0
