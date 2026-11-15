"""Static contracts for isolated logical databases on one RDS instance."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "terraform"


class TestLogicalDatabaseIsolation(unittest.TestCase):
    def test_single_rds_bootstraps_two_logical_databases_and_users(self):
        main = (TF / "main.tf").read_text()
        self.assertEqual(main.count('resource "aws_db_instance"'), 1)
        self.assertIn('resource "terraform_data" "logical_databases"', main)
        self.assertIn("enable_logical_database_bootstrap", main)
        variables = (TF / "variables.tf").read_text()
        for value in (
            "os_service_db",
            "billing_service_db",
            "os_service_user",
            "billing_service_user",
        ):
            self.assertIn(value, variables)
        script = (ROOT / "scripts" / "bootstrap-logical-databases.sh").read_text()
        for variable in (
            "OS_DATABASE",
            "OS_DATABASE_USER",
            "BILLING_DATABASE",
            "BILLING_DATABASE_USER",
        ):
            self.assertIn(variable, script)
        self.assertIn("SELECT format('CREATE DATABASE", script)
        self.assertIn("WHERE NOT EXISTS", script)

    def test_service_credentials_are_sensitive_inputs(self):
        variables = (TF / "variables.tf").read_text()
        for name in ("os_db_password", "billing_db_password"):
            block = variables.split(f'variable "{name}"', 1)[1].split("}", 1)[0]
            self.assertIn("sensitive   = true", block)
            self.assertIn("default     = null", block)
        self.assertNotIn('default     = "', variables.split('variable "os_db_password"', 1)[1].split("}", 1)[0])
        main = (TF / "main.tf").read_text()
        self.assertIn("var.os_db_password != null", main)
        self.assertIn("var.billing_db_password != null", main)

    def test_outputs_are_service_specific_and_password_free(self):
        outputs = (TF / "outputs.tf").read_text()
        for name in ("os_database", "os_database_username", "billing_database", "billing_database_username"):
            self.assertIn(f'output "{name}"', outputs)
        self.assertNotIn("password", outputs.lower())

    def test_bootstrap_is_disabled_by_default_for_private_sandbox_rds(self):
        variables = (TF / "variables.tf").read_text()
        block = variables.split('variable "enable_logical_database_bootstrap"', 1)[1].split("}", 1)[0]
        self.assertIn("default     = false", block)


if __name__ == "__main__":
    unittest.main()
