#!/usr/bin/env bash
set -euo pipefail

repository_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
terraform_dir="${repository_dir}/terraform"
tfvars_file="${TFVARS_FILE:-${terraform_dir}/environments/sandbox/terraform.tfvars}"

if [[ ! -f "${tfvars_file}" ]]; then
  echo "tfvars file not found: ${tfvars_file}" >&2
  exit 1
fi

: "${TF_STATE_BUCKET:?TF_STATE_BUCKET is required}"
: "${AWS_REGION:?AWS_REGION is required}"

terraform -chdir="${terraform_dir}" init -input=false \
  -backend-config="bucket=${TF_STATE_BUCKET}" \
  -backend-config="key=database/terraform.tfstate" \
  -backend-config="region=${AWS_REGION}" \
  -backend-config="use_lockfile=true"
terraform -chdir="${terraform_dir}" plan -var-file="${tfvars_file}" -out=tfplan "$@"
