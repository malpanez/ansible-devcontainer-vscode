#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
MODULE_DIR="${REPO_ROOT}/infrastructure/proxmox_lab"

if [[ ! -d "${MODULE_DIR}" ]]; then
  echo "Terraform scenario skipped: ${MODULE_DIR} not found." >&2
  exit 0
fi

if ! command -v terraform >/dev/null 2>&1; then
  echo "Terraform is required but not found on PATH." >&2
  exit 1
fi

cd "${MODULE_DIR}"

export TF_IN_AUTOMATION=1
export TF_CLI_ARGS="-no-color"
export TF_CLI_ARGS_init="-backend=false -input=false"

existing_lock=false
if [[ -f .terraform.lock.hcl ]]; then
  existing_lock=true
fi

cleanup() {
  rm -rf .terraform
  if [[ "${existing_lock}" == "false" ]]; then
    rm -f .terraform.lock.hcl
  fi
}
trap cleanup EXIT

echo "==> terraform fmt -check"
terraform fmt -check

if [[ ! -d .terraform ]]; then
  echo "==> terraform init (backend disabled)"
  terraform init >/dev/null
fi

echo "==> terraform validate"
terraform validate

echo "Terraform Proxmox scenario completed successfully."
