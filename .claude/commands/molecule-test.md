---
description: "Run molecule tests for an Ansible role — full cycle or targeted scenario"
---

Run molecule tests for an Ansible role. Supports full cycle, fast iteration mode, and testinfra debugging.

## Usage

Specify the role and optionally the scenario. If no scenario is given, the `default` scenario runs.

**Arguments:** `<role-name> [scenario-name]`

## Execution

```sh
# Determine role and scenario from arguments
ROLE="${1:-}"
SCENARIO="${2:-default}"

if [ -z "$ROLE" ]; then
  echo "Usage: /molecule-test <role-name> [scenario-name]"
  echo ""
  echo "Available roles:"
  ls roles/
  echo ""
  echo "Available scenarios:"
  uv run molecule list
  exit 1
fi

cd "roles/$ROLE"

# Full test cycle
uv run molecule test -s "$SCENARIO"
```

## Iteration Mode (faster)

Use when developing — skips container destroy between runs:

```sh
cd roles/<role-name>
uv run molecule converge -s <scenario>   # Apply role
uv run molecule verify -s <scenario>     # Run testinfra assertions
# Inspect if needed:
uv run molecule login -s <scenario>      # Shell into test container
uv run molecule destroy -s <scenario>    # Cleanup
```

## Debugging Failed Tests

```sh
# See the full Ansible output
uv run molecule converge -s <scenario> -- -vvv

# Inspect the container state after converge
uv run molecule login -s <scenario>
# Inside container:
systemctl status <service>
cat /etc/my-config.yml
journalctl -u <service> --no-pager

# Run testinfra directly against the running container
uv run pytest molecule/<scenario>/tests/ -v -s --tb=long
```

## All Roles

Run the full matrix across all roles:

```sh
FAILED_ROLES=()
for role_dir in roles/*/; do
  role=$(basename "$role_dir")
  echo "=== Testing: $role ==="
  if ! (cd "$role_dir" && uv run molecule test); then
    FAILED_ROLES+=("$role")
  fi
done

if [ ${#FAILED_ROLES[@]} -gt 0 ]; then
  echo "FAILED: ${FAILED_ROLES[*]}"
else
  echo "All roles passed."
fi
```

## Report

Provide:

- Which scenarios ran and their pass/fail status
- For failures: which phase failed (create/converge/verify/destroy) and the error
- Testinfra assertion failures with the specific assertion and actual vs expected value
- Fix applied (if any) with a brief explanation
