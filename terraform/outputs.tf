output "rds_endpoint" {
  description = "PostgreSQL RDS endpoint hostname for DB_HOST."
  value       = aws_db_instance.postgresql.address
}

output "rds_port" {
  description = "PostgreSQL port for DB_PORT."
  value       = aws_db_instance.postgresql.port
}

output "database_name" {
  description = "Database name for DB_NAME."
  value       = aws_db_instance.postgresql.db_name
}

output "database_username" {
  description = "Master username for DB_USERNAME."
  value       = aws_db_instance.postgresql.username
}

output "os_database" {
  description = "OS Service logical database name."
  value       = var.os_database
}

output "os_database_username" {
  description = "OS Service isolated database username."
  value       = var.os_database_username
}

output "billing_database" {
  description = "Billing Service logical database name."
  value       = var.billing_database
}

output "billing_database_username" {
  description = "Billing Service isolated database username."
  value       = var.billing_database_username
}
