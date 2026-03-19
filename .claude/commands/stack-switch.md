---
description: "Switch the active devcontainer stack (ansible|terraform|golang|latex) and verify it"
---

Switch the active devcontainer stack and verify the result. Always run the doctor check after switching.

## Available Stacks

| Stack       | Description                      |
| ----------- | -------------------------------- |
| `ansible`   | Ansible + molecule + collections |
| `terraform` | Terraform + Terragrunt + tflint  |
| `golang`    | Go toolchain + golangci-lint     |
| `latex`     | Tectonic LaTeX engine            |

## Switch Process

```sh
# Switch to the requested stack
make switch-<stack>

# Verify no drift after switch
make doctor-devcontainer

# Validate the new devcontainer.json and Dockerfile
jq . .devcontainer/devcontainer.json > /dev/null && echo "devcontainer.json: valid"
hadolint .devcontainer/Dockerfile

# Confirm metadata updated
cat .devcontainer/.template-metadata.json
```

## After Switching

Inform the user to reopen the container in VS Code:

- **F1 → Dev Containers: Reopen in Container** (rebuilds with the new stack)

Or manually build to verify:

```sh
make build
```

## Troubleshooting

If the switch leaves `.devcontainer/` in a broken state:

```sh
# Re-run the switch script directly
bash scripts/use-devcontainer.sh <stack>

# Check for drift
bash scripts/doctor-devcontainer.sh

# Compare with source stack
python3 scripts/devcontainer-diff.py
```
