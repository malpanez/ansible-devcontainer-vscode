# Branch Protection Configuration

This document describes the recommended branch protection rules for this repository's Git Flow workflow.

## Overview

The repository uses a **Git Flow** branching strategy with two protected branches:
- **`main`** - Production-ready code
- **`develop`** - Integration branch for ongoing development

## Recommended Branch Protection Rules

### For `main` branch

Navigate to: **Settings → Branches → Add branch protection rule**

**Branch name pattern:** `main`

#### Required Settings

- [x] **Require a pull request before merging**
  - [x] Require approvals: **1** (optional for solo maintainer, recommended for teams)
  - [x] Dismiss stale pull request approvals when new commits are pushed
  - [x] Require review from Code Owners (if CODEOWNERS file exists)

- [x] **Require status checks to pass before merging**
  - [x] Require branches to be up to date before merging
  - **Required checks** (select all that apply):
    - `CI Success` (from ci.yml)
    - `Pre-commit` (from ci.yml)
    - `Quality Summary` (from quality.yml)
    - `Security Scan` (from ci.yml)
    - `GitGuardian Security Checks`

- [x] **Require conversation resolution before merging**
  - Ensures all PR comments are addressed

- [x] **Require signed commits** (optional but recommended)
  - Enforces commit signature verification

- [x] **Require linear history**
  - Prevents merge commits, enforces squash or rebase

- [x] **Do not allow bypassing the above settings**
  - Applies rules to administrators too (recommended)

- [x] **Restrict who can push to matching branches**
  - Leave empty to allow only via PRs (recommended)
  - Or add: GitHub Actions bot (for automation)

#### Optional but Recommended

- [x] **Require deployments to succeed before merging** (if using GitHub Environments)
- [x] **Lock branch** (if you want to prevent all direct pushes, even from admins)

---

### For `develop` branch

Navigate to: **Settings → Branches → Add branch protection rule**

**Branch name pattern:** `develop`

#### Required Settings

- [x] **Require a pull request before merging**
  - [x] Require approvals: **0** (can be increased for teams)
  - [x] Dismiss stale pull request approvals when new commits are pushed

- [x] **Require status checks to pass before merging**
  - [x] Require branches to be up to date before merging
  - **Required checks** (select all that apply):
    - `CI Success` (from ci.yml)
    - `Pre-commit` (from ci.yml)
    - `Quality Summary` (from quality.yml)

- [x] **Require conversation resolution before merging**

- [x] **Allow force pushes** → **Specify who can force push**
  - Add: Repository maintainers (for rebasing/cleaning history if needed)

- [x] **Do not allow bypassing the above settings** (optional for develop)

---

## Quick Setup via GitHub CLI

You can also configure branch protection using the GitHub CLI:

### Protect `main` branch

```bash
gh api repos/:owner/:repo/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["CI Success","Pre-commit","Quality Summary","Security Scan"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"dismiss_stale_reviews":true,"require_code_owner_reviews":false,"required_approving_review_count":1}' \
  --field restrictions=null \
  --field required_linear_history=true \
  --field allow_force_pushes=false \
  --field allow_deletions=false \
  --field required_conversation_resolution=true
```

### Protect `develop` branch

```bash
gh api repos/:owner/:repo/branches/develop/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["CI Success","Pre-commit","Quality Summary"]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews='{"dismiss_stale_reviews":true,"require_code_owner_reviews":false,"required_approving_review_count":0}' \
  --field restrictions=null \
  --field allow_force_pushes=true \
  --field allow_deletions=false \
  --field required_conversation_resolution=true
```

---

## Rulesets (Modern Alternative)

GitHub now offers **Rulesets** as a more flexible alternative to branch protection rules. To use rulesets:

1. Navigate to: **Settings → Rules → Rulesets → New ruleset**
2. Choose **Branch ruleset**
3. Configure similar rules as above but with more granular control

Rulesets allow:
- Targeting multiple branches with patterns
- Bypass permissions for specific users/teams/apps
- More fine-grained status check requirements
- Better organization of rules

---

## Testing Branch Protection

After configuring, test with:

```bash
# Try to push directly to main (should fail)
git checkout main
echo "test" >> README.md
git add README.md
git commit -m "test: direct push"
git push origin main
# Expected: Error - branch protection rules

# Correct workflow (should work)
git checkout develop
git checkout -b feat/test-branch-protection
echo "test" >> README.md
git add README.md
git commit -m "feat: test branch protection"
git push origin feat/test-branch-protection
gh pr create --base develop --title "feat: test branch protection"
# Expected: PR created successfully
```

---

## Maintenance Notes

- Review and update required status checks when adding/removing CI jobs
- Adjust approval requirements as team grows
- Consider enabling "Require deployments to succeed" for production releases
- Periodically audit who has bypass permissions

---

## References

- [GitHub Branch Protection Documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [GitHub Rulesets Documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [Git Flow Workflow](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow)
