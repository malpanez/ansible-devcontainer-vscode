---
phase: 01-ci-stability
plan: "01"
subsystem: infra
tags: [github-actions, ci, molecule, pytest, python-matrix]

# Dependency graph
requires: []
provides:
  - molecule job fires on push to develop (ansible path changes)
  - scenario-tests job fires on push to develop
  - unit-tests runs as a 2-leg Python 3.11/3.12 matrix
affects:
  - 01-02-PLAN.md  # green run verification depends on these fixes being active

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Branch gate pattern: if conditions include both main and develop for jobs that should run on both"
    - "Python compat matrix pattern: strategy.matrix.python-version for multi-version unit-test runs"

key-files:
  created: []
  modified:
    - .github/workflows/ci.yml

key-decisions:
  - "Add refs/heads/develop to molecule and scenario-tests if conditions so develop commits exercise full test surface"
  - "Use matrix.python-version (not env.PYTHON_VERSION) in unit-tests to enable 3.11/3.12 matrix legs"
  - "Retain env.PYTHON_VERSION global for other jobs that still reference it"

patterns-established:
  - "Branch gate pattern: always include both main and develop in branch-gated job if conditions"

requirements-completed: [CI-02, CI-03]

# Metrics
duration: 3min
completed: 2026-03-26
---

# Phase 1 Plan 01: Fix molecule trigger (develop) and add Python compat matrix to unit-tests

**Molecule and scenario-tests jobs extended to fire on develop pushes; unit-tests converted to 2-leg Python 3.11/3.12 matrix for compat regression detection**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-26T07:45:21Z
- **Completed:** 2026-03-26T07:48:21Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- molecule job `if` condition now includes `refs/heads/develop` — any develop commit touching ansible files triggers molecule tests (satisfies CI-03)
- scenario-tests job `if` condition now includes `refs/heads/develop` — consistent gate with molecule
- unit-tests job converted from hardcoded `env.PYTHON_VERSION` to a `strategy.matrix` with `["3.11", "3.12"]` (satisfies CI-02)
- YAML validated successfully post-edits

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix molecule job trigger to include develop branch** - `54638c8` (fix)
2. **Task 2: Add Python version matrix to unit-tests job** - `1c44d63` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `.github/workflows/ci.yml` - Two structural fixes: develop branch gate added to molecule and scenario-tests; Python 3.11/3.12 matrix added to unit-tests

## Decisions Made

- Retained `env.PYTHON_VERSION` global — it is still referenced by test-playbooks, devcontainer-state, ansible-test, and molecule jobs. Only unit-tests was migrated to matrix variable.
- `fail-fast: false` added to unit-tests matrix so both Python versions always run and report independently.
- No change to `ci-success` needs list — GitHub waits for ALL matrix legs of a job automatically.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `python3` and `python` commands not available in devcontainer shell — used `uv run --no-project --with pyyaml python` for YAML validation instead. Validation passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CI pipeline changes are committed and pushed to develop
- 01-02-PLAN.md (verify 3 consecutive green CI runs) can now proceed
- Molecule will run on next develop push touching ansible files

---
*Phase: 01-ci-stability*
*Completed: 2026-03-26*
