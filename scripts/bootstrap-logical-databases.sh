#!/bin/sh
set -eu

require_value() {
  if [ -z "$2" ]; then
    printf 'Missing required database bootstrap value: %s\n' "$1" >&2
    exit 2
  fi
}

require_value PGHOST "${PGHOST:-}"
require_value PGPORT "${PGPORT:-}"
require_value PGDATABASE "${PGDATABASE:-}"
require_value PGUSER "${PGUSER:-}"
require_value PGPASSWORD "${PGPASSWORD:-}"
require_value OS_DATABASE "${OS_DATABASE:-}"
require_value OS_DATABASE_USER "${OS_DATABASE_USER:-}"
require_value OS_DATABASE_PASSWORD "${OS_DATABASE_PASSWORD:-}"
require_value BILLING_DATABASE "${BILLING_DATABASE:-}"
require_value BILLING_DATABASE_USER "${BILLING_DATABASE_USER:-}"
require_value BILLING_DATABASE_PASSWORD "${BILLING_DATABASE_PASSWORD:-}"

for identifier in "$OS_DATABASE" "$OS_DATABASE_USER" "$BILLING_DATABASE" "$BILLING_DATABASE_USER"; do
  case "$identifier" in
    [a-z_]* ) ;;
    * )
      echo "Invalid PostgreSQL identifier" >&2
      exit 1
      ;;
  esac
  case "$identifier" in
    *[!a-z0-9_]* )
      echo "Invalid PostgreSQL identifier" >&2
      exit 1
      ;;
  esac
done

bootstrap_service() {
  bootstrap_database_name="$1"
  bootstrap_role_name="$2"
  bootstrap_role_password="$3"

  BOOTSTRAP_ROLE_PASSWORD="$bootstrap_role_password" \
    psql --set=ON_ERROR_STOP=1 --set=role_name="$bootstrap_role_name" <<'SQL'
\getenv role_password BOOTSTRAP_ROLE_PASSWORD
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'role_name', :'role_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'role_name') \gexec
SELECT format('ALTER ROLE %I LOGIN PASSWORD %L', :'role_name', :'role_password') \gexec
SQL

  psql --set=ON_ERROR_STOP=1 --set=database_name="$bootstrap_database_name" --set=role_name="$bootstrap_role_name" <<'SQL'
SELECT format('CREATE DATABASE %I OWNER %I', :'database_name', :'role_name')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'database_name') \gexec
SQL
}

bootstrap_service "$OS_DATABASE" "$OS_DATABASE_USER" "$OS_DATABASE_PASSWORD"
bootstrap_service "$BILLING_DATABASE" "$BILLING_DATABASE_USER" "$BILLING_DATABASE_PASSWORD"
