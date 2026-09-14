data "terraform_remote_state" "infra" {
  backend = "s3"

  config = {
    bucket = var.infra_state_bucket
    key    = var.infra_state_key
    region = var.aws_region
  }
}

data "aws_vpc" "shared" {
  id = data.terraform_remote_state.infra.outputs.vpc_id
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
