#!/usr/bin/env bash
set -euo pipefail

for name in \
  AWS_REGION TF_STATE_BUCKET EKS_CLUSTER_NAME \
  DB_NAME DB_USERNAME DB_PASSWORD \
  OS_DATABASE OS_DATABASE_USERNAME OS_DB_PASSWORD \
  BILLING_DATABASE BILLING_DATABASE_USERNAME BILLING_DB_PASSWORD; do
  if [[ -z "${!name:-}" ]]; then
    printf 'Missing required configuration: %s\n' "$name" >&2
    exit 2
  fi
done

account_id="$(
  AWS_PAGER='' aws --no-cli-pager --region "$AWS_REGION" \
    sts get-caller-identity --query Account --output text
)"

if ! AWS_PAGER='' aws --no-cli-pager --region "$AWS_REGION" \
  s3api head-bucket --bucket "$TF_STATE_BUCKET" >/dev/null 2>&1; then
  printf 'Terraform state bucket is missing or inaccessible: %s\n' \
    "$TF_STATE_BUCKET" >&2
  exit 3
fi

vpc_count="$(
  AWS_PAGER='' aws --no-cli-pager --region "$AWS_REGION" ec2 describe-vpcs \
    --filters Name=tag:Name,Values=sandbox-vpc Name=tag:Environment,Values=sandbox \
    --query 'length(Vpcs)' --output text
)"
if [[ "$vpc_count" == "0" ]]; then
  printf 'Shared sandbox VPC was not found in %s\n' "$AWS_REGION" >&2
  exit 4
fi

printf 'Database sandbox prerequisites validated for account %s in %s\n' \
  "$account_id" "$AWS_REGION"
