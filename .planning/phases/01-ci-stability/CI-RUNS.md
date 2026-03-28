# CI Stability Evidence — Phase 1

| Run | ID          | SHA        | Timestamp            | Result | Jobs active (non-skipped)                                       | Molecule ran? |
|-----|-------------|------------|----------------------|--------|------------------------------------------------------------------|---------------|
| 1   | 23537166633 | b79e2679   | 2026-03-25T10:48:14Z | green  | Detect Changes, Ansible Test, Test Playbooks, CI Success         | skipped (no ansible-path changes in commit) |
| 2   | 23568984872 | 98611218   | 2026-03-25T23:15:08Z | green  | Detect Changes, Ansible Test, Test Playbooks, CI Success         | skipped (no ansible-path changes in commit) |
| 3   | 23569649930 | 98c5b346   | 2026-03-25T23:35:51Z | green  | Detect Changes, Ansible Test, Test Playbooks, CI Success         | skipped (no ansible-path changes in commit) |

All runs concluded with `conclusion: success` and the `CI Success` gate job passed in every case.

## Notes

### Path-filter behaviour (expected, not a defect)

The CI pipeline uses `dorny/paths-filter` to gate jobs. Each of the 3 runs above was triggered by a commit that only touched CI config files (`.github/workflows/ci.yml`, playbooks, tests) — not ansible role/playbook source paths. Because the Molecule job is conditioned on ansible-path changes, it was correctly skipped.

The molecule trigger was **added for the develop branch** by Plan 01-01 (commit `54638c8`). A future commit touching `roles/`, `playbooks/`, or `molecule/` paths on develop will exercise the Molecule job. That commit (54638c8) itself was made before the 3 evidence runs above and pushed the condition into the workflow file.

### Python Unit Tests skipped

Python Unit Tests also uses path filtering (Python scripts / test files). Since the commits above modified CI config files only, the matrix job (3.11 + 3.12) was skipped in each run. This is correct behaviour. The matrix definition was added by commit `1c44d63` in Plan 01-01.

### No argparse conflicts observed

All runs used `pytest -p no:pytest-ansible` (corrected from `pytest_ansible` in commit `9861121`). No pytest-ansible argparse errors appear in any of the 3 runs.

### Ansible Test and Test Playbooks: green in all 3 runs

- `Ansible Test` — runs `ansible-test` (sanity + units); green across all 3.
- `Test Playbooks` — runs the test playbook using `ansible_version` magic variable (not subprocess binary call, fixed in earlier commits); green across all 3.

### Links

- Run 1: https://github.com/malpanez/ansible-devcontainer-vscode/actions/runs/23537166633
- Run 2: https://github.com/malpanez/ansible-devcontainer-vscode/actions/runs/23568984872
- Run 3: https://github.com/malpanez/ansible-devcontainer-vscode/actions/runs/23569649930
