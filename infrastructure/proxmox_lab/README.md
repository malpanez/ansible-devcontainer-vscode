# Proxmox Lab Module

Opinionated Terraform module for cloning VM templates on a Proxmox VE cluster.
It assumes you already maintain golden templates (e.g. Ubuntu 24.04 cloud-init)
and want reproducible service VMs for home lab tooling such as Pi-hole, Immich,
or SterlingPDF.

## Getting Started

1. Copy `proxmox.auto.tfvars.example` to `proxmox.auto.tfvars` (git ignored) and
   tweak the values to match your lab.
2. Export secrets as environment variables before running Terraform:

   ```bash
   export TF_VAR_pm_token_secret="$(pass proxmox/terraform-token)"
   export TF_VAR_pm_token_id="svc-terraform@pam!terraform"
   export TF_VAR_pm_api_url="https://proxmox.example:8006/api2/json"
   ```

3. Validate the module:

   ```bash
   terraform init
   terraform validate
   terraform plan -var-file="proxmox.auto.tfvars"
   ```

## Variables

Key inputs exposed by `variables.tf`:

- `virtual_machines` – list of VM definitions (name, node, template clone,
  CPU/memory/storage, network).
- `authorized_ssh_keys` – multi-line string of public keys injected via
  cloud-init (`ssh_authorized_keys`).
- `nameservers` / `search_domains` – optional DNS settings, handy for Pi-hole or
  split-horizon DNS.

Optional parameters control provider behaviour (timeout, TLS validation,
logging, etc.). Review `variables.tf` for the full catalogue.

## Extending

- Add additional disks or NICs by extending the `disks` and `network` blocks.
- Layer Ansible roles by pointing inventory hosts to the IPs returned in the
  `vm_summary` output.
- Create Terragrunt wrappers that set environment-specific defaults (`inputs`) and
  handle remote state if you expand beyond a single host.

> This module is intentionally lightweight—treat it as scaffolding and adapt it
> to your Proxmox conventions.
