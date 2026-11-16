import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "k8s" / "database-bootstrap-job.yaml"
BOOTSTRAP = ROOT / "scripts" / "bootstrap-logical-databases.sh"
SYNC = ROOT / "scripts" / "render-database-bootstrap-secret.sh"
PREFLIGHT = ROOT / "scripts" / "validate-deployment-config.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "terraform.yml"


def _fake_kubectl(temp_path: Path) -> tuple[Path, Path]:
    log = temp_path / "kubectl-args.log"
    binary = temp_path / "kubectl"
    binary.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\0' "$@" >> "${FAKE_KUBECTL_LOG}"
if [[ " $* " == *" create "* ]]; then
  printf '%s\\n' 'apiVersion: v1' 'kind: Secret' 'metadata: {name: fake}'
else
  cat >/dev/null
fi
"""
    )
    binary.chmod(0o755)
    return binary, log


class TestDatabaseBootstrap(unittest.TestCase):
    def test_bootstrap_executes_with_alpine_posix_shell(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            psql_log = temp_path / "psql.log"
            psql = temp_path / "psql"
            psql.write_text(
                "#!/bin/sh\n"
                "case \"$*\" in\n"
                "  *database_name=*) ;;\n"
                "  *role_name=*)\n"
                '    [ "${BOOTSTRAP_ROLE_PASSWORD:-}" = "${EXPECTED_ROLE_PASSWORD}" ] || exit 91\n'
                "    ;;\n"
                "esac\n"
                'printf \'ARGS:%s\\n\' "$*" >> "${FAKE_PSQL_LOG}"\n'
                'cat >> "${FAKE_PSQL_LOG}"\n'
            )
            psql.chmod(0o755)
            password = "p@ss:word/%value"
            env = {
                **os.environ,
                "PATH": f"{temp_path}:{os.environ['PATH']}",
                "FAKE_PSQL_LOG": str(psql_log),
                "EXPECTED_ROLE_PASSWORD": password,
                "PGHOST": "sandbox.example.rds.amazonaws.com",
                "PGPORT": "5432",
                "PGDATABASE": "oficina",
                "PGUSER": "oficina_admin",
                "PGPASSWORD": password,
                "OS_DATABASE": "os_service_db",
                "OS_DATABASE_USER": "os_service_user",
                "OS_DATABASE_PASSWORD": password,
                "BILLING_DATABASE": "billing_service_db",
                "BILLING_DATABASE_USER": "billing_service_user",
                "BILLING_DATABASE_PASSWORD": password,
            }

            result = subprocess.run(
                ["/bin/sh", str(BOOTSTRAP)],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            log = psql_log.read_text()
            self.assertEqual(log.count("ARGS:"), 4)
            self.assertIn("\\getenv role_password BOOTSTRAP_ROLE_PASSWORD", log)
            self.assertNotIn(password, log)

    def test_bootstrap_propagates_psql_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            psql = temp_path / "psql"
            psql.write_text("#!/bin/sh\nexit 42\n")
            psql.chmod(0o755)
            env = {
                **os.environ,
                "PATH": f"{temp_path}:{os.environ['PATH']}",
                "PGHOST": "sandbox.example.rds.amazonaws.com",
                "PGPORT": "5432",
                "PGDATABASE": "oficina",
                "PGUSER": "oficina_admin",
                "PGPASSWORD": "admin-password",
                "OS_DATABASE": "os_service_db",
                "OS_DATABASE_USER": "os_service_user",
                "OS_DATABASE_PASSWORD": "os-password",
                "BILLING_DATABASE": "billing_service_db",
                "BILLING_DATABASE_USER": "billing_service_user",
                "BILLING_DATABASE_PASSWORD": "billing-password",
            }

            result = subprocess.run(
                ["/bin/sh", str(BOOTSTRAP)],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 42)

    def test_deploy_workflow_bootstraps_databases_after_terraform_apply(self):
        workflow = WORKFLOW.read_text()

        for variable in (
            "EKS_CLUSTER_NAME",
            "DB_NAME",
            "DB_USERNAME",
            "OS_DATABASE",
            "OS_DATABASE_USERNAME",
            "BILLING_DATABASE",
            "BILLING_DATABASE_USERNAME",
        ):
            self.assertIn(f"vars.{variable}", workflow)
        for secret in ("DB_PASSWORD", "OS_DB_PASSWORD", "BILLING_DB_PASSWORD"):
            self.assertIn(f"secrets.{secret}", workflow)

        self.assertIn("scripts/validate-deployment-config.sh", workflow)
        local_validation_position = workflow.index("scripts/validate-deployment-config.sh")
        credentials_position = workflow.index("aws-actions/configure-aws-credentials@v4")
        apply_position = workflow.index("./scripts/apply-database.sh")
        output_position = workflow.index("output -raw rds_endpoint")
        kubeconfig_position = workflow.index("aws eks update-kubeconfig")
        render_position = workflow.index("scripts/render-database-bootstrap-secret.sh")
        job_position = workflow.index("kubectl apply -f k8s/database-bootstrap-job.yaml")
        self.assertLess(local_validation_position, credentials_position)
        self.assertLess(apply_position, output_position)
        self.assertLess(output_position, kubeconfig_position)
        self.assertLess(kubeconfig_position, render_position)
        self.assertLess(render_position, job_position)
        self.assertIn("kubectl -n oficina wait", workflow)
        self.assertIn("kubectl -n oficina logs job/database-bootstrap", workflow)
        self.assertIn("id: kubeconfig", workflow)
        self.assertIn(
            "if: ${{ always() && steps.kubeconfig.outcome == 'success' }}",
            workflow,
        )
        self.assertIn(
            "kubectl -n oficina delete secret database-bootstrap-secrets",
            workflow,
        )

    def test_preflight_rejects_missing_bootstrap_value_before_aws_calls(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            aws_log = temp_path / "aws-called"
            aws = temp_path / "aws"
            aws.write_text(
                "#!/usr/bin/env bash\n"
                'touch "${FAKE_AWS_LOG}"\n'
                "exit 99\n"
            )
            aws.chmod(0o755)
            env = {
                **os.environ,
                "PATH": f"{temp_path}:{os.environ['PATH']}",
                "FAKE_AWS_LOG": str(aws_log),
                "AWS_ACCESS_KEY_ID": "test-access-key",
                "AWS_SECRET_ACCESS_KEY": "test-secret-key",
                "AWS_SESSION_TOKEN": "test-session-token",
                "AWS_REGION": "us-east-1",
                "TF_STATE_BUCKET": "terraform-state-example",
                "EKS_CLUSTER_NAME": "oficina-sandbox",
                "DB_NAME": "oficina",
                "DB_USERNAME": "oficina_admin",
                "DB_PASSWORD": "admin-password",
                "OS_DATABASE": "os_service_db",
                "OS_DATABASE_USERNAME": "os_service_user",
                "OS_DB_PASSWORD": "os-password",
                "BILLING_DATABASE": "billing_service_db",
                "BILLING_DATABASE_USERNAME": "billing_service_user",
            }

            result = subprocess.run(
                ["bash", str(PREFLIGHT)],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("BILLING_DB_PASSWORD", result.stderr)
            self.assertFalse(aws_log.exists())

    def test_bootstrap_job_is_private_non_root_and_uses_secret_references(self):
        document = yaml.safe_load(JOB.read_text())
        pod = document["spec"]["template"]["spec"]
        container = pod["containers"][0]

        self.assertEqual(document["kind"], "Job")
        self.assertEqual(document["metadata"]["namespace"], "oficina")
        self.assertIs(pod["securityContext"]["runAsNonRoot"], True)
        self.assertEqual(container["image"], "postgres:16.6-alpine")
        self.assertIs(container["securityContext"]["readOnlyRootFilesystem"], True)
        self.assertEqual(
            container["envFrom"],
            [{"secretRef": {"name": "database-bootstrap-secrets"}}],
        )
        self.assertTrue(
            any(
                volume.get("configMap", {}).get("name")
                == "database-bootstrap-script"
                for volume in pod["volumes"]
            )
        )
        self.assertNotIn("REPLACE_ME", JOB.read_text())

    def test_bootstrap_sql_is_idempotent_for_roles_and_databases(self):
        script = BOOTSTRAP.read_text()

        self.assertIn("WHERE NOT EXISTS (SELECT 1 FROM pg_roles", script)
        self.assertIn("ALTER ROLE %I LOGIN PASSWORD %L", script)
        self.assertIn("WHERE NOT EXISTS (SELECT 1 FROM pg_database", script)
        self.assertIn("ALTER DATABASE %I OWNER TO %I", script)
        self.assertIn('bootstrap_service "$OS_DATABASE"', script)
        self.assertIn('bootstrap_service "$BILLING_DATABASE"', script)

    def test_secret_sync_preserves_reserved_password_characters(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            _, log = _fake_kubectl(temp_path)
            password = "p@ss:word/%value"
            env = {
                **os.environ,
                "PATH": f"{temp_path}:{os.environ['PATH']}",
                "FAKE_KUBECTL_LOG": str(log),
                "RDS_ENDPOINT": "sandbox.example.rds.amazonaws.com",
                "RDS_PORT": "5432",
                "DB_NAME": "oficina",
                "DB_USERNAME": "oficina_admin",
                "DB_PASSWORD": password,
                "OS_DATABASE": "os_service_db",
                "OS_DATABASE_USERNAME": "os_service_user",
                "OS_DB_PASSWORD": password,
                "BILLING_DATABASE": "billing_service_db",
                "BILLING_DATABASE_USERNAME": "billing_service_user",
                "BILLING_DB_PASSWORD": password,
            }

            result = subprocess.run(
                ["bash", str(SYNC)],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            arguments = log.read_bytes().split(b"\0")

            self.assertEqual(result.returncode, 0)
            self.assertIn(
                f"--from-literal=DB_PASSWORD={password}".encode(), arguments
            )
            self.assertIn(
                f"--from-literal=OS_DB_PASSWORD={password}".encode(), arguments
            )
            self.assertIn(
                f"--from-literal=BILLING_DB_PASSWORD={password}".encode(), arguments
            )
            self.assertNotIn(password, result.stdout)
            self.assertNotIn(password, result.stderr)
            self.assertNotIn(b"DATABASE_URL", log.read_bytes())


if __name__ == "__main__":
    unittest.main()
