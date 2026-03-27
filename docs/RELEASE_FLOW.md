# Release Flow

This repository uses `develop` as the integration branch and `main` as the production branch.

## Normal Flow

1. Create a topic branch from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/my-change
   ```
2. Open the pull request into `develop`.
3. Merge the PR after checks pass.
4. A push to `develop` triggers the promotion workflow, which creates or reuses a PR from `develop` to `main` and enables auto-merge. The same workflow can also be run manually with `workflow_dispatch` when a promotion PR needs to be recreated.
5. When the promotion PR passes, it merges into `main`.
6. A push to `main` triggers the sync workflow back into `develop`.

## Hotfix Flow

Use this only for urgent production fixes.

1. Create a branch from `main`:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b hotfix/short-description
   ```
2. Open the pull request into `main`.
3. After merge, let the sync workflow bring the fix back to `develop`.

## Guardrails

- PRs into `main` are expected to come from `develop` or `hotfix/*`.
- PRs into `develop` should come from topic branches such as `feature/*`, `fix/*`, `docs/*`, `chore/*`, `refactor/*`, `test/*`, `ci/*`, `perf/*`, or `hotfix/*`.
- The repository enforces the `main` promotion path in `.github/workflows/enforce-promotion-path.yml`.
- You can validate the rule locally with `./scripts/check-branch-flow.sh --base main --head develop`.

## Operational Checks

Before touching devcontainer automation or release plumbing, run:

```bash
make doctor-devcontainer
python3 scripts/devcontainer-metadata.py
python3 scripts/devcontainer-diff.py
```
