# Resolve Main Conflicts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate `origin/main` into `feature/fase-4-infrastructure` without losing the portable, manually deployed Phase 4 database infrastructure.

**Architecture:** Merge the historical Phase 3 mainline into the Phase 4 branch and resolve overlapping configuration in favor of the Phase 4 deployment model. Preserve non-overlapping mainline documentation while keeping one RDS instance, separate logical service databases, partial S3 backend configuration, and manual sandbox deployment.

**Tech Stack:** Git, Terraform, GitHub Actions, Python unittest, Bash

**Spec:** Approved conflict-resolution design in the 2026-11-15 conversation.

## Global Constraints

- Modify and commit only `feature/fase-4-infrastructure`; never modify `main`.
- Preserve Phase 3 history and the `fase-3-final` tag.
- Pull requests validate without AWS access; deploy remains `workflow_dispatch` only.
- Keep account-dependent values outside versioned Terraform configuration.
- Keep one private RDS instance with isolated OS and Billing logical databases.

## Review Focus

- A pull request must not trigger AWS deployment.
- The deploy job must receive all required AWS, backend, and database inputs.
- No historical AWS account ID or state bucket may remain executable configuration.
- Terraform validation must accept the sandbox variables supplied by GitHub Actions.
- Database bootstrap and service-specific credentials must remain documented and tested.

---

### Task 1: Merge and Resolve Phase 4 Configuration

**Files:**
- Modify: `.github/workflows/terraform.yml`
- Modify: `README.md`
- Modify: `terraform/environments/sandbox/terraform.tfvars`
- Modify: `terraform/variables.tf`
- Modify: `tests/test_terraform_static.py`
- Test: `tests/test_terraform_static.py`

**Interfaces:**
- Consumes: `origin/main` and the current `feature/fase-4-infrastructure` tree.
- Produces: a merge commit whose workflow validates PRs and deploys manually with portable sandbox inputs.

- [ ] **Step 1: Reproduce the merge conflicts**

Run: `git merge --no-commit --no-ff origin/main`
Expected: conflicts in the five overlapping files listed above.

- [ ] **Step 2: Preserve the failing conflict state as the RED gate**

Run: `git diff --check`
Expected: failure caused by unresolved conflict markers.

- [ ] **Step 3: Resolve configuration and documentation**

Keep the Phase 4 workflow, portable variables, logical database documentation, and the combined static tests. Remove all conflict markers without adding automatic deployment.

- [ ] **Step 4: Verify the resolved tree**

Run: `python3 -m unittest discover tests -v`
Expected: 19 tests pass.

Run: `terraform -chdir=terraform fmt -check -recursive`
Expected: exit code 0.

Run: `TF_VAR_aws_region=us-east-1 TF_VAR_db_name=oficina TF_VAR_db_username=oficina_admin TF_VAR_db_password=validation-placeholder terraform -chdir=terraform init -backend=false -input=false && TF_VAR_aws_region=us-east-1 TF_VAR_db_name=oficina TF_VAR_db_username=oficina_admin TF_VAR_db_password=validation-placeholder terraform -chdir=terraform validate`
Expected: Terraform reports a valid configuration.

- [ ] **Step 5: Commit the merge resolution**

Run: `git commit -m "merge: resolve fase 4 database infrastructure conflicts"`
Expected: one merge commit on `feature/fase-4-infrastructure`, with a clean worktree.
