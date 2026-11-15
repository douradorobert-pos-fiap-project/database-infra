"""Static checks for the sandbox PostgreSQL Terraform configuration."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
TERRAFORM = ROOT / "terraform"


class TestDatabaseTerraform(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = (TERRAFORM / "main.tf").read_text()
        cls.data = (TERRAFORM / "data.tf").read_text()
        cls.variables = (TERRAFORM / "variables.tf").read_text()
        cls.outputs = (TERRAFORM / "outputs.tf").read_text()

    def test_postgresql_rds_exists(self):
        self.assertIn('resource "aws_db_instance" "postgresql"', self.main)
        self.assertIn('engine                 = "postgres"', self.main)

    def test_rds_is_private_and_single_az(self):
        self.assertIn("publicly_accessible        = false", self.main)
        self.assertIn("multi_az                   = false", self.main)

    def test_subnet_group_uses_existing_private_subnets(self):
        self.assertIn('resource "aws_db_subnet_group" "postgresql"', self.main)
        self.assertIn("subnet_ids = data.aws_subnets.private.ids", self.main)
        self.assertIn('name   = "tag:Type"', self.data)
        self.assertIn('values = ["private"]', self.data)

    def test_vpc_is_discovered_by_shared_infra_tags(self):
        self.assertIn('data "aws_vpc" "shared"', self.data)
        self.assertIn('name   = "tag:Name"', self.data)
        self.assertIn('"${var.environment}-vpc"', self.data)
        self.assertIn('name   = "tag:Environment"', self.data)

    def test_dedicated_security_group_and_private_postgres_rule(self):
        self.assertIn('resource "aws_security_group" "rds"', self.main)
        self.assertIn("from_port   = 5432", self.main)
        self.assertIn("to_port     = 5432", self.main)
        self.assertIn("cidr_blocks = [data.aws_vpc.shared.cidr_block]", self.main)
        ingress = self.main.split("egress {")[0]
        self.assertNotIn('cidr_blocks = ["0.0.0.0/0"]', ingress)

    def test_password_is_input_not_hardcoded(self):
        self.assertIn('variable "db_password"', self.variables)
        self.assertIn("password               = var.db_password", self.main)
        all_tf = "\n".join(path.read_text() for path in TERRAFORM.glob("*.tf"))
        self.assertIsNone(re.search(r'password\s*=\s*"[^"$]+"', all_tf))

    def test_required_outputs_exist_without_password(self):
        for output in ("rds_endpoint", "rds_port", "database_name", "database_username"):
            self.assertIn(f'output "{output}"', self.outputs)
        self.assertNotIn("password", self.outputs.lower())

    def test_workflow_exists_and_uses_required_secrets(self):
        workflow = (ROOT / ".github" / "workflows" / "terraform.yml").read_text()
        for secret in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "DB_PASSWORD"):
            self.assertIn(secret, workflow)
        self.assertIn("python3 -m unittest discover tests -v", workflow)
        self.assertIn("plan-database.sh", workflow)
        self.assertIn("apply-database.sh", workflow)

    def test_backend_is_partial_and_account_portable(self):
        providers = (TERRAFORM / "providers.tf").read_text()
        executable = "\n".join(
            path.read_text()
            for path in (
                *TERRAFORM.glob("*.tf"),
                ROOT / ".github" / "workflows" / "terraform.yml",
            )
        )

        self.assertIn('backend "s3" {}', providers)
        self.assertNotIn("terraform-state-", providers)
        self.assertNotIn("264040538379", executable)

    def test_workflow_validates_prs_and_applies_only_manually(self):
        workflow = (ROOT / ".github" / "workflows" / "terraform.yml").read_text()

        self.assertIn("pull_request:", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("push:", workflow)
        self.assertIn("environment: sandbox", workflow)
        self.assertIn("github.event_name == 'workflow_dispatch'", workflow)
        self.assertIn("init -backend=false", workflow)

    def test_workflow_uses_database_variables_and_secret(self):
        workflow = (ROOT / ".github" / "workflows" / "terraform.yml").read_text()

        for variable in ("AWS_REGION", "TF_STATE_BUCKET", "DB_NAME", "DB_USERNAME"):
            self.assertIn(f"vars.{variable}", workflow)
        self.assertIn("secrets.DB_PASSWORD", workflow)
        self.assertIn("scripts/validate-sandbox-config.sh", workflow)

    def test_database_scripts_initialize_the_remote_state_key(self):
        for name in ("plan-database.sh", "apply-database.sh"):
            script = (ROOT / "scripts" / name).read_text()
            self.assertIn('key=database/terraform.tfstate', script)
            self.assertIn("TF_STATE_BUCKET", script)
            self.assertIn("AWS_REGION", script)


if __name__ == "__main__":
    unittest.main()
