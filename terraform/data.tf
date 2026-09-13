# These data sources deliberately use shared-infra's stable tags instead of a
# Terraform state dependency. shared-infra creates Name=sandbox-vpc and marks
# its private subnets with Environment=sandbox and Type=private.
data "aws_vpc" "shared" {
  filter {
    name   = "tag:Name"
    values = ["${var.environment}-vpc"]
  }

  filter {
    name   = "tag:Environment"
    values = [var.environment]
  }
}

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.shared.id]
  }

  filter {
    name   = "tag:Environment"
    values = [var.environment]
  }

  filter {
    name   = "tag:Type"
    values = ["private"]
  }
}
