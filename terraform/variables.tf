variable "aws_region" {
  description = "AWS region where the existing shared network and RDS live."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Shared-infra environment used to find the existing VPC and private subnets."
  type        = string
  default     = "sandbox"
}

variable "db_name" {
  description = "Initial PostgreSQL database name."
  type        = string
  default     = "oficina"
}

variable "db_username" {
  description = "PostgreSQL master username. Supply through TF_VAR_db_username in CI."
  type        = string
  default     = "oficina_admin"
}

variable "db_password" {
  description = "PostgreSQL master password. Supply only through TF_VAR_db_password."
  type        = string
  sensitive   = true
  nullable    = false

  validation {
    condition     = length(var.db_password) >= 8
    error_message = "db_password must contain at least 8 characters."
  }
}

variable "db_instance_class" {
  description = "RDS instance class; db.t4g.micro is the lowest-cost suitable PostgreSQL class in us-east-1."
  type        = string
  default     = "db.t4g.micro"
}

variable "engine_version" {
  description = "PostgreSQL major engine version. RDS manages compatible minor updates."
  type        = string
  default     = "16"
}

variable "allocated_storage" {
  description = "Allocated gp3 storage in GiB; 20 is the RDS PostgreSQL gp3 minimum."
  type        = number
  default     = 20

  validation {
    condition     = var.allocated_storage >= 20
    error_message = "RDS PostgreSQL gp3 storage must be at least 20 GiB."
  }
}

variable "backup_retention_period" {
  description = "Number of automated-backup retention days for this sandbox."
  type        = number
  default     = 1

  validation {
    condition     = var.backup_retention_period >= 1 && var.backup_retention_period <= 35
    error_message = "backup_retention_period must be between 1 and 35 days."
  }
}

variable "skip_final_snapshot" {
  description = "Whether to skip a final snapshot when destroying the sandbox database."
  type        = bool
  default     = true
}
