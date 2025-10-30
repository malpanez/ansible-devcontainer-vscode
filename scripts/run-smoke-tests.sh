#!/usr/bin/env bash
set -euo pipefail

# Run the environment smoke checks against the local inventory.
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

cd "${repo_root}"
ansible-playbook playbooks/test-environment.yml "$@"
