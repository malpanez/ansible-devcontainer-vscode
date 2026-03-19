---
description: "Run the full CI pipeline locally and fix all failures before pushing"
---

Simulate the complete CI pipeline locally. This is the required check before opening any PR. Fix all failures before reporting done.

## CI Pipeline Steps

```sh
# 1. Install / sync dependencies
uv sync

# 2. Pre-commit hooks (full suite)
uvx pre-commit run --all-files

# 3. YAML validation
make validate-yaml

# 4. Dockerfile validation
make validate-docker

# 5. Python tests with coverage
uv run pytest tests/ -v --cov --cov-report=term-missing --cov-fail-under=95

# 6. Security scan
make security

# 7. Doctor check (devcontainer drift)
make doctor-devcontainer

# Or run everything with a single command:
make ci-local
```

## Failure Protocol

For each failure:

1. Read the full error output
2. Identify whether it's a code bug, a test bug, or a configuration issue
3. Fix the root cause — never suppress or skip
4. Re-run the failing step to confirm the fix
5. Continue to the next step only after the current one is clean

## Coverage Enforcement

Coverage must stay ≥ **95 %**. If it drops:

- Identify uncovered lines: `uv run pytest tests/ --cov --cov-report=term-missing`
- Write the missing test — do not add `# pragma: no cover`

## Pre-Push Checklist

- [ ] All pre-commit hooks pass
- [ ] `make validate-yaml` passes
- [ ] `make validate-docker` passes
- [ ] `uv run pytest tests/ --cov` passes at ≥ 95 %
- [ ] `make security` passes (no HIGH/CRITICAL unaddressed)
- [ ] `make doctor-devcontainer` reports no drift
- [ ] Branch targets `develop` (not `main`)
- [ ] Commit messages follow conventional commits (`feat:`, `fix:`, `docs:`, etc.)
- [ ] No Co-Authored-By lines in commits
