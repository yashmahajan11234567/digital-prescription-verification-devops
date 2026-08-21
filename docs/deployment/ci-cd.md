# RxVerify CI/CD Pipeline Documentation

## 1. Workflow Overview

**File:** `.github/workflows/ci-cd.yml`

Single workflow file handling both CI (automatic) and CD (manual dispatch).

### 1.1 Trigger Matrix

| Event | CI Jobs | CD Jobs |
|-------|---------|---------|
| `push` to `main` | ✅ All | ❌ |
| `pull_request` to `main` | ✅ All | ❌ |
| `workflow_dispatch` (manual) | ✅ All | ✅ If `environment: production` |

### 1.2 Permissions

```yaml
permissions:
  contents: read
  id-token: write
```

- `contents: read` — Checkout repository
- `id-token: write` — OIDC for AWS (if configured)

---

## 2. CI Jobs (Automatic)

### 2.1 Job: `validation`

```yaml
runs-on: ubuntu-latest
steps:
  - checkout
  - setup-python (3.12, pip cache)
  - install: requirements.txt + requirements-dev.txt
  - validate: python -c "import flask; import gunicorn; import psycopg2; import pytest"
```

**Purpose:** Fast sanity check that all dependencies install and import correctly.

---

### 2.2 Job: `postgresql-tests`

```yaml
runs-on: ubuntu-latest
services:
  postgres:
    image: postgres:16-alpine
    env: POSTGRES_DB=rxverify, POSTGRES_USER=postgres, POSTGRES_PASSWORD=testpassword
    ports: 5432:5432
    healthcheck: pg_isready
steps:
  - checkout, setup-python, install deps
  - wait for pg_isready (30 retries × 2s)
  - pytest tests/ -q --tb=short -x
    env:
      DATABASE_URL: postgresql://postgres:testpassword@localhost:5432/rxverify
      FLASK_ENV: testing
      SECRET_KEY: test-secret-key
      TESTING: "1"
```

**Purpose:** Full test suite against real PostgreSQL 16 (matches production DB).

**Note:** Uses hardcoded `testpassword` — CI-only, not production.

---

### 2.3 Job: `docker-validation`

```yaml
runs-on: ubuntu-latest
steps:
  - checkout
  - docker compose config          # Validates syntax + interpolation
  - docker build -t rxverify:sha-${{ github.sha }} .
  - docker compose up -d --build
  - wait for health (30 retries × 2s): curl http://localhost:5001/health
  - smoke: curl -f http://localhost:5001/health
  - docker compose down (always)
```

**Purpose:** Validates Docker Compose stack builds, starts, and passes health checks.

---

### 2.4 Job: `terraform-validation`

```yaml
runs-on: ubuntu-latest
defaults:
  run:
    working-directory: terraform
steps:
  - checkout
  - hashicorp/setup-terraform@v3 (version 1.9.0)
  - terraform fmt -check -recursive
  - terraform init -backend=false
  - terraform validate
```

**Purpose:** Validates Terraform syntax, formatting, and configuration without AWS credentials.

---

### 2.5 Job: `ansible-validation`

```yaml
runs-on: ubuntu-latest
defaults:
  run:
    working-directory: ansible
steps:
  - checkout
  - pip install ansible-core
  - ansible-playbook --syntax-check deploy.yml
  - ansible-config dump --only-changed
```

**Purpose:** Validates Ansible playbook syntax and shows effective configuration.

---

## 3. CD Jobs (Manual Workflow Dispatch)

### 3.1 Execution Flow

```mermaid
flowchart TD
    D1[workflow_dispatch<br/>environment: production] --> D2[Terraform Plan]
    D2 --> D3[Upload tfplan artifact]
    D3 --> D4[Manual Approval<br/>environment: production]
    D4 --> D5[Terraform Apply]
    D5 --> D6[Output: instance_public_ip, website_url]
    D6 --> D7[Ansible Deploy]
    D7 --> D8[Generate inventory from Terraform outputs]
    D8 --> D9[Run deploy.yml playbook]
    D9 --> D10[Post-Deploy Health Check]
    D10 --> D11[Smoke Test: /login]
```

---

### 3.2 Job: `terraform-plan`

```yaml
needs: [validation, postgresql-tests, docker-validation, terraform-validation, ansible-validation]
if: github.event_name == 'workflow_dispatch'
runs-on: ubuntu-latest
defaults:
  run:
    working-directory: terraform
steps:
  - checkout
  - setup-terraform
  - configure-aws-credentials (via secrets)
  - terraform init
  - terraform plan -out=tfplan
  - upload-artifact: tfplan (7-day retention)
```

**Gate:** Runs only if all CI jobs pass AND manual dispatch.

---

### 3.3 Job: `terraform-apply`

```yaml
needs: terraform-plan
if: github.event_name == 'workflow_dispatch'
runs-on: ubuntu-latest
environment: production   # ← REQUIRES MANUAL APPROVAL IN GITHUB
defaults:
  run:
    working-directory: terraform
steps:
  - checkout, setup-terraform, configure-aws-credentials
  - download-artifact: tfplan
  - terraform apply -auto-approve tfplan
  - output: instance_public_ip, website_url
```

**Approval Gate:** GitHub Environment `production` requires manual approval by authorized reviewer.

---

### 3.4 Job: `ansible-deploy`

```yaml
needs: terraform-apply
if: github.event_name == 'workflow_dispatch'
runs-on: ubuntu-latest
environment: production   # ← SECOND APPROVAL GATE (optional, same env)
steps:
  - checkout, configure-aws-credentials
  - setup-terraform
  - get Terraform outputs (instance_public_ip, website_url)
  - generate inventory: python generate_inventory.py --tf-output-dir ../terraform --key-file "${{ secrets.SSH_PRIVATE_KEY }}"
  - pip install ansible-core docker
  - ansible-playbook -i inventory.ini deploy.yml
    env: ANSIBLE_HOST_KEY_CHECKING: "False"
  - verify: curl ${{ website_url }}/health (30 retries × 10s)
  - smoke: curl ${{ website_url }}/login
```

**Dependencies:** Requires `terraform-apply` outputs + `SSH_PRIVATE_KEY` secret.

---

## 4. Secrets & Variables Reference

### 4.1 GitHub Secrets (Required for CD)

| Secret | Scope | Description |
|--------|-------|-------------|
| `AWS_ACCESS_KEY_ID` | Org/Repo | IAM user with EC2, VPC, IAM permissions |
| `AWS_SECRET_ACCESS_KEY` | Org/Repo | Corresponding secret access key |
| `SSH_PRIVATE_KEY` | Org/Repo | EC2 key pair PEM file (for Ansible SSH) |

### 4.2 GitHub Variables

| Variable | Scope | Description |
|----------|-------|-------------|
| `AWS_REGION` | Org/Repo | e.g., `ap-south-1` |

### 4.3 CI-Only Hardcoded Values

```yaml
env:
  POSTGRES_PASSWORD: testpassword  # CI-only PostgreSQL password
```

---

## 5. GitHub Environment Configuration

### 5.1 `production` Environment

Required settings in GitHub repository → Settings → Environments → `production`:

- **Required reviewers**: At least 1 person/team
- **Wait timer**: Optional (e.g., 5 minutes)
- **Deployment branches**: `main` (or protected branches)

This creates the **manual approval gate** before `terraform-apply` and `ansible-deploy`.

---

## 6. Pipeline Status Matrix

| Stage | Automation | Approval | Secrets Required |
|-------|------------|----------|------------------|
| CI: Validation | Auto (push/PR) | None | None |
| CI: PostgreSQL Tests | Auto (push/PR) | None | None |
| CI: Docker Validation | Auto (push/PR) | None | None |
| CI: Terraform Validation | Auto (push/PR) | None | None |
| CI: Ansible Validation | Auto (push/PR) | None | None |
| CD: Terraform Plan | Manual dispatch | None | AWS creds |
| CD: Terraform Apply | Manual dispatch | **Yes (production env)** | AWS creds |
| CD: Ansible Deploy | Manual dispatch | **Yes (production env)** | AWS creds, SSH key |

---

## 7. Verification Commands

```bash
# Local CI simulation
# 1. Validation
python -c "import flask; import gunicorn; import psycopg2; import pytest"

# 2. PostgreSQL tests (requires local PostgreSQL on 5432)
DATABASE_URL=postgresql://postgres:testpassword@localhost:5432/rxverify \
FLASK_ENV=testing SECRET_KEY=test-secret-key TESTING=1 \
python -m pytest tests/ -q --tb=short -x

# 3. Docker validation
docker compose config
docker compose up -d --build
sleep 10
curl -f http://localhost:5001/health
docker compose down

# 4. Terraform validation
cd terraform
terraform fmt -check -recursive
terraform init -backend=false
terraform validate

# 5. Ansible validation
cd ansible
ansible-playbook --syntax-check deploy.yml
ansible-config dump --only-changed
```

---

## 8. Current Deployment Status

| Phase | Status | Evidence |
|-------|--------|----------|
| CI Pipeline | **VALIDATED** | Runs on push/PR; all jobs pass |
| CD Pipeline | **CONFIGURED** | Workflow defined, manual dispatch ready |
| Terraform Apply | **NOT EXECUTED** | Not run in current verification |
| Ansible Deploy | **NOT EXECUTED** | Not run in current verification |
| Live AWS Deployment | **NOT VERIFIED** | No current EC2 instance confirmed |

> ⚠️ **Important:** The CD pipeline is fully *configured* and *validated* in CI, but has **not been executed** against a live AWS account in the current verification cycle. No live EC2 IP or deployment URL should be documented as current.

---

*Last updated: 2026-08-21 — Based on `.github/workflows/ci-cd.yml` inspection*