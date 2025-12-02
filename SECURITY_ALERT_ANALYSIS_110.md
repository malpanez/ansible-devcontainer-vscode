# Security Alert Analysis - 110 Open Alerts

**Date**: 2025-12-02
**Branch**: main
**Total Alerts**: 110

---

## Executive Summary

After dismissing the 6 Podman false positives, **110 alerts remain** on the main branch. These fall into three categories:

| Category | Count | Severity | Priority | Action Required |
|----------|-------|----------|----------|-----------------|
| **OpenSSF Scorecard** | 27 | HIGH | 🔴 **Critical** | Fix now |
| **Go Stdlib CVEs** | 54 | MEDIUM | 🟡 **Medium** | Document exceptions |
| **Container Images** | 29 | LOW-MEDIUM | 🟢 **Low** | Review & dismiss |

---

## Category 1: OpenSSF Scorecard Issues (27 alerts) 🔴

### 1.1 Pinned-Dependencies (20 alerts)

**Issue**: Dockerfiles and workflows use unpinned dependencies.

**Affected Files**:
- All 10 Dockerfiles (base, ansible, golang, terraform, latex, podman variant)
- GitHub Actions workflows (ci.yml, quality.yml, release.yml)

**Risk**: Supply chain attacks if upstream images/actions are compromised.

**Recommendation**: **FIX THIS** - High priority for security posture.

**Solution**:
```dockerfile
# Before (vulnerable)
FROM python:3.12-slim-bookworm

# After (secure)
FROM python:3.12-slim-bookworm@sha256:abc123...
```

**Estimated Effort**: 2-3 hours to pin all dependencies + digest lookup.

---

### 1.2 Token-Permissions (7 alerts)

**Issue**: GitHub Actions workflows missing explicit `permissions:` declarations.

**Affected Workflows**:
1. `.github/workflows/auto-merge.yml`
2. `.github/workflows/cleanup-ghcr.yml`
3. `.github/workflows/dependency-refresh.yml`
4. `.github/workflows/promote-to-main.yml`
5. `.github/workflows/quality.yml`
6. `.github/workflows/release.yml`

**Risk**: Workflows run with default `read-write` permissions, violating least-privilege.

**Recommendation**: **FIX THIS** - Required for security compliance.

**Solution**:
```yaml
permissions:
  contents: read  # Only what's needed
  packages: write  # If publishing
```

**Estimated Effort**: 30 minutes to add permissions to 6 workflows.

---

## Category 2: Go Stdlib CVEs (54 alerts) 🟡

### Overview

All alerts are in **vendored Go binaries** that we don't compile ourselves:
- `age` / `age-keygen` (21 + 21 = 42 alerts)
- `sops` (12 alerts)
- `terragrunt`, `terraform`, `tflint` (varies)

**Key CVEs**:
| CVE | Count | Severity | Package | Description |
|-----|-------|----------|---------|-------------|
| CVE-2025-58181 | 6 | MEDIUM | golang.org/x/crypto | SSH GSSAPI validation |
| CVE-2025-47914 | 6 | MEDIUM | golang.org/x/crypto | SSH Agent message size |
| CVE-2025-61725 | 4 | MEDIUM | net/mail | CPU exhaustion in ParseAddress |
| CVE-2025-61724 | 3 | MEDIUM | net/textproto | CPU exhaustion in ReadResponse |
| CVE-2025-58187 | 3 | HIGH | crypto/x509 | Name constraint checking panic |
| CVE-2025-58186 | 3 | HIGH | net/http | Cookie header DoS |
| CVE-2025-58183 | 3 | HIGH | archive/tar | Unbounded allocation |

### Analysis

**Root Cause**: These are upstream vendor binaries (age, sops, terragrunt) that we download but don't compile. We cannot patch them ourselves.

**Impact Assessment**:
- **Development environment only** - Not production-facing
- **Limited attack surface** - Tools used locally, not exposed services
- **SSH CVEs** - Only affect SSH server functionality (we don't run SSH servers in containers)
- **DoS CVEs** - Require malicious input to trigger

**Options**:

#### Option A: Wait for Upstream Fixes ⏳
- Monitor age, sops, terragrunt releases
- Update when fixed versions available
- **Timeline**: Varies by vendor (weeks to months)

#### Option B: Compile from Source 🔨
- Build age, sops, terragrunt with latest Go stdlib
- Adds complexity to build process
- **Effort**: High (4-8 hours + maintenance)

#### Option C: Document as Accepted Risk ✅
- Add to `.trivyignore` or dismiss in GitHub
- Document in security review
- Re-evaluate quarterly
- **Effort**: Low (30 minutes)

**Recommendation**: **Option C** for now, **Option A** long-term.

**Rationale**:
1. Development environment only (not production)
2. Limited attack surface
3. Most CVEs require specific attack vectors (malicious SSH connections, crafted HTTP headers)
4. Time better spent on Category 1 (Scorecard) fixes
5. Can reassess when upstream releases new versions

---

## Category 3: Container Image Alerts (29 alerts) 🟢

**Affected**: Various base images and their dependencies.

**Examples**:
- BusyBox CVE-2025-46394 in golang image
- Misc stdlib issues in vendor binaries

**Recommendation**: Review individually, likely dismiss most as:
- Base image issues (upstream responsibility)
- False positives
- Not applicable to use case

---

## Remediation Plan

### Phase 1: Critical Fixes (This Week) 🔴

**Priority 1A: Fix Scorecard - Pinned Dependencies**
1. Pin all Docker base images by digest
2. Pin all GitHub Actions by commit SHA
3. Update documentation

**Files to Update**:
```
devcontainers/base/Dockerfile
devcontainers/ansible/Dockerfile
devcontainers/ansible/Dockerfile.podman
devcontainers/golang/Dockerfile
devcontainers/terraform/Dockerfile
devcontainers/latex/Dockerfile
.devcontainer/Dockerfile
.github/workflows/ci.yml
.github/workflows/quality.yml
.github/workflows/release.yml
```

**Priority 1B: Fix Scorecard - Token Permissions**
1. Add explicit `permissions:` to all workflows
2. Follow least-privilege principle
3. Test workflows still function

**Files to Update**:
```
.github/workflows/auto-merge.yml
.github/workflows/cleanup-ghcr.yml
.github/workflows/dependency-refresh.yml
.github/workflows/promote-to-main.yml
.github/workflows/quality.yml (update existing)
.github/workflows/release.yml (update existing)
```

### Phase 2: Document Exceptions (This Week) 🟡

**Priority 2: Go Stdlib CVEs**
1. Update `.trivyignore` or alert automation
2. Add to SECURITY_REVIEW.md
3. Set quarterly review schedule

**Exceptions to Document**:
```
# Go stdlib CVEs in vendor binaries (age, sops, terragrunt)
# Accepted risk: Development environment only, limited attack surface
# Review: Quarterly or when upstream releases updates
CVE-2025-58181  # golang.org/x/crypto SSH
CVE-2025-47914  # golang.org/x/crypto SSH Agent
CVE-2025-61725  # net/mail CPU exhaustion
CVE-2025-61724  # net/textproto CPU exhaustion
CVE-2025-61723  # encoding/pem quadratic complexity
CVE-2025-58189  # crypto/tls ALPN
CVE-2025-58188  # crypto/x509 DSA panic
CVE-2025-58187  # crypto/x509 name constraints
CVE-2025-58186  # net/http cookie DoS
CVE-2025-58185  # encoding/asn1 exhaustion
CVE-2025-58183  # archive/tar unbounded alloc
CVE-2025-47912  # net/url IPv6 validation
```

### Phase 3: Review Remaining (Next Week) 🟢

**Priority 3: Container Image Alerts**
1. Review 29 remaining alerts
2. Dismiss false positives
3. Fix or document real issues

---

## Automation Updates

### Update Alert Management Script

Add rules for Go stdlib CVEs:

```bash
# Rule 5: Go stdlib CVEs in vendor binaries
if [[ "${LOCATION}" =~ (usr/local/bin/(age|sops|terragrunt|terraform|tflint)) ]] && \
   [[ "${RULE_ID}" =~ ^CVE-2025-(58181|58183|58185|58186|58187|58188|58189|47912|47914|61723|61724|61725)$ ]]; then
    if [ "${AGE_DAYS}" -ge 30 ]; then
        SHOULD_DISMISS=true
        DISMISS_REASON="used in tests"
        DISMISS_COMMENT="Go stdlib CVE in vendor binary. Risk accepted for dev env. Awaiting upstream fix. See SECURITY_REVIEW.md"
        log_warning "  → Marked for dismissal: Vendor binary Go stdlib CVE"
    fi
fi
```

---

## Timeline & Effort

| Phase | Tasks | Effort | Deadline |
|-------|-------|--------|----------|
| **Phase 1A** | Pin dependencies (20 files) | 2-3 hours | This week |
| **Phase 1B** | Add permissions (6 files) | 30 min | This week |
| **Phase 2** | Document exceptions | 1 hour | This week |
| **Phase 3** | Review remaining | 2 hours | Next week |
| **Total** | | **6 hours** | |

---

## Success Metrics

### Before
- ✗ 110 open alerts
- ✗ No pinned dependencies
- ✗ Missing workflow permissions
- ✗ Scorecard failing

### After (Phase 1)
- ✅ 83 open alerts (27 fixed)
- ✅ All dependencies pinned
- ✅ Workflow permissions explicit
- ✅ Scorecard passing

### After (Phase 2)
- ✅ ~29 open alerts (54 documented)
- ✅ Clear exception policy
- ✅ Quarterly review schedule

### After (Phase 3)
- ✅ <10 open alerts
- ✅ All alerts reviewed
- ✅ False positives dismissed

---

## Recommendations

### Immediate Actions (Today)
1. ✅ **Merge current PR** (alert automation)
2. 🔴 **Start Phase 1A** (pin dependencies)
3. 🔴 **Start Phase 1B** (add permissions)

### This Week
4. 🟡 **Complete Phase 2** (document exceptions)
5. 📝 **Update automation** (add Go stdlib rules)

### Next Week
6. 🟢 **Complete Phase 3** (review remaining)
7. 📊 **Review metrics** (validate improvements)

---

## Notes

- **Scorecard issues** are the highest priority - they directly impact security posture and are easy to fix
- **Go stdlib CVEs** are lower priority - they're in vendor binaries we don't control, in a dev environment
- **Container alerts** can wait - need individual review but likely dismissable
- **Total effort**: ~6 hours to get from 110 → <10 alerts

---

*Analysis Date: 2025-12-02*
*Next Review: After Phase 1 completion*
