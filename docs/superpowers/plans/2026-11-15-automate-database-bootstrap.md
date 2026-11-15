# Automated Database Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the idempotent logical-database bootstrap automatically after a successful manual Terraform apply.

**Architecture:** The public GitHub runner will not connect directly to the private RDS. It will obtain the RDS endpoint from Terraform state, authenticate to the existing EKS cluster, submit the existing Kubernetes bootstrap Job, wait for completion, surface logs, and delete the administrative Secret afterward.

**Tech Stack:** GitHub Actions, Terraform, Kubernetes, Bash, Python unittest

**Spec:** Approved design in the 2026-11-15 conversation.

## Global Constraints

- Deploy and bootstrap run only through `workflow_dispatch` in environment `sandbox`.
- Database administrator credentials stay in `database-infra` GitHub Secrets and must not reach service Deployments.
- OS and Billing retain ownership of their Alembic migrations.
- The bootstrap remains idempotent and runs from inside EKS because RDS is private.
- The administrative Kubernetes Secret is removed after success or failure.

## Review Focus

- Missing bootstrap configuration must fail before Terraform plan/apply.
- Terraform outputs must provide endpoint and port without hardcoding them.
- Bootstrap must start only after a successful Terraform apply.
- Job failure must expose logs and fail the workflow.
- Cleanup must not leak or print database passwords.

---

### Task 1: Integrate Bootstrap with Manual Database Deployment

**Files:**
- Modify: `.github/workflows/terraform.yml`
- Modify: `scripts/validate-sandbox-config.sh`
- Modify: `tests/test_database_bootstrap.py`
- Modify: `tests/test_terraform_static.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: Terraform outputs `rds_endpoint` and `rds_port`; GitHub Variables for cluster/database names; GitHub Secrets for administrator and service passwords.
- Produces: `os_service_db`/`os_service_user` and `billing_service_db`/`billing_service_user` before service pipelines run migrations.

- [ ] **Step 1: Add failing workflow and preflight tests**

Assert that the workflow maps all bootstrap Variables/Secrets, reads Terraform outputs after apply, updates EKS kubeconfig, renders bootstrap credentials, applies/waits/logs the Job, and always deletes the administrative Secret. Assert that preflight rejects every missing non-secret configuration value without calling AWS.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python3 -m unittest tests.test_database_bootstrap tests.test_terraform_static -v`
Expected: failures identifying the missing automated bootstrap steps and preflight inputs.

- [ ] **Step 3: Implement workflow bootstrap and preflight validation**

Add the required environment mappings and post-apply steps. Use `terraform output -raw`, `aws eks update-kubeconfig`, the existing render script, and a shell block that reports Job logs on both success and failure. Add an `if: always()` cleanup step for `database-bootstrap-secrets`.

- [ ] **Step 4: Update operational documentation**

Document the automatic bootstrap, required Variables/Secrets, cleanup behavior, and the fact that service migrations run afterward in their own pipelines.

- [ ] **Step 5: Verify and commit**

Run: `python3 -m unittest discover tests -v`
Expected: all tests pass.

Run: `terraform -chdir=terraform fmt -check -recursive && terraform -chdir=terraform validate`
Expected: valid Terraform configuration.

Commit: `feat: automate logical database bootstrap`
