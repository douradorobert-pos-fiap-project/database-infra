#!/usr/bin/env bash
set -euo pipefail

repository_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
terraform_dir="${repository_dir}/terraform"
tfvars_file="${TFVARS_FILE:-${terraform_dir}/environments/sandbox/terraform.tfvars}"

if [[ ! -f "${tfvars_file}" ]]; then
  echo "tfvars file not found: ${tfvars_file}" >&2
  exit 1
fi

terraform -chdir="${terraform_dir}" init
terraform -chdir="${terraform_dir}" plan -var-file="${tfvars_file}" -out=tfplan "$@"
