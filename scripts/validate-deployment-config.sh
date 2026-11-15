#!/usr/bin/env bash
set -euo pipefail
set +x

for name in \
  AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN \
  AWS_REGION TF_STATE_BUCKET EKS_CLUSTER_NAME \
  DB_NAME DB_USERNAME DB_PASSWORD \
  OS_DATABASE OS_DATABASE_USERNAME OS_DB_PASSWORD \
  BILLING_DATABASE BILLING_DATABASE_USERNAME BILLING_DB_PASSWORD; do
  if [[ -z "${!name:-}" ]]; then
    printf 'Missing required configuration: %s\n' "$name" >&2
    exit 2
  fi
done

printf 'Required database deployment configuration is present\n'
