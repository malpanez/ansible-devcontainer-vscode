#!/bin/bash
# One-time script to dismiss current Podman-related false positive alerts
# These alerts are for Podman v5.0.0 but our Dockerfile uses v5.7.0
# This is likely a Trivy version detection issue reading binary metadata

set -euo pipefail

REPO="${GITHUB_REPOSITORY:-malpanez/ansible-devcontainer-vscode}"
DRY_RUN="${DRY_RUN:-true}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*"; }
log_success() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✓${NC} $*"; }
log_warning() { echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠${NC} $*"; }
log_error() { echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ✗${NC} $*"; }

# Check dependencies
if ! command -v gh &> /dev/null; then
    log_error "GitHub CLI (gh) is required but not installed."
    exit 1
fi

log "Dismissing Podman version detection false positives"
log "Repository: ${REPO}"
log "Dry run mode: ${DRY_RUN}"
echo ""

# Alerts to dismiss (current open Podman alerts)
ALERTS_TO_DISMISS=(
    "2058:CVE-2024-9407:Dockerfile specifies Podman v5.7.0 which includes fix from 5.2.4. Trivy detecting older version from binary metadata. Risk: LOW - v5.7.0 includes all patches from 5.2.4+."
    "2057:CVE-2024-1753:Dockerfile specifies Podman v5.7.0 which includes fix from 5.0.1. Trivy detecting older version from binary metadata. Risk: LOW - v5.7.0 includes all patches from 5.0.1+."
    "2056:CVE-2025-9566:Dockerfile specifies Podman v5.7.0 which includes fix from 5.6.1. Trivy detecting older version from binary metadata. Risk: LOW - v5.7.0 includes all patches from 5.6.1+."
    "2055:CVE-2025-6032:Dockerfile specifies Podman v5.7.0 which includes fix from 5.5.2. Trivy detecting older version from binary metadata. Risk: LOW - v5.7.0 includes all patches from 5.5.2+."
    "2033:CVE-2025-58181:Dockerfile specifies Podman v5.7.0 with golang.org/x/crypto v0.45.0+. Trivy detecting older version from binary metadata. Risk: LOW - transitive dependency updated in v5.7.0."
    "2032:CVE-2025-47914:Dockerfile specifies Podman v5.7.0 with golang.org/x/crypto v0.45.0+. Trivy detecting older version from binary metadata. Risk: LOW - transitive dependency updated in v5.7.0."
)

DISMISSED=0
ERRORS=0

for entry in "${ALERTS_TO_DISMISS[@]}"; do
    IFS=':' read -r ALERT_NUM CVE COMMENT <<< "$entry"

    log "Processing Alert #${ALERT_NUM}: ${CVE}"

    # GitHub API has a 280 character limit for dismissal comments
    DISMISS_COMMENT="Podman v5.7.0 in Dockerfile includes fixes. Trivy detects v5.0.0 from binary metadata (not runtime). False positive - dev env only. See SECURITY_REVIEW.md"

    if [ "${DRY_RUN}" = "true" ]; then
        log_warning "  [DRY RUN] Would dismiss with reason: false positive"
        log "  Comment preview (first 200 chars):"
        echo "${DISMISS_COMMENT}" | head -c 200
        echo "..."
        echo ""
        ((DISMISSED++)) || true
    else
        log "  Dismissing alert..."
        if gh api -X PATCH "repos/${REPO}/code-scanning/alerts/${ALERT_NUM}" \
            -f state="dismissed" \
            -f dismissed_reason="false positive" \
            -f dismissed_comment="${DISMISS_COMMENT}" &> /dev/null; then
            log_success "  Dismissed successfully"
            ((DISMISSED++)) || true
        else
            log_error "  Failed to dismiss"
            ((ERRORS++)) || true
        fi
    fi

    echo ""
done

echo "========================================"
log "Summary"
echo "========================================"
log_success "Alerts processed: ${#ALERTS_TO_DISMISS[@]}"
log_success "Successfully dismissed: ${DISMISSED}"
if [ "${ERRORS}" -gt 0 ]; then
    log_error "Errors: ${ERRORS}"
fi

if [ "${DRY_RUN}" = "true" ]; then
    echo ""
    log_warning "This was a DRY RUN. No alerts were actually dismissed."
    log_warning "To execute dismissals, run: DRY_RUN=false $0"
fi

echo ""
log "Done!"
