# ADR-0002: Git Flow Branching Strategy

**Status**: Accepted
**Date**: 2024-10-20
**Deciders**: @malpanez
**Tags**: workflow, git, collaboration

---

## Context

As the repository matured and gained multiple contributors, we needed a standardized branching strategy to:
- Protect the `main` branch from breaking changes
- Enable parallel feature development
- Support automated testing before merges
- Provide clear separation between development and production-ready code
- Facilitate hotfixes and release management

Without a formal strategy, we risked:
- Broken builds on `main`
- Merge conflicts from simultaneous work
- Unclear release states
- Difficult rollbacks

---

## Decision

Adopt **Git Flow** as the branching strategy with the following structure:

- **`main`** - Production-ready code only. Protected branch, direct pushes forbidden.
- **`develop`** - Integration branch for ongoing development. All feature PRs target here.
- **Feature branches** - Created from `develop` with naming convention `feat/description`
- **Fix branches** - Created from `develop` with naming convention `fix/description`
- **Hotfix branches** - Created from `main` for urgent production fixes

All branches use conventional naming:
- `feat/*` - New features
- `fix/*` - Bug fixes
- `chore/*` - Maintenance tasks
- `docs/*` - Documentation updates
- `refactor/*` - Code refactoring
- `test/*` - Test additions/improvements

---

## Rationale

### Stability Guarantees
- `main` always represents deployable state
- All changes tested on `develop` before promotion
- Branch protection prevents accidental direct commits

### Parallel Development
- Multiple features can be developed simultaneously without conflicts
- Each feature branch isolated until ready for integration
- Clear merge targets reduce confusion

### Automation-Friendly
- GitHub Actions can run different checks on different branches
- Auto-merge workflows can promote `develop` → `main` when stable
- Dependabot PRs automatically target correct branch

### Industry Standard
- Git Flow widely adopted and understood by developers
- Extensive tooling and CI/CD integration available
- Clear visual representation in GitHub network graph

---

## Consequences

### Positive

- ✅ **Stability**: `main` branch never broken, always deployable
- ✅ **Collaboration**: Multiple developers can work in parallel without conflicts
- ✅ **Automation**: CI/CD workflows can safely auto-merge between branches
- ✅ **Clarity**: Branch names clearly indicate purpose (feat/, fix/, etc.)
- ✅ **Safety**: Branch protection prevents mistakes
- ✅ **Hotfix support**: Can quickly fix production issues without disrupting development

### Negative

- ⚠️ **Complexity**: More branches to manage than trunk-based development
- ⚠️ **Merge overhead**: Features must merge to develop, then develop to main
- ⚠️ **Learning curve**: New contributors need to understand the workflow

### Neutral

- ℹ️ Requires documenting branching strategy in CONTRIBUTING.md
- ℹ️ Need automated workflow to sync develop → main
- ℹ️ Branch cleanup needed after merges (automated via workflow)

---

## Alternatives Considered

### Alternative 1: Trunk-Based Development

**Pros:**
- Simpler (single main branch)
- Faster integration
- Less merge overhead
- Popular in large companies (Google, Facebook)

**Cons:**
- Requires very mature CI/CD and feature flags
- Higher risk of breaking main
- Less suitable for open-source with varying contributor experience
- Difficult to maintain stable release point

**Why rejected:** Trunk-based development requires sophisticated CI/CD infrastructure and highly disciplined contributors. For an open-source project with varied contributor experience levels, Git Flow provides better safety.

### Alternative 2: GitHub Flow

**Pros:**
- Simpler than Git Flow (just main + feature branches)
- Good for continuous deployment
- Easy to understand

**Cons:**
- No develop branch means less staging area
- Harder to batch changes for releases
- Every merge to main should deploy (not always desired)
- Less suitable for projects with infrequent releases

**Why rejected:** We wanted a staging area (`develop`) to test integration of multiple features before promoting to `main`. GitHub Flow's simplicity comes at the cost of flexibility we need.

### Alternative 3: GitLab Flow

**Pros:**
- Environment branches (production, staging, development)
- Good for multi-environment deployments
- Combines benefits of Git Flow and GitHub Flow

**Cons:**
- More complex branch structure
- Overkill for our use case (we don't have staging/production environments)
- Less widely adopted than Git Flow

**Why rejected:** GitLab Flow is designed for organizations with multiple deployment environments. We don't have that complexity.

---

## Implementation Notes

### Branch Protection Rules

**`main` branch:**
- Require pull request reviews before merging
- Require status checks to pass (CI, linting, security scans)
- Require branches to be up to date before merging
- Do not allow force pushes
- Do not allow deletions

**`develop` branch:**
- Require pull request reviews before merging
- Require status checks to pass
- Allow force pushes by admins only (for emergency fixes)

### Automated Workflows

1. **Auto-promote develop → main**
   - When all tests pass on `develop` for 24 hours
   - Create PR from `develop` to `main`
   - Auto-merge if CI passes

2. **Branch cleanup**
   - Delete feature branches after merge
   - Weekly cleanup of stale branches (>30 days old, no activity)

3. **Sync main → develop**
   - After hotfixes merge to `main`, auto-sync back to `develop`
   - Prevents develop from falling behind

### Contributor Workflow

```bash
# Start new feature
git checkout develop
git pull origin develop
git checkout -b feat/my-feature

# Make changes, commit
git add .
git commit -m "feat: add amazing feature"

# Push and create PR to develop
git push origin feat/my-feature
gh pr create --base develop --title "feat: add amazing feature"

# After merge, delete branch
git branch -d feat/my-feature
```

---

## References

- [Git Flow Original Blog Post](https://nvie.com/posts/a-successful-git-branching-model/)
- [Comparing Git Workflows](https://www.atlassian.com/git/tutorials/comparing-workflows)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Documents workflow for contributors

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2024-10-20 | @malpanez | Created ADR after adopting Git Flow |
| 2024-12-04 | @malpanez | Updated with automation details and cleanup workflows |
