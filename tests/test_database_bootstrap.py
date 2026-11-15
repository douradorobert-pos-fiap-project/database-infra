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
