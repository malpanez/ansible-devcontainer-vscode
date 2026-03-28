# Phase 1: CI Stability - Research

**Researched:** 2026-03-25
**Domain:** GitHub Actions CI, pytest, pytest-ansible, Ansible playbook testing
**Confidence:** HIGH

## Summary

This is a brownfield CI stabilization phase. The codebase has undergone ~10 recent fix commits targeting specific CI failures. Many of those fixes are now in place but have not been validated by 3 consecutive successful CI runs. The phase goal is to confirm the fixes are complete, identify any remaining gaps, and add a compatibility matrix so future regressions are detected early.

The core conflict is that `pytest-ansible` 24.x registers argparse arguments that conflict with pytest's own argument parser when the plugin is active. The fix (`-p no:pytest-ansible`) is already in both `pyproject.toml` and `.github/workflows/ci.yml`. The `regex_search` Jinja2 filter incompatibility (returning `None` vs a truthy match object in newer Ansible/Jinja2 versions) has also been patched in `playbooks/test-environment.yml`. The `test-playbooks` job no longer uses `--check` mode so the playbook actually executes.

The primary remaining risk is that none of these fixes has been proven by 3 consecutive green CI runs. There may also be secondary issues: the `unit-tests` job does not use a Python version matrix, the molecule job only runs on `main` (not `develop`), and the `test-playbooks` job has no `continue-on-error` guard, meaning a single environment discrepancy in CI could still block the whole pipeline.

**Primary recommendation:** Verify all fixes are consistent between `pyproject.toml` and `ci.yml`, remove any remaining `continue-on-error: true` on the `unit-tests` run step, add a compatibility matrix for Python versions, and trigger 3 consecutive workflow runs to confirm stability.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CI-01 | All pytest tests pass consistently without flakiness | pytest-ansible plugin conflict fix is in place; needs verification by 3 clean runs |
| CI-02 | No pytest-ansible vs argparse conflicts in any environment | `-p no:pytest-ansible` flag added to both pyproject.toml and ci.yml; plugin name was previously wrong (underscore vs hyphen) — now corrected |
| CI-03 | molecule/testinfra tests pass in CI (not just locally) | molecule job currently runs only on `main` branch; to fix CI-03 for `develop`, the trigger condition may need adjustment |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | >=8.0.0 | Python test runner | Project dependency in pyproject.toml |
| pytest-ansible | >=24.1.0,<24.7.0 | Ansible integration for pytest | Pinned to avoid argparse conflict in 24.7+ |
| pytest-cov | >=4.1.0 | Coverage measurement | Already in use |
| pytest-testinfra | >=10.1.0 | Container/infra testing | Already in use for molecule |
| molecule | >=6.0.0,<26.0.0 | Role testing framework | Already configured |
| molecule-plugins[docker] | >=23.5.0,<26.0.0 | Docker driver for molecule | Already configured |
| uv | 0.10.10 (installed) | Fast Python package management | Project standard (replaces pip) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| geerlingguy/docker-debian12-ansible | latest | Molecule test image | molecule job on develop/main |
| geerlingguy/docker-ubuntu2204-ansible | latest | Molecule test image | molecule job cross-distro testing |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `-p no:pytest-ansible` flag | Uninstalling pytest-ansible | Flag approach is reversible; uninstalling would break future ansible-specific tests |
| `continue-on-error: true` on unit-tests | Removing the flag and fixing tests | `continue-on-error` hides failures; better to fix root cause |

**Installation:**
```bash
uv pip install --system -e .
ansible-galaxy collection install -r requirements.yml
```

**Version verification:** Package versions verified from `pyproject.toml` and `uv.lock` in the repository. pytest-ansible is pinned to `>=24.1.0,<24.7.0` to avoid the argparse conflict introduced in 24.7.0.

## Architecture Patterns

### Recommended Project Structure
```
.github/workflows/
├── ci.yml              # Main CI: test-playbooks, unit-tests, ansible-test, molecule
tests/
├── test_devcontainer_tools.py   # pytest tests for Python scripts
├── container-structure/         # container-structure-test YAML specs
playbooks/
├── test-environment.yml         # Ansible playbook run by test-playbooks CI job
pyproject.toml                   # pytest config (addopts, markers, coverage)
```

### Pattern 1: Disabling pytest-ansible Plugin

**What:** pytest-ansible registers CLI arguments that conflict with pytest's own argparse when both the `ansible` and `pytest-ansible` entry points are active.

**When to use:** Any project that installs `pytest-ansible` but does not need ansible-specific pytest fixtures (e.g., uses molecule separately).

**How it works:** pytest loads plugins by entry point name. The correct name to disable is `pytest-ansible` (hyphen), NOT `pytest_ansible` (underscore). The plugin can be disabled in two places:

```toml
# pyproject.toml — applies to all local pytest runs
[tool.pytest.ini_options]
addopts = [
  "-p no:pytest-ansible",
  ...
]
```

```yaml
# ci.yml — must match pyproject.toml; redundant but ensures CI env alignment
uv run pytest tests/ \
  -p no:ansible \
  -p no:pytest-ansible
```

**Source:** Verified by git history — `c1a0e15` fixed the underscore/hyphen typo in both files.

### Pattern 2: Ansible regex_search Compatibility

**What:** In Ansible >=2.18 / Jinja2 >=3.1, `regex_search()` returns `None` on no match instead of an empty string. Using the result directly in an `assert that:` condition evaluates `None` as falsy but does NOT raise an error — the assertion silently passes even when it should fail. The correct pattern is explicit `is not none` check.

**When to use:** Any `assert that:` or conditional using `regex_search()`.

**Example:**
```yaml
# WRONG — passes silently if regex_search returns None (no match found)
- ansible.builtin.assert:
    that:
      - some_var | regex_search('^pattern')

# CORRECT — explicit None check
- ansible.builtin.assert:
    that:
      - some_var | regex_search('^pattern') is not none
```

**Source:** Verified by `cde52fc` which fixed 4 occurrences in `playbooks/test-environment.yml`. The current file is patched correctly.

### Pattern 3: Compatibility Matrix for CI

**What:** A GitHub Actions strategy matrix that runs tests across multiple Python versions (and optionally Ansible versions) to detect regressions early.

**When to use:** For any job that needs to verify library compatibility across versions.

**Example:**
```yaml
strategy:
  fail-fast: false
  matrix:
    python-version: ["3.11", "3.12", "3.13"]
steps:
  - uses: actions/setup-python@...
    with:
      python-version: ${{ matrix.python-version }}
```

**Note:** Currently the `unit-tests` job uses only `PYTHON_VERSION: "3.12"` (hard-coded env var). There is no compatibility matrix.

### Pattern 4: Molecule Trigger Scope

**What:** The `molecule` job currently only runs when `github.ref == 'refs/heads/main'`. This means Ansible role tests never run on `develop`, which is the primary development branch.

**Current condition:**
```yaml
if: |
  needs.changes.outputs.ansible == 'true' &&
  (github.ref == 'refs/heads/main' || github.event_name == 'workflow_dispatch')
```

**Risk:** A breaking change to an Ansible role can be merged to `develop` and only detected when promoted to `main`. For CI-03 (molecule tests pass in CI), this trigger must include `develop`.

### Anti-Patterns to Avoid

- **`continue-on-error: true` on `unit-tests` run step:** The current `unit-tests` job does NOT have `continue-on-error: true` at the step level (it was removed in recent fixes). Do not re-add it — it hides test failures.
- **`-p no:pytest_ansible` (underscore):** The underscore form is silently ignored by pytest, meaning the plugin remains active. Always use hyphen: `-p no:pytest-ansible`.
- **`ansible-playbook ... --check` in CI test:** The `--check` mode skips tasks that create side effects, making the test pass trivially. The `test-environment.yml` playbook uses `connection: local` and only reads state — no side effects — so `--check` was incorrectly preventing actual execution. It has been removed.
- **Relying on `|| echo "::warning::..."` to suppress test failures:** The `unit-tests` job previously had `|| echo "::warning::Some pytest tests failed"` which caused the step to always exit 0 even on test failures. This was removed in commit `1dc0401`. Do not re-introduce this pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Plugin conflict detection | Custom argparse inspection | `-p no:pytest-ansible` flag | Already solved by pytest plugin system |
| Cross-version compatibility testing | Multiple separate workflow files | GitHub Actions strategy matrix | Native feature, less duplication |
| Ansible version validation | Shell script subprocess calls | `ansible_version` magic variable | Subprocess approach breaks in `connection: local` (no ssh) |

**Key insight:** The `ansible_version` magic variable is populated by Ansible itself before any task runs. Using `ansible.builtin.command: ansible --version` in a `connection: local` playbook adds unnecessary process overhead and can fail if PATH is not set correctly in the CI environment.

## Common Pitfalls

### Pitfall 1: pytest-ansible Plugin Name (Underscore vs Hyphen)
**What goes wrong:** Tests appear to run correctly but the plugin is still active, causing argparse conflicts on certain pytest argument combinations.
**Why it happens:** pytest accepts both forms syntactically but only the hyphen form correctly identifies the entry point registered by `pytest-ansible`.
**How to avoid:** Always use `-p no:pytest-ansible` (hyphen). Confirmed correct in current `pyproject.toml` and `ci.yml` after commit `c1a0e15`.
**Warning signs:** pytest error like `error: unrecognized arguments: --ansible-*` or `argparse.ArgumentError`.

### Pitfall 2: regex_search Returns None in Newer Ansible
**What goes wrong:** `assert that: - var | regex_search('pattern')` evaluates `None` as falsy, causing assertion failure. OR in some Jinja2 versions it raises a TypeError when None is used in a boolean context.
**Why it happens:** Ansible 2.18+ changed `regex_search()` to return `None` on no match (previously returned empty string). The `is not none` check is required for unambiguous behavior.
**How to avoid:** Always use `regex_search(...) is not none`. Already fixed in `playbooks/test-environment.yml`.
**Warning signs:** `TypeError: 'NoneType' cannot be interpreted as bool` in playbook output.

### Pitfall 3: ci-success Gates on Skipped Jobs
**What goes wrong:** A job in the `needs` list of `ci-success` is skipped because its path filter didn't match. The `ci-success` job sees `result == "skipped"` and must not treat that as failure.
**Why it happens:** GitHub Actions reports `skipped` for jobs that didn't run due to `if:` conditions. The current ci-success logic uses `select(.value.result == "failure")` which correctly ignores skipped jobs.
**How to avoid:** Current logic is correct. Do not change `== "failure"` to `!= "success"` — that would break skipped jobs.
**Warning signs:** CI red on a commit that touched only `scripts/` (triggering `script-lint` but not `unit-tests`).

### Pitfall 4: molecule Only Runs on main
**What goes wrong:** Ansible role bugs in develop are only caught after promotion to main, defeating the purpose of CI on the development branch.
**Why it happens:** The `molecule` job has `github.ref == 'refs/heads/main'` condition. This is overly restrictive.
**How to avoid:** Add `|| github.ref == 'refs/heads/develop'` to the molecule trigger condition.
**Warning signs:** Ansible role test failures discovered only on main branch promotion.

### Pitfall 5: uv install failure due to missing compiler
**What goes wrong:** `uv pip install --system -e .` fails to build `ruamel-yaml-clibz` because `cc` (C compiler) is not present in the devcontainer environment.
**Why it happens:** The `ansible-navigator` dependency chain pulls in `ruamel-yaml-clibz` which requires a C compiler. In CI (Ubuntu) this is typically available. In some local environments it may not be.
**How to avoid:** In CI, the `ubuntu-latest` runner has `gcc` installed. For local dev, the devcontainer has `build-essential`. No action needed for CI, but local failures should fall back to `--no-build-isolation` or pre-built wheels.
**Warning signs:** `error: command 'cc' failed: No such file or directory` during `uv pip install`.

## Code Examples

Verified patterns from repository source:

### Correct pytest-ansible Disable (pyproject.toml)
```toml
# /workspace/pyproject.toml — current correct state
[tool.pytest.ini_options]
addopts = [
  "--verbose",
  "--tb=short",
  "--strict-markers",
  "-p no:pytest-ansible",   # hyphen, not underscore
  "--cov=roles",
  "--cov=playbooks",
  "--cov=scripts",
  "--cov-report=html:htmlcov",
  "--cov-report=xml:coverage.xml",
  "--cov-report=term-missing:skip-covered",
  "--cov-branch",
]
```

### Correct pytest-ansible Disable (ci.yml)
```yaml
# /workspace/.github/workflows/ci.yml — current correct state
- name: Run pytest with coverage
  run: |
    if [ -d "tests" ] && [ -n "$(ls -A tests/*.py 2>/dev/null)" ]; then
      uv run pytest tests/ \
        --verbose \
        --tb=short \
        --maxfail=5 \
        --cov=roles \
        --cov=playbooks \
        --cov=scripts \
        --cov-report=xml:coverage.xml \
        --cov-report=html:htmlcov \
        --cov-report=term-missing \
        -p no:ansible \
        -p no:pytest-ansible
    else
      echo "::notice::No Python tests found, skipping"
    fi
```

### Compatibility Matrix Pattern (to be added)
```yaml
unit-tests:
  strategy:
    fail-fast: false
    matrix:
      python-version: ["3.11", "3.12", "3.13"]
  steps:
    - uses: actions/setup-python@...
      with:
        python-version: ${{ matrix.python-version }}
```

### Molecule Trigger Fix (to be added)
```yaml
molecule:
  if: |
    needs.changes.outputs.ansible == 'true' &&
    (github.ref == 'refs/heads/main' ||
     github.ref == 'refs/heads/develop' ||
     github.event_name == 'workflow_dispatch')
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `ansible --version` subprocess in connection:local playbook | `ansible_version` magic variable | commit `76f92c2` | Eliminates PATH dependency, faster |
| `regex_search('pattern')` bare in assert | `regex_search('pattern') is not none` | commit `cde52fc` | Compatible with Ansible >=2.18 |
| `-p no:pytest_ansible` (underscore) | `-p no:pytest-ansible` (hyphen) | commit `c1a0e15` | Plugin actually disabled |
| `--check` on test-environment.yml | No `--check` (real execution) | commit `b393d20` | Tests actually validate state |
| `\|\| echo "::warning::..."` on pytest | Removed (pytest failure = step failure) | commit `1dc0401` | Test failures actually fail CI |
| Coverage `--cov-fail-under=95` | Removed | commit `1dc0401` | Scripts tested via subprocess can't report coverage |

**Deprecated/outdated:**
- `pytest_ansible` (underscore) in `-p no:` argument: silently ignored, use hyphen form
- `--check` mode for connection:local playbooks that only read state: masks test effectiveness

## Open Questions

1. **Has the full CI pipeline run green 3 consecutive times since the recent fixes?**
   - What we know: All individual fixes are in place as of commit `1dc0401` (2026-03-25)
   - What's unclear: Whether there are any remaining undiscovered failures in edge cases (e.g., path filter not triggering `unit-tests` on non-Python commits)
   - Recommendation: Trigger 3 manual `workflow_dispatch` runs or make 3 commits that touch Python files and verify all required jobs pass

2. **Should the compatibility matrix cover Python 3.11 and 3.13 in addition to 3.12?**
   - What we know: `pyproject.toml` requires `python>=3.12`. Adding 3.13 would catch forward-compatibility issues. 3.11 would be unnecessary given the `>=3.12` constraint.
   - What's unclear: Whether any dependencies (especially `ansible-navigator`) support Python 3.13 yet
   - Recommendation: Add 3.12 + 3.13 matrix for forward compatibility detection; skip 3.11

3. **Should molecule run on develop as well as main?**
   - What we know: CI-03 requirement says molecule/testinfra tests must pass in CI. Currently they only run on main.
   - What's unclear: Whether the develop branch has had molecule failures that this restriction was intended to avoid
   - Recommendation: Enable molecule on develop branch (add `|| github.ref == 'refs/heads/develop'`) — the `fail-fast: false` strategy already handles partial failures gracefully

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | unit-tests, test-playbooks | ✓ | 3.12.x (via setup-python) | — |
| uv | all Python jobs | ✓ | 0.10.10 (local devcontainer) | pip (slower) |
| Ansible | test-playbooks, molecule | ✓ | installed via `uv pip install -e .` | — |
| molecule | molecule job | ✓ | >=6.0.0 (in pyproject.toml deps) | — |
| Docker | molecule (docker driver) | ✓ | available on ubuntu-latest runner | — |
| geerlingguy docker images | molecule test | ✓ | pulled at runtime | — |
| jq | ci-success result parsing | ✓ | pre-installed on ubuntu-latest | — |

**Missing dependencies with no fallback:** None identified.

**Missing dependencies with fallback:** None identified.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `/workspace/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run pytest tests/ -p no:ansible -p no:pytest-ansible -x -q` |
| Full suite command | `uv run pytest tests/ -p no:ansible -p no:pytest-ansible --tb=short` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CI-01 | pytest tests pass without flakiness | unit | `uv run pytest tests/ -p no:ansible -p no:pytest-ansible --tb=short` | ✅ |
| CI-02 | No pytest-ansible argparse conflict | smoke | `uv run pytest tests/ -p no:pytest-ansible --collect-only` (exits 0) | ✅ (via pyproject.toml) |
| CI-03 | molecule tests pass in CI | integration | `molecule test --scenario-name default` (triggered by ci.yml) | ✅ (molecule job in ci.yml) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -p no:ansible -p no:pytest-ansible -x -q`
- **Per wave merge:** Full pytest suite
- **Phase gate:** Full CI pipeline green 3 consecutive times before marking complete

### Wave 0 Gaps
None — existing test infrastructure covers all phase requirements. The gaps are in CI configuration, not test files.

## Sources

### Primary (HIGH confidence)
- `/workspace/pyproject.toml` — pytest configuration, dependency versions
- `/workspace/.github/workflows/ci.yml` — CI pipeline definition
- `/workspace/playbooks/test-environment.yml` — Ansible test playbook (patched)
- `git log --oneline -20` — commit history showing all recent fixes

### Secondary (MEDIUM confidence)
- Git diff of individual fix commits (c1a0e15, cde52fc, b393d20, 76f92c2, 1dc0401) — verified exact changes made
- `/workspace/.planning/PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md` — project context and requirements

### Tertiary (LOW confidence)
- None required — all findings are directly from codebase inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified from pyproject.toml and installed toolchain
- Architecture: HIGH — verified from actual workflow file and git history
- Pitfalls: HIGH — all pitfalls documented from actual commit history (not speculation)

**Research date:** 2026-03-25
**Valid until:** 2026-04-24 (stable ecosystem, 30-day window)

---

## RESEARCH COMPLETE
