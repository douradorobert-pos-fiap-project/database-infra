#!/usr/bin/env bash
set -euo pipefail

for identifier in "$OS_DATABASE" "$OS_DATABASE_USER" "$BILLING_DATABASE" "$BILLING_DATABASE_USER"; do
  if [[ ! "$identifier" =~ ^[a-z_][a-z0-9_]*$ ]]; then
    echo "Invalid PostgreSQL identifier" >&2
    exit 1
  fi
done

bootstrap_service() {
  local database_name="$1"
  local role_name="$2"
  local role_password="$3"

  psql --set=ON_ERROR_STOP=1 --set=role_name="$role_name" --set=role_password="$role_password" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'role_name', :'role_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'role_name') \gexec
SELECT format('ALTER ROLE %I LOGIN PASSWORD %L', :'role_name', :'role_password') \gexec
SQL

  psql --set=ON_ERROR_STOP=1 --set=database_name="$database_name" --set=role_name="$role_name" <<'SQL'
SELECT format('CREATE DATABASE %I OWNER %I', :'database_name', :'role_name')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'database_name') \gexec
SQL
}

bootstrap_service "$OS_DATABASE" "$OS_DATABASE_USER" "$OS_DATABASE_PASSWORD"
bootstrap_service "$BILLING_DATABASE" "$BILLING_DATABASE_USER" "$BILLING_DATABASE_PASSWORD"
