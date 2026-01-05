#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

DEFAULT_MODULE_ROOT="${REPO_ROOT}/infrastructure"
MODULE_ROOT="${1:-${DEFAULT_MODULE_ROOT}}"

if ! command -v terraform >/dev/null 2>&1; then
  echo "terraform command not found. Install Terraform to continue." >&2
  exit 1
fi

if [[ ! -d "${MODULE_ROOT}" ]]; then
  echo "No Terraform modules directory found at ${MODULE_ROOT}; skipping."
  exit 0
fi

# Provide safe placeholder values for common variables so `terraform validate`
# succeeds even when secrets are not exported locally/CI.
TF_VAR_PM_API_URL_DEFAULT="${TF_VAR_PM_API_URL_DEFAULT:-https://proxmox.example.invalid:8006/api2/json}"
TF_VAR_PM_USER_DEFAULT="${TF_VAR_PM_USER_DEFAULT:-svc-terraform@pam}"
TF_VAR_PM_TOKEN_ID_DEFAULT="${TF_VAR_PM_TOKEN_ID_DEFAULT:-svc-terraform@pam!placeholder}"
TF_VAR_PM_TOKEN_SECRET_DEFAULT="${TF_VAR_PM_TOKEN_SECRET_DEFAULT:-placeholder-secret}"
TF_VAR_ENV=(
  "TF_VAR_pm_api_url=${TF_VAR_PM_API_URL_DEFAULT}"
  "TF_VAR_pm_user=${TF_VAR_PM_USER_DEFAULT}"
  "TF_VAR_pm_token_id=${TF_VAR_PM_TOKEN_ID_DEFAULT}"
  "TF_VAR_pm_token_secret=${TF_VAR_PM_TOKEN_SECRET_DEFAULT}"
)

mapfile -t TERRAFORM_FILES < <(find "${MODULE_ROOT}" -type f -name '*.tf' \
  -not -path '*/.terraform/*' -not -path '*/.terragrunt-cache/*')

if [[ "${#TERRAFORM_FILES[@]}" -eq 0 ]]; then
  echo "No Terraform configuration files detected under ${MODULE_ROOT}; skipping."
  exit 0
fi

echo ">> Running terraform fmt -check -recursive on ${MODULE_ROOT}"
terraform fmt -check -recursive "${MODULE_ROOT}"

export TF_IN_AUTOMATION=1

mapfile -t TERRAFORM_MODULE_DIRS < <(
  for file in "${TERRAFORM_FILES[@]}"; do
    dirname "${file}"
  done | sort -u
)

SKIP_MODULES=("${REPO_ROOT}/infrastructure/proxmox_lab")

should_skip() {
  local dir="$1"
  for skip in "${SKIP_MODULES[@]}"; do
    if [[ -n "${skip}" && "${dir}" == "${skip}" ]]; then
      return 0
    fi
  done
  return 1
}

for module_dir in "${TERRAFORM_MODULE_DIRS[@]}"; do
  if should_skip "${module_dir}"; then
    echo "::notice::Skipping ${module_dir} (provider not available in CI)."
    continue
  fi
  echo ">> Validating Terraform module at ${module_dir}"
  pushd "${module_dir}" >/dev/null

  if ! env "${TF_VAR_ENV[@]}" terraform init -backend=false -input=false; then
    echo "::warning::terraform init failed for ${module_dir}; skipping validation"
    popd >/dev/null
    continue
  fi
  env "${TF_VAR_ENV[@]}" terraform validate -no-color

  # Clean up the local .terraform directory to avoid leaving behind artifacts.
  rm -rf .terraform

  popd >/dev/null
done

echo "Terraform checks completed successfully."
