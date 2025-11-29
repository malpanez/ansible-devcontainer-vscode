---
name: DevContainer Issue
about: Report an issue specific to a devcontainer stack
title: '[STACK] '
labels: 'devcontainer'
assignees: 'malpanez'

---

## Stack

Which devcontainer is affected?
- [ ] Ansible (`devcontainer-ansible`)
- [ ] Terraform (`devcontainer-terraform`)
- [ ] Golang (`devcontainer-golang`)
- [ ] LaTeX (`devcontainer-latex`)

## Issue Type

- [ ] Container won't build
- [ ] Container won't start
- [ ] Tool missing or wrong version
- [ ] VS Code extension not working
- [ ] Performance issue
- [ ] Other

## Description

Clear description of the issue.

## Environment

- **Image**: [e.g., `ghcr.io/malpanez/devcontainer-ansible:latest`]
- **Host OS**: [e.g., Windows 11 + WSL2 Ubuntu 22.04]
- **Docker**: [e.g., Docker Desktop 24.0.6]
- **VS Code**: [e.g., 1.85.0]
- **Dev Containers ext**: [e.g., 0.320.0]

## Steps to Reproduce

1. Clone repo
2. Open in VS Code
3. Select stack: `./scripts/use-devcontainer.sh [stack]`
4. Reopen in container
5. Error occurs...

## Expected vs Actual

**Expected**: Container starts and all tools are available
**Actual**: [What happened]

## Logs

<details>
<summary>Dev Container log</summary>

```
Command Palette > Dev Containers: Show Log
Paste relevant output here
```
</details>

<details>
<summary>Docker/build output (if build fails)</summary>

```
docker build output here
```
</details>

## Diagnostic Info

Run in container (if it starts):
```bash
# Tool versions
terraform version
go version
python --version
ansible --version
tectonic --version

# Environment
env | grep -E '(UV_|TERRAFORM|ANSIBLE|TECTONIC)'
```

## Tried So Far

- [ ] Rebuilt container (Cmd+Shift+P > Rebuild Container)
- [ ] Cleared Docker cache (`docker system prune -a`)
- [ ] Checked [TROUBLESHOOTING.md](../../docs/TROUBLESHOOTING.md)
- [ ] Verified image is latest from GHCR

## Additional Context

Any other relevant information.
