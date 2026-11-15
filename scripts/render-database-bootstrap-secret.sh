#!/usr/bin/env bash
set -euo pipefail
set +x

for name in \
  RDS_ENDPOINT RDS_PORT DB_NAME DB_USERNAME DB_PASSWORD \
  OS_DATABASE OS_DATABASE_USERNAME OS_DB_PASSWORD \
  BILLING_DATABASE BILLING_DATABASE_USERNAME BILLING_DB_PASSWORD; do
  if [[ -z "${!name:-}" ]]; then
    printf 'Missing required bootstrap configuration: %s\n' "$name" >&2
    exit 2
  fi
done

repository_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
namespace="${K8S_NAMESPACE:-oficina}"

kubectl --namespace "$namespace" create configmap database-bootstrap-script \
  --from-file="bootstrap-logical-databases.sh=${repository_dir}/scripts/bootstrap-logical-databases.sh" \
  --dry-run=client -o yaml | kubectl apply -f - >/dev/null

kubectl --namespace "$namespace" create secret generic database-bootstrap-secrets \
  --from-literal="PGHOST=${RDS_ENDPOINT}" \
  --from-literal="PGPORT=${RDS_PORT}" \
  --from-literal="PGDATABASE=${DB_NAME}" \
  --from-literal="PGUSER=${DB_USERNAME}" \
  --from-literal="PGPASSWORD=${DB_PASSWORD}" \
  --from-literal="DB_PASSWORD=${DB_PASSWORD}" \
  --from-literal="OS_DATABASE=${OS_DATABASE}" \
  --from-literal="OS_DATABASE_USER=${OS_DATABASE_USERNAME}" \
  --from-literal="OS_DB_PASSWORD=${OS_DB_PASSWORD}" \
  --from-literal="OS_DATABASE_PASSWORD=${OS_DB_PASSWORD}" \
  --from-literal="BILLING_DATABASE=${BILLING_DATABASE}" \
  --from-literal="BILLING_DATABASE_USER=${BILLING_DATABASE_USERNAME}" \
  --from-literal="BILLING_DB_PASSWORD=${BILLING_DB_PASSWORD}" \
  --from-literal="BILLING_DATABASE_PASSWORD=${BILLING_DB_PASSWORD}" \
  --dry-run=client -o yaml | kubectl apply -f - >/dev/null

printf 'Database bootstrap ConfigMap and Secret synchronized in namespace %s\n' \
  "$namespace"
