# Repository Maintenance Guide

**Last Updated**: 2025-12-04
**Next Review**: 2026-03-04 (Quarterly)

---

## Overview

This document describes the automated and manual maintenance procedures for the ansible-devcontainer-vscode repository.

**Key Principles**:
- **Automation First**: Most maintenance tasks run automatically
- **Quarterly Reviews**: Security and dependency updates reviewed every 3 months
- **Minimal Manual Intervention**: Only critical issues require human action

---

## Automated Maintenance

### 1. Dependency Updates 🤖

**Renovate Bot** automatically manages all dependencies:

#### What It Does
- **Weekly scans** for outdated dependencies
- **Auto-creates PRs** for:
  - Python packages (pyproject.toml, uv.lock)
  - GitHub Actions (workflows/*.yml)
  - Docker base images
  - Tool versions (terraform, ansible, etc.)

#### Configuration
- File: [`.github/renovate.json`](.github/renovate.json)
- Schedule: Weekly (Mondays)
- Auto-merge: Patch and minor updates (after CI passes)
- Manual review: Major updates

#### How to Monitor
```bash
# View recent Renovate PRs
gh pr list --label "dependencies"

# View Renovate dashboard
# https://github.com/malpanez/ansible-devcontainer-vscode/issues/4
```

---

### 2. Security Alert Management 🔒

**Automated weekly cleanup** of security alerts:

#### What It Does
- **Dismisses documented CVEs** in vendor binaries
- **Monitors age of alerts** (auto-dismiss after 90 days)
- **Generates weekly reports** with statistics

#### Workflow
- File: [`.github/workflows/security-alert-management.yml`](.github/workflows/security-alert-management.yml)
- Schedule: Weekly (Mondays 9 AM UTC)
- Manual trigger: Available via GitHub Actions UI

#### Scripts
1. **Main script**: `.github/scripts/manage-code-scanning-alerts.sh`
   - Auto-dismisses stale alerts
   - Handles vendor binary CVEs
   - Generates statistics

2. **Configuration**: `.github/security-alert-exceptions.yml`
   - Documents 27 accepted CVEs
   - Defines dismissal policies
   - Review schedule

#### How to Use
```bash
# Run manually (dry-run)
DRY_RUN=true bash .github/scripts/manage-code-scanning-alerts.sh

# Run manually (dismiss alerts)
DRY_RUN=false bash .github/scripts/manage-code-scanning-alerts.sh

# Customize age threshold (default: 90 days)
MAX_ALERT_AGE_DAYS=60 bash .github/scripts/manage-code-scanning-alerts.sh
```

#### What to Review
- **Weekly**: Check workflow runs for new alerts
- **Quarterly**: Update `.github/security-alert-exceptions.yml`
- **On new CVEs**: Investigate before adding to exceptions

---

### 3. Branch Synchronization 🔄

**Auto-syncs main → develop** after every merge:

#### What It Does
- Merges `main` into `develop` automatically
- Creates PR if conflicts detected
- Keeps develop up-to-date

#### Workflow
- File: [`.github/workflows/sync-main-to-develop.yml`](.github/workflows/sync-main-to-develop.yml)
- Trigger: Every push to `main` branch
- Conflict handling: Creates PR for manual review

#### How to Handle Conflicts
```bash
# If sync PR is created:
git fetch origin
git checkout develop
git pull
git merge main
# Resolve conflicts manually
git commit
git push
```

---

### 4. Quality Checks ✅

**Pre-commit hooks** run automatically before every commit:

#### What It Does
- Lints YAML, Python, Dockerfile
- Checks for secrets
- Validates Terraform syntax
- Runs security scans

#### Setup
```bash
# Install pre-commit (already in devcontainer)
uv pip install --system pre-commit

# Install hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

#### CI Integration
- Workflow: `.github/workflows/ci.yml`
- Runs: On every PR and push
- Checks: Linting, tests, security scans

---

## Manual Maintenance Tasks

### Quarterly Review (Every 3 Months)

**Due Date**: 2026-03-04

#### 1. Security Review
- [ ] Review `.github/security-alert-exceptions.yml`
- [ ] Check for new CVEs in vendor binaries
- [ ] Update acceptance rationale if needed
- [ ] Review OpenSSF Scorecard: https://securityscorecards.dev/viewer/?uri=github.com/malpanez/ansible-devcontainer-vscode

#### 2. Dependency Audit
- [ ] Review major version updates waiting for approval
- [ ] Test containers with latest tool versions
- [ ] Update pinned tool versions in README.md

#### 3. Docker Base Images
- [ ] Check for new Python/Golang/Debian releases
- [ ] Update SHA256 digests if base images updated
- [ ] Rebuild and test all containers

```bash
# Get latest digests
docker manifest inspect python:3.12.12-slim-bookworm | jq -r '.config.digest'
docker manifest inspect golang:1.25.4-alpine3.21 | jq -r '.config.digest'
```

#### 4. Documentation Review
- [ ] Update README.md tool versions
- [ ] Review SECURITY.md for accuracy
- [ ] Update this MAINTENANCE.md if procedures changed

---

### Monthly Tasks

#### Security Alerts Check
```bash
# Check open security alerts
gh api repos/malpanez/ansible-devcontainer-vscode/code-scanning/alerts \
  --jq '.[] | select(.state == "open") | {number, rule: .rule.id, severity: .rule.severity}'

# Should show ~5 alerts (4 Scorecard + 1-2 vendor CVEs)
```

#### Workflow Health Check
```bash
# Check failed workflows
gh run list --status failure --limit 10

# Should mostly be empty (except sync-main-to-develop on feature branches - now fixed!)
```

---

### As-Needed Tasks

#### 1. Adding New Tool to Containers

When adding a new tool (e.g., new CLI utility):

1. **Update Dockerfile**
   ```dockerfile
   # Pin version explicitly
   ARG TOOL_VERSION=1.2.3
   RUN curl -LO "https://releases.example.com/tool-v${TOOL_VERSION}"
   ```

2. **Update README.md**
   - Add to "Pinned Tool Versions" table
   - Document purpose and usage

3. **Update Renovate**
   - Add to `.github/renovate.json` if possible
   - Configure auto-update rules

4. **Test**
   ```bash
   # Build and test
   cd devcontainers/ansible
   docker build -t test .
   docker run --rm test tool --version
   ```

#### 2. Handling New CVEs

When a new CVE alert appears:

1. **Investigate**
   ```bash
   # Get CVE details
   gh api "repos/malpanez/ansible-devcontainer-vscode/code-scanning/alerts/ALERT_ID"
   ```

2. **Determine Action**
   - **Fixable**: Update dependency and test
   - **Vendor binary**: Add to `.github/security-alert-exceptions.yml`
   - **False positive**: Dismiss with justification

3. **Document**
   - Update `SECURITY_REVIEW.md` if needed
   - Add to exceptions config
   - Create issue if requires upstream fix

#### 3. OpenSSF Scorecard Improvements

Current score: **6.1/10**

To improve score:

**Code-Review (currently 0/10)**:
- Score will improve automatically after PR template usage
- Scorecard cache refreshes weekly

**Maintained (currently 0/10)**:
- Requires consistent activity over 90 days
- Improves naturally with regular contributions

**Fuzzing (currently 0/10)**:
- Not applicable for infrastructure project
- No action needed

---

## Monitoring Dashboard

### Key Metrics

#### Security
- **Open Alerts**: ~5 (4 Scorecard + 1 vendor CVE)
- **OpenSSF Score**: 6.1/10
- **Last Review**: 2025-12-04
- **Next Review**: 2026-03-04

#### Automation Health
- **Renovate**: Active (weekly scans)
- **Security Alert Management**: Active (weekly runs)
- **Sync Main→Develop**: Active (on main push)
- **Pre-commit Hooks**: Active (local only)

#### Dependencies
- **Python Packages**: Auto-updated by Renovate
- **GitHub Actions**: Pinned by SHA, auto-updated by Renovate
- **Docker Base Images**: Pinned by SHA256 digest
- **Tool Versions**: Documented in README.md

---

## Quick Reference

### Useful Commands

```bash
# Check repository health
gh repo view --json openIssues,pullRequests

# View security alerts
gh api repos/malpanez/ansible-devcontainer-vscode/code-scanning/alerts \
  --jq 'map({number, rule: .rule.id, state, severity: .rule.severity})'

# Run security scan locally
trivy config .
trivy fs --scanners vuln .

# View recent workflow runs
gh run list --limit 10

# Check pre-commit hooks status
pre-commit run --all-files --show-diff-on-failure
```

### Important Links

- **OpenSSF Scorecard**: https://securityscorecards.dev/viewer/?uri=github.com/malpanez/ansible-devcontainer-vscode
- **Renovate Dashboard**: https://github.com/malpanez/ansible-devcontainer-vscode/issues/4
- **GitHub Actions**: https://github.com/malpanez/ansible-devcontainer-vscode/actions
- **Security Alerts**: https://github.com/malpanez/ansible-devcontainer-vscode/security/code-scanning

### Related Documentation

- [SECURITY_REVIEW.md](SECURITY_REVIEW.md) - Detailed security analysis
- [SECURITY_ALERT_MANAGEMENT_SUMMARY.md](SECURITY_ALERT_MANAGEMENT_SUMMARY.md) - Alert management guide
- [OSSF_SCORECARD_PROGRESS.md](OSSF_SCORECARD_PROGRESS.md) - Scorecard improvement tracking
- [.github/security-alert-exceptions.yml](.github/security-alert-exceptions.yml) - CVE exceptions config

---

## Troubleshooting

### Renovate Not Creating PRs

**Symptoms**: No dependency update PRs for 2+ weeks

**Solutions**:
1. Check Renovate dashboard for errors
2. Validate `.github/renovate.json` syntax
3. Check if rate limit exceeded
4. Manually trigger: Settings → Integrations → Renovate → Configure

### Security Workflow Failing

**Symptoms**: Weekly security workflow fails

**Solutions**:
1. Check workflow logs: `gh run view <run-id>`
2. Verify GitHub token permissions
3. Test script locally:
   ```bash
   DRY_RUN=true bash .github/scripts/manage-code-scanning-alerts.sh
   ```
4. Check `.github/security-alert-exceptions.yml` syntax

### Pre-commit Hooks Not Running

**Symptoms**: Commits bypass pre-commit checks

**Solutions**:
1. Reinstall hooks: `pre-commit install`
2. Check if using `--no-verify` flag
3. Update hooks: `pre-commit autoupdate`
4. Run manually: `pre-commit run --all-files`

### Containers Failing to Build

**Symptoms**: Docker build errors

**Solutions**:
1. Check if base image digest changed
2. Verify network connectivity for downloads
3. Test with latest base image:
   ```bash
   docker pull python:3.12.12-slim-bookworm
   docker build devcontainers/base
   ```
4. Check tool download URLs still valid

---

## Change Log

### 2025-12-04
- ✅ Initial maintenance guide created
- ✅ Documented all automated workflows
- ✅ Added quarterly review checklist
- ✅ Established monitoring procedures

### Next Steps
- [ ] Automate quarterly review reminders (GitHub Issues)
- [ ] Create dashboard for metrics visualization
- [ ] Add Slack/email notifications for critical alerts

---

*For questions or issues, create a GitHub issue or discussion.*
