# Terraform: Proxmox Homelab Scenario

This scenario shows how to use the Terraform devcontainer to iterate on the `infrastructure/proxmox_lab` modules, validate changes, and ship them to a Proxmox cluster.

## Prerequisites

- The Terraform devcontainer selected via `./scripts/use-devcontainer.sh terraform`.
- Proxmox API credentials exported as environment variables (or stored in a `.env` file mounted into the container).
- `infrastructure/proxmox_lab/terraform.tfvars` populated with your lab details.

## Workflow

1. **Open the repo in VS Code** and reopen in the Terraform devcontainer.
2. **Authenticate**:
   ```bash
   export PROXMOX_HOST=proxmox.local
   export PROXMOX_USERNAME=root@pam
   export PROXMOX_TOKEN_ID=terraform
   export PROXMOX_TOKEN_SECRET=...
   ```
3. **Install providers**:
   ```bash
   cd infrastructure/proxmox_lab
   terraform init
   ```
4. **Validate formatting and config** (CI mirrors these steps):
   ```bash
   terraform fmt -check
   terraform validate
   tflint --init && tflint
   checkov -d .
   ```
5. **Plan changes**:
   ```bash
   terraform plan -var-file=terraform.tfvars
   ```
6. **Apply when ready**:
   ```bash
   terraform apply -var-file=terraform.tfvars
   ```

> CI runs `scripts/scenarios/run-terraform-proxmox.sh` to make sure these steps stay healthy (fmt, init, validate).

## Smoke Test Checklist

- `terraform fmt -check` passes with no diffs.
- `terraform plan` yields the expected resource changes (or `No changes.`).
- `checkov` returns zero HIGH/CRITICAL findings (or documented justifications).

## Tips

- Use the precreated VS Code tasks (`Terraform: Plan`, `Terraform: Validate`) for quick iteration.
- The container ships Terragrunt as well; point `terragrunt.hcl` at the same workspace if you prefer Terragrunt workflows.
- Store sensitive credentials outside the repo—consider `direnv` or the VS Code secret manager to keep tokens out of history.
