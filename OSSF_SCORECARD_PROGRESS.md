# OpenSSF Scorecard Improvement Progress

**Last Updated**: 2025-12-03
**Status**: 🔄 In Progress

---

## Overview

This document tracks our progress implementing OpenSSF Scorecard improvements to increase the repository's security score.

**Related Documents**:
- [SECURITY_ALERT_ANALYSIS_110.md](SECURITY_ALERT_ANALYSIS_110.md) - Full analysis of 110 remaining alerts
- [SECURITY_REVIEW.md](SECURITY_REVIEW.md) - Initial 6 Podman alerts analysis
- [SECURITY_ALERT_MANAGEMENT_SUMMARY.md](SECURITY_ALERT_MANAGEMENT_SUMMARY.md) - Automation guide

### Current Alert Status

**Total Open Alerts**: 110 (as of 2025-12-02, after dismissing 6 Podman alerts)

| Category | Count | Priority | Status |
|----------|-------|----------|--------|
| OpenSSF Scorecard Issues | 27 | 🔴 Critical | ⏳ In Progress |
| Go Stdlib CVEs (vendor bins) | 54 | 🟡 Medium | ⏳ To Document |
| Container Image Alerts | 29 | 🟢 Low | ⏳ To Review |

### Current Scorecard Issues

1. **Pinned-Dependencies** (20 alerts) - CRITICAL
   - Issue: Docker base images not pinned by digest
   - Issue: GitHub Actions not pinned by commit SHA
   - Status: ✅ Phase 1A Complete (Docker images) | ⏳ Phase 1B Pending (Actions)

2. **Token-Permissions** (7 alerts) - CRITICAL
   - Issue: Workflows missing explicit `permissions:` declarations
   - Affected: 6 workflows (auto-merge, cleanup-ghcr, dependency-refresh, promote-to-main, quality, release)
   - Status: ⏳ Not Started

3. **Branch-Protection** - IMPORTANT
   - Issue: Not enough required reviewers, no branch protection rules
   - Status: ⏳ Not Started

4. **Code-Review** - IMPORTANT
   - Issue: PRs merged without review
   - Status: ⏳ Not Started

---

## Phase 1: Pinned Dependencies

### Phase 1A: Docker Base Images ✅ COMPLETE

**PR**: [#130](https://github.com/malpanez/ansible-devcontainer-vscode/pull/130)
**Branch**: `feat/ossf-scorecard-pinned-dependencies`
**Status**: ✅ All Dockerfiles Updated | ⏳ CI Running

#### Files Updated

| File | Base Image | Pinned Digest | Status |
|------|-----------|---------------|--------|
| `devcontainers/base/Dockerfile` | `python:3.12.12-slim-bookworm` | `sha256:5621ae4640bf259c8a9f09c513cd6c80fc14b3fab3d9cf99f3227637cdf78525` | ✅ |
| `devcontainers/ansible/Dockerfile` | `python:3.12-slim-bookworm` | `sha256:5621ae4640bf259c8a9f09c513cd6c80fc14b3fab3d9cf99f3227637cdf78525` | ✅ |
| `devcontainers/ansible/Dockerfile.podman` | `python:3.12-slim-bookworm` + `podman:v5.7.0` | `sha256:5621ae4640bf259c8a9f09c513cd6c80fc14b3fab3d9cf99f3227637cdf78525` + `sha256:2f5944072be14f41dceb2ece57302959f7cd541af7435060fb77813b2a00069f` | ✅ |
| `devcontainers/golang/Dockerfile` | `golang:1.25.4-alpine3.21` | `sha256:66318aca70141a077877f813ad6e903b3d6e0ef861b5f41defb80e4b29364c57` | ✅ |
| `devcontainers/latex/Dockerfile` | `debian:bookworm-slim` | `sha256:72ceb30c8c49e50d4bf87aa6eb5390c3bcf091c13f41e6382e79953ea44c11c8` | ✅ |
| `devcontainers/terraform/Dockerfile` | `debian:bookworm-slim` | `sha256:72ceb30c8c49e50d4bf87aa6eb5390c3bcf091c13f41e6382e79953ea44c11c8` | ✅ |

**Commit**: `8f37104` - "feat(security): pin all Docker base images by SHA256 digest"

#### Verification Commands

```bash
# Verify all Dockerfiles have pinned images
grep -r "FROM.*@sha256:" devcontainers/

# Check for unpinned images (should return nothing)
grep -r "FROM [^@]*$" devcontainers/ --include="Dockerfile*" | grep -v "AS " | grep -v "@sha256"
```

#### Next Steps for Phase 1A

1. ⏳ **Wait for CI to complete** - Builds in progress
2. ⏳ **Verify builds succeed** - All 4 stacks (ansible, golang, latex, terraform)
3. ⏳ **Merge PR #130 to develop** - After CI passes
4. ⏳ **Verify Scorecard improvement** - Check score after merge

---

### Phase 1B: GitHub Actions ⏳ TODO

**Objective**: Pin all GitHub Actions to commit SHAs instead of tags

**Status**: Not Started

#### Actions to Pin

Need to audit all workflow files in `.github/workflows/` for actions using tags:

```bash
# Find all actions using tags (not SHAs)
grep -r "uses:.*@v[0-9]" .github/workflows/

# Expected pattern change:
# Before: uses: actions/checkout@v4
# After:  uses: actions/checkout@a12b3c4d5e6f7890123456789abcdef01234567  # v4.1.2
```

#### Workflow Files to Audit

Actual workflow files in the repository:
- [ ] `.github/workflows/auto-merge.yml`
- [ ] `.github/workflows/build-containers.yml`
- [ ] `.github/workflows/ci.yml`
- [ ] `.github/workflows/cleanup-ghcr.yml`
- [ ] `.github/workflows/dependency-refresh.yml`
- [ ] `.github/workflows/promote-to-main.yml`
- [ ] `.github/workflows/quality.yml`
- [ ] `.github/workflows/release.yml`
- [ ] `.github/workflows/scorecard.yml`
- [ ] `.github/workflows/security-alert-management.yml`
- [ ] `.github/workflows/stale.yml`
- [ ] `.github/workflows/sync-main-to-develop.yml`
- [ ] `.github/workflows/test-containers.yml`

#### Implementation Plan

1. **Audit Phase**
   - List all actions used across workflows
   - Identify current versions (tags)
   - Get commit SHAs for each version

2. **Update Phase**
   - Replace tags with commit SHAs
   - Add inline comments with version numbers
   - Test workflows still execute correctly

3. **Documentation Phase**
   - Document pinned versions
   - Create update process/policy
   - Add to maintenance runbook

**Estimated Effort**: 2-3 hours

---

## Phase 1.5: Token Permissions ⏳ TODO

**Status**: Not Started
**Priority**: 🔴 Critical (7 alerts)

### Problem

OpenSSF Scorecard requires explicit `permissions:` in all workflows following least-privilege principle.

**Current State**: 6 workflows missing `permissions:` declarations run with default `read-write` permissions.

### Affected Workflows

According to [SECURITY_ALERT_ANALYSIS_110.md](SECURITY_ALERT_ANALYSIS_110.md):

1. `.github/workflows/auto-merge.yml` - Missing permissions
2. `.github/workflows/cleanup-ghcr.yml` - Missing permissions
3. `.github/workflows/dependency-refresh.yml` - Missing permissions
4. `.github/workflows/promote-to-main.yml` - Missing permissions
5. `.github/workflows/quality.yml` - May need update
6. `.github/workflows/release.yml` - May need update

### Implementation

Add explicit permissions following least-privilege:

```yaml
permissions:
  contents: read        # Read repo contents (default for most)
  pull-requests: write  # If creating/updating PRs
  packages: write       # If publishing to GHCR
  security-events: write # If uploading SARIF/security scans
```

### Checklist

- [ ] Audit each workflow to determine required permissions
- [ ] Add `permissions:` block to each job or workflow level
- [ ] Test workflows still function correctly
- [ ] Commit and verify Scorecard alerts resolved

**Estimated Effort**: 30-45 minutes

---

## Phase 2: Document Go Stdlib CVEs ⏳ TODO

**Status**: Not Started
**Priority**: 🟡 Medium (54 alerts)

### Problem

54 alerts for Go stdlib CVEs in vendored binaries (age, sops, terragrunt) that we don't compile ourselves.

### Analysis Summary

From [SECURITY_ALERT_ANALYSIS_110.md](SECURITY_ALERT_ANALYSIS_110.md):

| Binary | Alerts | Why We Can't Fix |
|--------|--------|------------------|
| `age` / `age-keygen` | 42 | Vendor binary from upstream |
| `sops` | 12 | Vendor binary from upstream |
| `terragrunt`, `terraform`, `tflint` | Varies | Vendor binaries from upstream |

**Key CVEs**:
- CVE-2025-58181 (SSH GSSAPI) - MEDIUM
- CVE-2025-47914 (SSH Agent) - MEDIUM
- CVE-2025-61725 (net/mail CPU) - MEDIUM
- CVE-2025-58187 (crypto/x509) - HIGH
- CVE-2025-58186 (net/http cookie) - HIGH
- CVE-2025-58183 (archive/tar) - HIGH

### Risk Assessment

**Impact**: LOW
- Development environment only (not production)
- Limited attack surface (local tools, not exposed services)
- SSH CVEs only affect SSH server functionality (we don't run SSH servers)
- DoS CVEs require malicious input

### Recommended Approach

**Option C: Document as Accepted Risk** ✅

1. Update `.github/security-alert-exceptions.yml` with CVE exceptions
2. Add automation rule to dismiss after 30 days
3. Document in SECURITY_REVIEW.md
4. Re-evaluate quarterly

### Implementation

#### 1. Update Alert Exceptions Config

Edit `.github/security-alert-exceptions.yml`:

```yaml
accepted_risks:
  go_stdlib_vendor_binaries:
    description: "Go stdlib CVEs in vendor binaries (age, sops, terragrunt)"
    rationale: "Development environment only, limited attack surface. Awaiting upstream fixes."
    review_frequency: "Quarterly"
    cves:
      - CVE-2025-58181  # golang.org/x/crypto SSH
      - CVE-2025-47914  # golang.org/x/crypto SSH Agent
      - CVE-2025-61725  # net/mail CPU exhaustion
      - CVE-2025-61724  # net/textproto CPU exhaustion
      - CVE-2025-61723  # encoding/pem quadratic
      - CVE-2025-58189  # crypto/tls ALPN
      - CVE-2025-58188  # crypto/x509 DSA panic
      - CVE-2025-58187  # crypto/x509 name constraints
      - CVE-2025-58186  # net/http cookie DoS
      - CVE-2025-58185  # encoding/asn1 exhaustion
      - CVE-2025-58183  # archive/tar unbounded
      - CVE-2025-47912  # net/url IPv6
```

#### 2. Update Alert Management Script

Edit `.github/scripts/manage-code-scanning-alerts.sh`:

```bash
# Rule 5: Go stdlib CVEs in vendor binaries
if [[ "${LOCATION}" =~ (usr/local/bin/(age|sops|terragrunt|terraform|tflint)) ]] && \
   [[ "${RULE_ID}" =~ ^CVE-2025-(58181|58183|58185|58186|58187|58188|58189|47912|47914|61723|61724|61725)$ ]]; then
    if [ "${AGE_DAYS}" -ge 30 ]; then
        SHOULD_DISMISS=true
        DISMISS_REASON="used in tests"
        DISMISS_COMMENT="Go stdlib CVE in vendor binary. Risk accepted for dev env. Awaiting upstream fix. See SECURITY_REVIEW.md"
    fi
fi
```

#### 3. Update Security Review

Add section to SECURITY_REVIEW.md documenting the 54 Go stdlib CVE exceptions.

**Estimated Effort**: 1 hour

---

## Phase 3: Branch Protection ⏳ TODO

**Status**: Not Started

### Current State

- Branch protection exists on `main`
- Required checks: "CI Success", "Quality Summary"
- No required reviewers
- No dismiss stale reviews
- No require signed commits

### Improvements Needed

1. **Add required reviewers**
   - Require at least 1 approval
   - Dismiss stale reviews on new commits

2. **Strengthen protection rules**
   - Require status checks to pass
   - Require branches to be up to date
   - Require signed commits (optional)

3. **Apply to `develop` branch**
   - Same rules as `main`
   - Prevent direct pushes

### Implementation

```bash
# Example: Update branch protection via GitHub API
gh api -X PUT /repos/malpanez/ansible-devcontainer-vscode/branches/main/protection \
  -f required_status_checks='{"strict":true,"contexts":["CI Success","Quality Summary"]}' \
  -f enforce_admins=true \
  -f required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  -f restrictions=null
```

**Estimated Effort**: 1 hour

---

## Phase 3: Code Review ⏳ TODO

**Status**: Not Started

### Current Issues

- PRs merged without reviews (automated merges)
- Dependabot PRs auto-merged without review
- No review checklist

### Improvements Needed

1. **Require reviews for all PRs**
   - Including Dependabot PRs
   - Including bot-generated PRs

2. **Create review guidelines**
   - Security checklist
   - Code quality checklist
   - Testing requirements

3. **Update auto-merge workflow**
   - Add approval requirement
   - Add security scan requirement

**Estimated Effort**: 2 hours

---

## Additional Improvements

### Security Alert Management ✅ COMPLETE

**Documentation**:
- ✅ [SECURITY_REVIEW.md](SECURITY_REVIEW.md) - Comprehensive analysis
- ✅ [SECURITY_ALERT_MANAGEMENT_SUMMARY.md](SECURITY_ALERT_MANAGEMENT_SUMMARY.md) - Usage guide
- ✅ `.github/scripts/manage-code-scanning-alerts.sh` - Automation script
- ✅ `.github/workflows/security-alert-management.yml` - Weekly workflow

**Current Alerts**: 6 (all Podman version detection false positives)

**Next Steps**:
1. ⏳ Run one-time cleanup: `bash .github/scripts/dismiss-current-podman-alerts.sh`
2. ⏳ Monitor weekly automation (Mondays 9 AM UTC)

---

## Pre-commit Workflow Changes ✅ COMPLETE

**PR**: [#128](https://github.com/malpanez/ansible-devcontainer-vscode/pull/128)

**Changes**:
- ✅ Removed pre-commit from CI workflows
- ✅ Pre-commit now local-only (before push)
- ✅ Updated branch protection (removed "Pre-commit" check)
- ✅ Created sync-main-to-develop workflow

**Rationale**: Pre-commit hooks should run locally, not in CI, to:
- Reduce CI time
- Fail fast before push
- Keep CI focused on tests/builds

---

## Timeline & Priority

### High Priority (This Week)

1. ✅ Complete Phase 1A (Docker images) - **IN REVIEW**
2. ⏳ Start Phase 1B (GitHub Actions) - **NEXT**
3. ⏳ Deploy security alert cleanup

### Medium Priority (Next Week)

4. ⏳ Implement Phase 2 (Branch Protection)
5. ⏳ Implement Phase 3 (Code Review)

### Low Priority (Next Month)

6. Document maintenance procedures
7. Create security runbook
8. Set up metrics dashboard

---

## Scorecard Target

### Current Score
*TODO: Run scorecard and record baseline*

### Target Score
- **Pinned-Dependencies**: 10/10 (from ~5/10)
- **Branch-Protection**: 8/10 (from ~3/10)
- **Code-Review**: 7/10 (from ~2/10)
- **Overall**: Improve from ~4/10 to ~7/10

### How to Check Score

```bash
# Install scorecard
go install github.com/ossf/scorecard/v5/cmd/scorecard@latest

# Run scorecard
scorecard --repo=github.com/malpanez/ansible-devcontainer-vscode
```

---

## References

- [OpenSSF Scorecard Documentation](https://github.com/ossf/scorecard)
- [Best Practices Badge](https://bestpractices.coreinfrastructure.org/)
- [GitHub Branch Protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)
- [Pinning Actions](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions#using-third-party-actions)

---

*Last updated: 2025-12-03*
*Next review: After PR #130 merge*
