---
description: "Run the full test suite (pytest + molecule + ansible-lint) and fix any failures"
---

Run the test suite for this infrastructure devcontainer project and fix all failures before reporting.

## Execution Order

1. **YAML lint** — `uv run yamllint . -c .yamllint`
   - Fix all violations before proceeding

2. **Ansible lint** (if roles or playbooks changed) — `uv run ansible-lint roles/ playbooks/`
   - Fix rule violations (use FQCN, add `name:`, set `mode:` on file tasks)

3. **Pytest suite** — `uv run pytest tests/ -v --cov --cov-report=term-missing`
   - Coverage must stay ≥ 95 %
   - Fix each failure individually and re-run before moving to the next

4. **Molecule** (if a role was modified) — `uv run molecule test -s <scenario>`
   - Run `uv run molecule converge && uv run molecule verify` for faster iteration
   - Fix the role implementation or the assertions, not both simultaneously

5. **Pre-commit** — `uvx pre-commit run --all-files`
   - This catches anything missed by the steps above

## Fix Strategy

- Fix one layer at a time (YAML → lint → pytest → molecule)
- For each failure: read the error, identify root cause, fix, re-run immediately
- Never skip a layer — downstream tests may mask upstream issues
- If coverage drops below 95 %: write testinfra assertions or pytest tests for the uncovered path
- If molecule `verify` fails: inspect the test container with `uv run molecule login`

Report when **all** layers pass cleanly.
