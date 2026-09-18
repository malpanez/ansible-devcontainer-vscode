# Branch Protection Configuration

This document describes the branch protection rules configured on this repository's Git Flow branches, and what they oblige the workflows to do.

## Overview

The repository uses a **Git Flow** branching strategy with two protected branches:

- **`main`** - Production-ready code
- **`develop`** - Integration branch for ongoing development

## Current Branch Protection Rules

These tables describe what is actually configured today. Read them back with
`gh api repos/:owner/:repo/branches/main/protection` and
`gh api repos/:owner/:repo/branches/develop/protection`.

### For `main` branch

Navigate to: **Settings → Branches → Edit rule**

**Branch name pattern:** `main`

| Setting | Value |
| --- | --- |
| Require a pull request before merging | Yes |
| Required approvals | 1 |
| Dismiss stale pull request approvals | Yes |
| Require review from Code Owners | Yes |
| Require approval of the most recent push | No |
| Require status checks to pass | Yes |
| Require branches to be up to date (`strict`) | No |
| Require conversation resolution | Yes |
| Require signed commits | No |
| Require linear history | No |
| Do not allow bypassing (`enforce_admins`) | Yes |
| Allow force pushes | No |
| Allow deletions | No |
| Lock branch | No |

**Required status checks on `main`:**

- `CI Success` (from `ci.yml`)
- `CodeQL Summary` (from `codeql.yml`)
- `SBOM Verification Success` (from `sbom-verification.yml`)
- `Quality Summary` (from `quality.yml`)

`Guard Main Promotion Path` (from `enforce-promotion-path.yml`, on PRs whose
base is `main`) and `GitGuardian Security Checks` report on these PRs but are
**not** required contexts.

---

### For `develop` branch

**Branch name pattern:** `develop`

| Setting | Value |
| --- | --- |
| Require a pull request before merging | No review requirement configured |
| Require status checks to pass | Yes |
| Require branches to be up to date (`strict`) | No |
| Require conversation resolution | No |
| Require signed commits | No |
| Require linear history | No |
| Do not allow bypassing (`enforce_admins`) | No |
| Allow force pushes | No |
| Allow deletions | No |
| Lock branch | No |

**Required status checks on `develop`:**

- `CI Success` (from `ci.yml`)
- `SBOM Verification Success` (from `sbom-verification.yml`)
- `Quality Summary` (from `quality.yml`)

`develop` deliberately does **not** require `CodeQL Summary`; CodeQL still
runs on every pull request into it. `Guard Develop Intake` (from
`enforce-promotion-path.yml`) also reports here without being required.

---

### What a required check obliges the workflow to do

Two consequences follow from the lists above, and both have already cost a
blocked promotion:

1. **Every required workflow must start on every push and pull request, and
   gate its work from inside.** A required context that never appears leaves
   the pull request waiting forever -- GitHub does not treat "the workflow
   was skipped" as "the check passed". Trigger-level `paths` / `paths-ignore`
   filters are therefore banned in `ci.yml`, `codeql.yml`, `quality.yml` and
   `sbom-verification.yml`; each one runs a cheap `changes` job
   (`dorny/paths-filter`) and gates the expensive jobs on its outputs, and
   each aggregate job is `if: always()` and fails only on a job whose result
   is `failure`, so a skipped job stays green.

2. **`Quality Summary` gates that the metrics ran, not what they found.** The
   jobs in `quality.yml` are deliberately non-blocking (`continue-on-error`,
   `no-fail: true`): they publish complexity, dead-code, lint and Hadolint
   reports. The check fails only if one of those jobs itself fails -- for
   example when the hash-pinned install breaks. The lint gates that can
   actually reject a change live in `ci.yml` and in the pre-commit hooks.

---

## Reading and Setting Protection via GitHub CLI

### Read the current rules

```bash
gh api repos/:owner/:repo/branches/main/protection
gh api repos/:owner/:repo/branches/develop/protection
```

### Reapply the `main` rules

```bash
gh api repos/:owner/:repo/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":false,"contexts":["CI Success","CodeQL Summary","SBOM Verification Success","Quality Summary"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"dismiss_stale_reviews":true,"require_code_owner_reviews":true,"required_approving_review_count":1}' \
  --field restrictions=null \
  --field required_linear_history=false \
  --field allow_force_pushes=false \
  --field allow_deletions=false \
  --field required_conversation_resolution=true
```

### Reapply the `develop` rules

```bash
gh api repos/:owner/:repo/branches/develop/protection \
  --method PUT \
  --field required_status_checks='{"strict":false,"contexts":["CI Success","SBOM Verification Success","Quality Summary"]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews=null \
  --field restrictions=null \
  --field required_linear_history=false \
  --field allow_force_pushes=false \
  --field allow_deletions=false \
  --field required_conversation_resolution=false
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
- Before adding a required check, merge the workflow that produces it first: a
  context required but never reported blocks every pull request
- Adjust approval requirements as team grows
- Consider enabling "Require deployments to succeed" for production releases
- Periodically audit who has bypass permissions
- Keep `main` as a promotion branch: target it from `develop` for normal releases and from `hotfix/*` only for urgent production fixes

---

## References

- [GitHub Branch Protection Documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [GitHub Rulesets Documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [Git Flow Workflow](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow)
