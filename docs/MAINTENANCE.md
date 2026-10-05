# Repository Maintenance Guide

**Last Updated**: 2026-10-05
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

**Renovate** (self-hosted, in GitHub Actions) manages dependency updates.
It replaced Dependabot because this repo pins tool versions in Dockerfile
`ARG`s that Dependabot cannot reach.

#### What It Does
- **Weekly PRs** (Mondays, targeting `develop`, auto-merged on green) for:
  - Python packages (pyproject.toml + uv.lock)
  - GitHub Actions (SHA-pinned) and Docker base-image digests
  - The `ARG`-pinned CLI tools (terraform, terragrunt, tflint, sops, age,
    tectonic, aws-cli, uv) via regex custom managers
  - Ansible Galaxy collections and Terraform providers
- A companion workflow (`renovate-postprocess.yml`) runs on each Renovate
  PR in a full runner and, when needed, recomputes the age/tectonic/
  aws-cli hashes (`scripts/refresh-tool-pins.py --sync-hashes`),
  regenerates the `requirements*.txt` exports from uv.lock, and resyncs
  the active `.devcontainer` — then pushes the fix back so CI re-runs.
- Runs with `BOT_TOKEN` (see [Automation Token](#5-automation-token-bot_token));
  the Dependency Dashboard issue lists everything.

#### Configuration
- Config: [`renovate.json`](renovate.json)
- Workflows: [`renovate.yml`](../.github/workflows/renovate.yml) (scheduled Monday +
  `workflow_dispatch`, `force` input to ignore the schedule) and
  [`renovate-postprocess.yml`](../.github/workflows/renovate-postprocess.yml)

#### Rules That Are Easy To Break

- **`uv.lock` is the source of truth.** `requirements.txt`,
  `requirements-ansible.txt` and `requirements-ci-quality.txt` are
  *generated* from it by `uv export`, so Renovate is disabled for all
  three. It used to bump them
  directly, which left them ahead of the lock and, on 2026-08-16, let a
  HIGH `cryptography` advisory look patched while the lock still resolved
  the vulnerable version — the next regeneration would have reverted it.
  When something looks updated, check the lock too:
  `grep -A1 'name = "<pkg>"' uv.lock`.
- **CI tools belong in a dependency group, not in a bare `pip install`.**
  `quality.yml` and `sbom-verification.yml` install their tooling from
  `requirements-ci-quality.txt` with `--require-hashes`; the group lives in
  `pyproject.toml` so Renovate manages it like everything else. Before this,
  `pip install ansible ansible-lint` resolved whatever PyPI served that day —
  which is how CI ran ansible 14.3.1 against a lock pinning 14.2.0 and broke
  develop on 2026-08-10.
- **Never regenerate the exports locally.** The build pins uv via
  `ARG UV_VERSION`; a different local uv rewrites every `--hash=sha256:`
  line and drops hashes from the ansible export. Change the lock and let
  lock file maintenance or the companion regenerate the exports in CI.
- **Security fixes auto-merge regardless of update type.**
  `vulnerabilityAlerts.automerge` is set, because the ordinary automerge
  rule only matches patch/minor — a HIGH advisory once waited six days
  purely because its fix was a major. CI still gates the merge.
- **Dependabot must stay off.** Deleting `.github/dependabot.yml` only
  stops *version* updates; *security* updates are a separate
  repository-level toggle that will re-open PRs duplicating Renovate's.
  The **alerts** stay enabled — Renovate consumes them:
  ```bash
  gh api -X DELETE repos/OWNER/REPO/automated-security-fixes   # updates off
  gh api repos/OWNER/REPO/vulnerability-alerts -i | head -1    # 204 = alerts on
  ```

#### How to Monitor
```bash
# View recent dependency PRs
gh pr list --label "dependencies"

# Open security advisories (Renovate raises fixes from these)
gh api repos/OWNER/REPO/dependabot/alerts \
  --jq '[.[]|select(.state=="open")]|length'
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

### 5. Automation Token (`BOT_TOKEN`)

**One personal access token** carries every automated step that the
built-in `GITHUB_TOKEN` cannot do: pushing to protected `develop`, opening
dependency PRs, and producing pushes that trigger other workflows. It is
stored as the Actions secret `BOT_TOKEN` and acts as `malpanez`.

It has an expiry, and when it lapses nothing announces it. On 2026-10-03 it
expired 90 days after it was stored and half the automation stopped
without a single alert.

#### What Depends On It

| Workflow | Uses the token to | What breaks on expiry |
| --- | --- | --- |
| [`sync-main-to-develop.yml`](../.github/workflows/sync-main-to-develop.yml) | Check out and push the `main` merge to protected `develop` (admin bypass of the required check) | Run fails at checkout; `develop` stops receiving `main`'s merge commits |
| [`renovate.yml`](../.github/workflows/renovate.yml) | Run Renovate (branches, PRs, auto-merge) | No dependency PRs at all |
| [`renovate-postprocess.yml`](../.github/workflows/renovate-postprocess.yml) | Check out the Renovate branch and push the regenerated hashes, `requirements*.txt` and `.devcontainer` | Run fails at checkout on every open Renovate PR |
| [`promote-to-main.yml`](../.github/workflows/promote-to-main.yml) | Approve the promotion PR's parked workflow runs and enable auto-merge | Runs stay parked (`action_required`) until approved by hand; auto-merge falls back to `GITHUB_TOKEN`, whose merge push emits no events (no build on `main`, no sync) until the scheduled sweeps catch up |
| [`auto-release.yml`](../.github/workflows/auto-release.yml) | Check out and push the release tag so the tag push triggers `release.yml` | Run fails at checkout: no tag, no release |

The `secrets.BOT_TOKEN || github.token` fallbacks in `sync-main-to-develop.yml`
and `auto-release.yml` only apply when the secret is **absent**. An expired
token is still a non-empty secret, so it is used and rejected.

#### Required Token

- **Type**: personal access token (classic). Fine-grained tokens do not
  report their scopes, so the canary could not verify them.
- **Owner**: a repository admin — the sync push bypasses `develop`'s required
  status check as admin (`enforce_admins` is off).
- **Scopes**: `repo` and `workflow` (Renovate edits workflow files; approving
  a parked run needs `repo`).
- **Expiry**: always set one. The canary below is what makes that safe.

#### Canary

- Workflow: [`token-health.yml`](../.github/workflows/token-health.yml)
- Script: [`scripts/check-token-health.sh`](../scripts/check-token-health.sh)
- Schedule: Daily (06:17 UTC), plus manual trigger
- Method: one authenticated `GET /rate_limit` (costs no quota), then reads the
  `github-authentication-token-expiration` and `x-oauth-scopes` response headers

It goes **red** when:
- the secret is empty or missing
- GitHub rejects the token (HTTP 401: expired or revoked)
- the token lacks `repo` or `workflow`
- the token expires within 14 days (`WARN_DAYS`)
- the API answers anything else than 200, or cannot be reached

When green it prints the expiry date and the days left as a notice.

It does **not** verify that the token's owner is still a repository admin;
that only shows as a rejected push in `Sync Main to Develop`.

The alert is the failed scheduled run. GitHub sends that notification to the
user who created the workflow or last changed its `cron` line (or who last
re-enabled it), and only if their Actions notifications are on:
https://github.com/settings/notifications → Actions.

Scheduled workflows only run from the default branch, so the canary is live
once `token-health.yml` is on `main`.

#### Renewal Runbook

```bash
# 1. Create the token at https://github.com/settings/tokens (classic, scopes: repo, workflow)
# 2. Store it — paste at the prompt, never on the command line:
gh secret set BOT_TOKEN --repo malpanez/ansible-devcontainer-vscode
# 3. Prove it works and restart what stopped:
gh workflow run token-health.yml
gh workflow run sync-main-to-develop.yml
gh workflow run renovate.yml
# 4. Only if a promotion PR is open with parked runs:
gh workflow run promote-to-main.yml
```

Then confirm the canary is green and delete the old token:
```bash
gh run list --workflow token-health.yml --limit 1
```

#### Symptoms of an Expired Token

| Symptom | Where | Cause |
| --- | --- | --- |
| `Sync Main to Develop` is red; checkout ends with `fatal: could not read Username for 'https://github.com'` | Actions → Sync Main to Develop | Checkout authenticates with the rejected token |
| `HTTP 401: Bad credentials` in the log, promotion PR checks stuck waiting for approval | Actions → Promote develop to main | The token can neither approve the parked runs nor enable auto-merge |
| No Renovate PRs on Monday | Pull requests, Dependency Dashboard | Renovate cannot authenticate |
| `Token Health` is red | Actions → Token Health | The canary itself: read its annotation |

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
   - Document it in the relevant docs/ page
   - Document purpose and usage

3. **Update Renovate coverage**
   - Add a regex custom manager in `renovate.json` for the new `ARG`
   - Pin the version as a Dockerfile ARG with its checksum
   - If the tool ships no upstream checksum manifest, add it to
     `scripts/refresh-tool-pins.py` (the post-process hash sync)

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
   - Update `SECURITY.md` or the .grype.yaml rationale comments if needed
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
- **Token Health**: Active (daily canary for `BOT_TOKEN`)
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
grype dir:. --only-fixed --fail-on high

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

- [.github/security-alert-exceptions.yml](.github/security-alert-exceptions.yml) - CVE exceptions config

---

## Troubleshooting

### Automation Stopped (`BOT_TOKEN` Expired or Rejected)

**Symptoms**: `Sync Main to Develop` red at checkout, `HTTP 401: Bad credentials`
in `Promote develop to main`, no Renovate PRs on Monday

**Solutions**:
1. Read the latest canary result: `gh run list --workflow token-health.yml --limit 1`
2. Renew the token: [Renewal Runbook](#renewal-runbook)

### Renovate Not Creating PRs

**Symptoms**: No dependency update PRs for 2+ weeks

**Solutions**:
1. Check that `Token Health` is green (Renovate runs with `BOT_TOKEN`)
2. Check Renovate dashboard for errors
3. Validate `renovate.json` syntax
4. Check if rate limit exceeded
5. Manually trigger: `gh workflow run renovate.yml`

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

### 2026-10-05
- ✅ Documented `BOT_TOKEN`: consumers, required scopes, renewal runbook
- ✅ Added the daily `Token Health` canary after the silent expiry of 2026-10-03

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
