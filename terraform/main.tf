resource "aws_db_subnet_group" "postgresql" {
  name       = "${var.environment}-oficina-postgresql"
  subnet_ids = data.aws_subnets.private.ids

  tags = {
    Name = "${var.environment}-oficina-postgresql"
  }

  lifecycle {
    precondition {
      condition     = length(data.aws_subnets.private.ids) >= 2
      error_message = "At least two private subnets from shared-infra are required for the RDS DB subnet group."
    }
  }
}

resource "aws_security_group" "rds" {
  name        = "${var.environment}-oficina-rds-sg"
  description = "PostgreSQL access from the private shared-infra VPC"
  vpc_id      = data.aws_vpc.shared.id

  ingress {
    description = "PostgreSQL from EKS workloads and nodes in the shared private VPC"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.shared.cidr_block]
  }

  egress {
    description = "Allow return traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment}-oficina-rds-sg"
  }
}

resource "aws_db_instance" "postgresql" {
  identifier             = "${var.environment}-oficina-postgresql"
  engine                 = "postgres"
  engine_version         = var.engine_version
  instance_class         = var.db_instance_class
  allocated_storage      = var.allocated_storage
  storage_type           = "gp3"
  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password
  port                   = 5432
  db_subnet_group_name   = aws_db_subnet_group.postgresql.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  multi_az                   = false
  publicly_accessible        = false
  backup_retention_period    = var.backup_retention_period
  deletion_protection        = false
  skip_final_snapshot        = var.skip_final_snapshot
  auto_minor_version_upgrade = true
  copy_tags_to_snapshot      = true

  tags = {
    Name = "${var.environment}-oficina-postgresql"
  }
}
