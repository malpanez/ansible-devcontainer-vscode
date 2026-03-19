---
description: "Pre-PR checklist — verify everything is ready before opening a pull request to develop"
---

Run the complete pre-PR checklist for this repository. Fix every failure before declaring the PR ready.

## Pre-PR Checklist

### 1. Branch Validation

```sh
# Confirm you are NOT on main or develop
git branch --show-current

# Branch must follow the naming convention
bash scripts/check-branch-flow.sh

# Confirm target is develop (not main)
gh pr view --json baseRefName 2>/dev/null || echo "No PR yet — target branch will be develop"
```

**Valid branch prefixes:** `feature/`, `fix/`, `docs/`, `chore/`, `refactor/`, `security/`
**Hotfix only** (`hotfix/`) may target `main` — rare exception.

### 2. Full CI Locally

```sh
make ci-local
```

All steps must pass: pre-commit, yamllint, hadolint, pytest, security scan, doctor check.

### 3. Pre-commit on All Staged Changes

```sh
uvx pre-commit run --files $(git diff --name-only --cached)

# Or full suite
uvx pre-commit run --all-files
```

### 4. Commit Message Audit

```sh
# Review all commits in this branch vs develop
git log origin/develop..HEAD --oneline
```

Verify:

- [ ] All commits follow conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `security:`
- [ ] No `WIP`, `temp`, `fixup`, or vague messages
- [ ] No `Co-Authored-By:` lines

### 5. Devcontainer Health

```sh
make doctor-devcontainer
```

### 6. Test Coverage

```sh
uv run pytest tests/ --cov --cov-fail-under=95
```

Coverage must be ≥ 95 %. No exceptions.

### 7. Security

```sh
make security
```

No unaddressed HIGH or CRITICAL findings.

### 8. Documentation

- [ ] If a new tool was added to a container → `tests/test_devcontainer_tools.py` updated
- [ ] If a new script was added → `scripts/README.md` updated
- [ ] If behavior changed → relevant `docs/` file updated
- [ ] If a new stack feature → `README.md` updated

### 9. Self-Review

```sh
# Review your full diff
git diff origin/develop..HEAD

# Check for leftover debug code, TODO comments, commented-out blocks
git diff origin/develop..HEAD | grep -E '^\+.*(TODO|FIXME|HACK|XXX|print\(|console\.log|pdb|breakpoint)' || echo "Clean"
```

## PR Description Template

When opening the PR via `gh pr create`:

```
## Summary
- What changed and why (not what files were edited)
- Link to issue if applicable

## Test Plan
- [ ] `make ci-local` passed
- [ ] `make doctor-devcontainer` passed
- [ ] Coverage ≥ 95 %
- [ ] Pre-commit hooks passed

## Notes
Any context reviewers need (breaking changes, dependencies, follow-ups)
```

## Report

State whether the branch is **READY** or list each item that still needs fixing.
