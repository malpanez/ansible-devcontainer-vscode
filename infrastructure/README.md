# Infrastructure Baseline

This directory hosts Terraform configuration that complements the Dev Container stacks.
Use it as a starting point for declaring lab services (e.g. Proxmox VMs) so the
workspace and GitHub Actions stay in sync.

## Layout

- `proxmox_lab/` – Opinionated module for provisioning a handful of Proxmox VMs.
  It demonstrates how to structure variables, leverage Terragrunt (optional), and
  keep credentials outside of git.

> Add additional modules under `infrastructure/<name>` and the local validation
> script (`./scripts/run-terraform-tests.sh`) plus CI (`Terraform Checks` job)
> will pick them up automatically.

## Usage

1. Copy `proxmox_lab/example.tfvars` (created after running `terraform init`) to
   a secure location and tailor it to your hardware.
2. Export the required environment variables before running Terraform (see
   [Secrets & Credentials](../docs/SECRETS.md)).
3. Validate the configuration locally:

   ```bash
   ./scripts/run-terraform-tests.sh
   ```

4. From inside the Dev Container (Terraform stack recommended):

   ```bash
   cd infrastructure/proxmox_lab
   terraform init
   terraform plan -var-file="proxmox.auto.tfvars"
   ```

   > The repository's CI job runs `terraform init -backend=false` and `terraform
   > validate` on each module to ensure the syntax stays healthy.

## Provider versions

Terraform modules in this repository target:

- Terraform `1.7.x`
- Proxmox provider (`Telmate/proxmox`) `~> 3.0`

Pin alternate versions in `terraform { required_providers { … } }` blocks if
you maintain modules for other platforms.
