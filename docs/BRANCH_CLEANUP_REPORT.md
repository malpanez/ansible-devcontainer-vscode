# Branch Cleanup Report

**Generated**: 2025-12-04
**Status**: Pending cleanup

## Summary

This report identifies branches that can be safely deleted after verifying their content has been merged into main.

## Branches Ready for Deletion

### Already Merged (Content in Main)

These branches appear to have their changes already incorporated into main through other PRs:

1. **feat/ossf-scorecard-pinned-dependencies** (last: 2025-12-03)
   - OpenSSF Scorecard improvements are in main via PR #134

2. **feat/ossf-pin-github-actions** (last: 2025-12-03)
   - GitHub Actions pinning completed in main

3. **feat/security-and-polish** (last: 2025-12-01)
   - Security improvements merged

4. **fix/trivy-cve-hadolint-complete** (last: 2025-12-01)
   - Trivy and CVE fixes in main

5. **feat/container-structure-tests** (last: 2025-12-01)
   - Container testing added to main

6. **fix/security-round-2-permissions-go-update** (last: 2025-12-01)
   - Security permissions updated

7. **feat/add-trivy-scan-to-build-workflow** (last: 2025-12-01)
   - Trivy scan workflow is live in main

8. **security/update-dependencies-reduce-alerts** (last: 2025-12-02)
   - Dependencies updated via Renovate

9. **feat/additional-cve-documentation** (last: 2025-12-03)
   - CVE documentation in main

10. **fix/scorecard-hadolint-alerts** (last: 2025-12-01)
    - Hadolint issues resolved

### Potentially Obsolete (Old/Stale)

These branches haven't been updated recently and may be superseded:

1. **refactor/slimmer-devcontainers-precommit** (last: 2025-11-08)
   - Pre-commit refactoring may be superseded by recent changes

2. **docs/update-pyproject-migration** (last: unknown)
   - PyProject migration likely complete

3. **docs/update-pyproject-migration-fix** (last: unknown)
   - Follow-up fix likely not needed

4. **feature/base-pre-commit** (last: unknown)
   - Base pre-commit setup complete

5. **feature/fix-build-single** (last: unknown)
   - Build fixes incorporated

6. **fix/build-workflow-args** (last: unknown)
   - Workflow args likely fixed

7. **fix/dockerfile-podman-arg-scope** (last: unknown)
   - Podman arg scope fixed

8. **feat/remove-precommit-from-ci** (last: unknown)
   - CI workflow updated

9. **feat/build-dockerfile-variants** (last: unknown)
   - Dockerfile variants in main

10. **feature/release-owner-namespace** (last: unknown)
    - Release namespace configured

### Active/Recent (Keep for Now)

These branches have recent activity and should be reviewed manually:

1. **docs/integration-guide** (last: 2025-12-04) ✅
   - Has unique changes (PROMPTS.md, devcontainer updates)
   - Ready for merge after rebase with main

2. **docs/ossf-phases-3-4-complete** (last: 2025-12-04)
   - Recent OSSF Phase 3&4 work
   - Verify if content already in main via PR #134

3. **fix/sync-workflow-branch-condition** (last: 2025-12-04)
   - Recent fix for sync workflow
   - Check if already applied

4. **chore/update-tool-versions** (last: 2025-11-30)
   - Tool version updates
   - May still be relevant

5. **feat/vscode-improvements-and-branch-cleanup** (last: 2025-12-04) ✅
   - Just created - contains this automation!

## Cleanup Script Usage

```bash
# Dry run first (recommended)
./scripts/cleanup-merged-branches.sh --dry-run

# Interactive cleanup (asks for confirmation)
./scripts/cleanup-merged-branches.sh

# Or use the new VS Code task:
# Command Palette → Tasks: Run Task → "Cleanup Merged Branches"
```

## Automated Cleanup

The new workflow `.github/workflows/cleanup-merged-branches.yml` will automatically:
- Delete branches after successful PR merges
- Can be manually triggered with dry-run option
- Protects main/develop branches

## Manual Verification Steps

Before running cleanup:

1. For each branch, check if content is in main:
   ```bash
   git log main --oneline --grep="<branch-topic>"
   ```

2. Check for unique commits:
   ```bash
   git log main..<branch-name> --oneline
   ```

3. Review any unmerged changes:
   ```bash
   git diff main...<branch-name>
   ```

## Recommendations

### Immediate Actions
1. ✅ Merge `feat/vscode-improvements-and-branch-cleanup` (this PR)
2. ✅ Merge `docs/integration-guide` (already rebased with main)
3. Review `docs/ossf-phases-3-4-complete` and `fix/sync-workflow-branch-condition`

### Batch Cleanup
After verifying content is in main, delete these 20 obsolete branches:
- All 10 "Already Merged" branches
- All 10 "Potentially Obsolete" branches

### Verification
Use the dry-run script to see exactly what would be deleted:
```bash
./scripts/cleanup-merged-branches.sh --dry-run
```

---

**Next Update**: After merging active branches and running cleanup
