# Secrets & Credential Management

Keeping secrets out of the repository is non-negotiable. The workflows here
expect credentials to be injected at runtime—never hard-coded in Terraform
files, Ansible variables, or Git history.

## Terraform (Proxmox)

- **Environment variables** – Export variables with the `TF_VAR_` prefix (e.g.
  `export TF_VAR_pm_token_secret=...`) so Terraform picks them up automatically.
- **Terraform Cloud/CLI Config** – Use `~/.terraform.d/credentials.tfrc.json`
  when authenticating to Terraform Cloud or private registries.
- **Terragrunt** – If you layer Terragrunt on top, prefer `inputs` merged from
  encrypted files (e.g. `sops` or `ansible-vault`) instead of plain `.hcl`.
- **Proxmox API tokens** – Create tokens with the minimal privileges required.
  Store the secret in a local password manager or secret backend (1Password,
  Bitwarden, Azure Key Vault, etc.). Do **not** commit `*.auto.tfvars` that
  contain real credentials—use the provided example file as reference only.

## Ansible

- Keep inventory secrets (vault passwords, API keys) in `group_vars` or
  `host_vars` files encrypted via `ansible-vault`.
- The repository ships a `.secrets.baseline` for `detect-secrets`; run
  `pre-commit run --all-files` before every commit to prevent accidental leaks.

## GitHub Actions

- Define Terraform/Proxmox secrets as repository or organization secrets (e.g.
  `TF_PM_TOKEN_ID`, `TF_PM_TOKEN_SECRET`). Reference them in workflows via
  `${{ secrets.NAME }}`.
- Restrict who can read or rotate GitHub secrets. Rotate them periodically and
  audit workflow access.

## Dev Container

- When you need credentials inside the container, prefer mounting
  `~/.config/terraform.d/credentials.tfrc.json` or using environment variables
  via `.devcontainer/devcontainer.json` `"remoteEnv"` entries. Avoid writing
  secrets into the repo’s `.vscode/settings.json`.

## Recommended Tools

- [`sops`](https://github.com/mozilla/sops) or [`age`](https://github.com/FiloSottile/age`)
  for encrypting YAML/HCL snippets.
- Password managers with CLI integration (e.g. `op`, `bw`, `pass`) to inject
  secrets directly into Terraform or Ansible runs.
- Terraform Cloud or Vault for managing provider credentials centrally.

Treat every secret as disposable—rotate aggressively whenever you suspect
exposure or after sharing access with a new collaborator.
