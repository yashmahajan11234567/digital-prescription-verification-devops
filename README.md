# RxVerify Digital Prescription Verification System

A complete digital prescription verification system with role-based portals for doctors, pharmacists, and administrators, featuring prescription lifecycle management, hospital hierarchy, in-app notifications, and a full DevOps pipeline (Docker, Terraform, Ansible, GitHub Actions CI/CD).

---

## Problem Statement

Paper-based prescriptions suffer from forgery risk, no real-time verification, no audit trail, manual handoff errors, and no notification to prescribing doctors when medicine is dispensed. RxVerify replaces this with a secure digital workflow: unique verification IDs, real-time pharmacist verification, automated handoff notifications, and complete audit trails.

---

## Features

### Doctor Portal
- Secure login with role validation
- Create prescriptions (7 fields: patient name, reference, doctor, clinic, medicine, dosage, instructions, issue date)
- Unique non-sequential verification ID (`RX-<10HEX>`)
- View prescription history with date filtering
- Revoke active prescriptions
- Receive notifications when pharmacist marks medicine received

### Pharmacist Portal
- Secure login with role validation
- Verify prescriptions by verification ID
- Mark active prescriptions as received (terminal state)
- Protection: cannot receive revoked or already-received prescriptions
- Automatic notification to prescribing doctor and all admins

### Admin Portal
- Dashboard with system statistics (hospitals, users, prescriptions by status)
- Hospital management: list with doctor/pharmacist counts
- Hospital detail: doctors with prescription counts, pharmacists with verification counts
- Doctor detail with optional date filtering
- Full system oversight across all hospitals

### Prescription Lifecycle
```
ACTIVE → RECEIVED (pharmacist action, terminal)
ACTIVE → REVOKED  (doctor action, terminal)
```
- Data preservation: all original fields retained on transition
- Duplicate receive protection
- Revoked receive protection

### Hospital Hierarchy
- Hospitals table with unique names
- Users affiliated via `hospital_id` FK (admins unaffiliated)
- Role-based visibility: own hospital vs. all hospitals

### Notifications
- In-app only (no external email/SMS dependencies)
- Auto-created on medicine receipt
- Recipients: prescribing doctor + all active admins
- Read/unread state with individual and bulk mark-read
- Deduplication prevents duplicate alerts

---

## Roles & Credentials (Development Demo)

| Role | Email | Password |
|------|-------|----------|
| **Doctor** | `doctor@rxverify.local` | `doctor123` |
| **Pharmacist** | `pharmacist@rxverify.local` | `pharmacist123` |
| **Admin** | `admin@rxverify.local` | `admin123` |

> ⚠️ **DEVELOPMENT CREDENTIALS ONLY** — Never use in production. Production requires explicit admin creation via environment variables.

---

## Architecture

```mermaid
flowchart TD
    subgraph Client[Client]
        Browser[Web Browser]
    end

    subgraph App[Application - Flask]
        Auth[Auth Blueprint]
        Doctor[Doctor Blueprint]
        Pharm[Pharmacist Blueprint]
        Admin[Admin Blueprint]
    end

    subgraph Data[Data Layer]
        SQLite[(SQLite Dev)]
        PG[(PostgreSQL 16 Prod)]
    end

    subgraph DevOps[DevOps Pipeline]
        Docker[Docker Compose]
        TF[Terraform AWS]
        Ansible[Ansible Deploy]
        CICD[GitHub Actions CI/CD]
    end

    Browser --> Auth & Doctor & Pharm & Admin
    Auth & Doctor & Pharm & Admin -.-> Data
    Data -.-> SQLite & PG
    DevOps -.-> Docker & TF & Ansible & CICD
    CICD --> TF --> Ansible
```

**Components:**
- **Flask Application Factory** — Single entry point, three configs (Dev/Testing/Prod)
- **Blueprints** — Auth, Doctor, Pharmacist, Admin
- **Database Abstraction** — Unified SQLite/PostgreSQL interface with auto-placeholder conversion
- **Models** — User, Notification dataclasses with data access layer
- **Seeds** — Idempotent development data with hospital associations

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Web Framework** | Flask 3.x |
| **WSGI Server** | Gunicorn |
| **Database (Dev)** | SQLite 3 |
| **Database (Prod)** | PostgreSQL 16 |
| **Password Hashing** | Werkzeug PBKDF2-SHA256 |
| **Containerization** | Docker multi-stage, Docker Compose v2 |
| **Infrastructure** | Terraform ≥1.5 (AWS) |
| **Configuration** | Ansible Core + community.docker |
| **CI/CD** | GitHub Actions |
| **Testing** | pytest 8.x (98 tests) |
| **Language** | Python 3.12 |

---

## Project Structure

```
digital-prescription-verification-devops/
├── app.py                      # Backwards compatibility entry point
├── config.py                   # Configuration classes (Dev/Testing/Prod)
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development dependencies
├── Dockerfile                  # Multi-stage production image
├── docker-compose.yml          # Local development stack
├── .dockerignore               # Docker build exclusions
├── .env.example                # Environment variable template
├── .github/workflows/ci-cd.yml # CI/CD pipeline
├── src/
│   ├── __init__.py             # Application factory + DB abstraction
│   ├── decorators.py           # RBAC decorators
│   ├── seeds.py                # Development data seeding
│   ├── admin/                  # Admin blueprint
│   ├── auth/                   # Authentication blueprint
│   ├── doctor/                 # Doctor blueprint
│   ├── pharmacist/             # Pharmacist blueprint
│   └── models/                 # User, Notification models
├── templates/                   # Jinja2 templates
├── static/                      # CSS
├── tests/                       # 98 pytest tests
├── terraform/                   # AWS infrastructure
│   ├── main.tf                 # Resources
│   ├── variables.tf            # Input variables
│   ├── outputs.tf              # Outputs
│   ├── versions.tf             # Provider versions
│   └── terraform.tfvars.example
├── ansible/                     # Configuration management
│   ├── deploy.yml              # Deployment playbook
│   ├── generate_inventory.py   # Terraform → Ansible inventory
│   ├── secrets.yml.example     # Secrets template
│   └── requirements.yml        # Galaxy collections
└── docs/                        # Documentation
    ├── architecture/
    ├── deployment/
    ├── security/
    ├── testing/
    └── submission/
```

---

## Local Setup

### Option 1: Virtual Environment (SQLite)

```bash
# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configure environment
cp .env.example .env
# Edit .env if needed (FLASK_ENV=development, SECRET_KEY, etc.)

# Run Flask development server
flask --app app run --debug
# Open http://127.0.0.1:5000
```

SQLite database auto-created at `instance/prescriptions.db`.

### Option 2: Docker Compose (PostgreSQL)

```bash
# Prerequisites: Docker Engine 24+, Docker Compose v2+

# Configure environment
cp .env.example .env
# Edit .env — at minimum change:
# POSTGRES_PASSWORD=your-secure-password
# SECRET_KEY=your-long-random-secret

# Validate config
docker compose config

# Build and start
docker compose up --build -d

# Check status
docker compose ps

# View logs
docker compose logs -f

# Verify health
curl http://localhost:5001/health
# Expected: {"status": "ok"}

# Open http://localhost:5001
```

**Services:**
| Service | Host Port | Container Port | Notes |
|---------|-----------|----------------|-------|
| rxverify (Flask/Gunicorn) | 5001 | 5000 | Port 5001 avoids macOS Control Center conflict |
| postgres | 5433 | 5432 | Exposed for debugging; internal network uses 5432 |

**Data Persistence:**
- `prescription_data` volume → `/app/instance`
- `postgres_data` volume → `/var/lib/postgresql/data`

**Reset completely:**
```bash
docker compose down -v
```

---

## Testing

```bash
# Run all tests (98 tests)
python -m pytest tests/ -q

# Verbose output
python -m pytest tests/ -v

# Specific categories
python -m pytest tests/test_auth.py -q
python -m pytest tests/test_task6_integration.py -q

# With coverage
python -m pytest tests/ --cov=src --cov-report=html
```

**Current Result:**
```
98 tests passed
```

(3 tests skipped/fail only when local PostgreSQL not running — expected)

### Test Categories
- **App Core** (4): Health, home, routing
- **Authentication** (35): Login/logout, password hash, roles, user CRUD
- **Prescription Flow** (24): Issue, verify, revoke, receive, transitions
- **Hospital & Admin** (25): Seeding, dashboard, hierarchy, date filter
- **Notifications**: Creation, read state, ownership, deduplication
- **IDOR Protection**: Notification ownership, cross-user access
- **Input Validation**: Malformed IDs, SQL-like strings, non-existent
- **Unit Routes** (10): Route behavior with test client

---

## PostgreSQL

The application supports both SQLite (development) and PostgreSQL (production/Docker/CI) through a unified abstraction layer in `src/__init__.py`.

**Connection string format:**
```bash
# Local SQLite (default)
DATABASE_URL=sqlite:///instance/prescriptions.db

# Docker Compose
DATABASE_URL=postgresql://postgres:password@postgres:5432/rxverify

# Production (Ansible)
DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/rxverify
```

**Key compatibility features:**
- Auto-increment (SQLite) vs Identity (PostgreSQL)
- `?` placeholders auto-converted to `%s` for PostgreSQL
- Idempotent migrations for `UNIQUE` constraints and columns
- Boolean stored as INTEGER (0/1) on both backends
- Timestamps as ISO8601 UTC strings

---

## Terraform (AWS Infrastructure)

Provisions: VPC, public subnet, Internet Gateway, route table, security group, EC2 instance (Ubuntu 24.04, t3.micro).

```bash
cd terraform

# Configure variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars:
# allowed_ssh_cidr = "YOUR_IP/32"   # CRITICAL: override default 0.0.0.0/0

# Provision
terraform fmt -check -recursive
terraform init
terraform validate
terraform plan
terraform apply
```

**Outputs:**
- `instance_public_ip` — Target for Ansible
- `instance_public_dns` — DNS name
- `website_url` — `http://<public_ip>`

**Critical Variable:**
```hcl
variable "allowed_ssh_cidr" {
  default = "0.0.0.0/0"  # MUST OVERRIDE for production!
}
```

---

## Ansible (Deployment to EC2)

```bash
cd ansible

# 1. Generate inventory from Terraform outputs
python generate_inventory.py --tf-output-dir ../terraform --key-file ~/.ssh/your-key.pem > inventory.ini

# 2. Configure secrets (gitignored)
cp secrets.yml.example secrets.yml
# Edit secrets.yml:
# app_secret_key: "YOUR_32+_CHAR_HEX"     # openssl rand -hex 32
# postgres_password: "YOUR_16+_CHAR"       # openssl rand -hex 16

# 3. Test connectivity
ansible all -m ping

# 4. Deploy
ansible-playbook -i inventory.ini deploy.yml
```

**Playbook Flow:**
1. Assert secure secrets (fail fast on defaults)
2. Update Ubuntu packages
3. Install Docker Engine + Python Docker SDK
4. Start/enable Docker service
5. Copy application files to `/opt/rxverify`
6. Build Docker image on EC2
7. Create Docker network + volumes
8. Deploy PostgreSQL container with healthcheck
9. Wait for PostgreSQL readiness
10. Deploy RxVerify container (port 80:5000)
11. Verify health endpoint

---

## CI/CD Pipeline (GitHub Actions)

**Workflow:** `.github/workflows/ci-cd.yml`

### Continuous Integration (Automatic on push/PR to main)
| Job | Validates |
|-----|-----------|
| `validation` | Python imports, dependencies |
| `postgresql-tests` | 98 tests vs live PostgreSQL 16 |
| `docker-validation` | Compose config, build, up, health, smoke |
| `terraform-validation` | fmt, init (no backend), validate |
| `ansible-validation` | Syntax check, config dump |

### Continuous Deployment (Manual workflow_dispatch)
```
Terraform Plan → [Approval Gate: environment:production] → Terraform Apply → Ansible Deploy → Health + Smoke Checks
```

**Required GitHub Secrets:**
- `AWS_ACCESS_KEY_ID` — IAM user with EC2/VPC permissions
- `AWS_SECRET_ACCESS_KEY` — Corresponding secret key
- `SSH_PRIVATE_KEY` — EC2 key pair PEM file

**Required GitHub Variables:**
- `AWS_REGION` — e.g., `ap-south-1`

**Approval Gate:** GitHub Environment `production` requires manual approval by authorized reviewer.

---

## Security

### Implemented Controls
| Layer | Controls |
|-------|----------|
| **Application** | Parameterized queries, PBKDF2 password hashing, RBAC decorators, session auth, input validation, generic error messages |
| **Database** | FK constraints, CHECK constraints, UNIQUE constraints, idempotent migrations |
| **Container** | Non-root user, healthcheck, no secrets in image, minimal base |
| **Network (Docker)** | Isolated bridge network, PostgreSQL not internet-exposed |
| **Network (AWS)** | Security group: SSH restricted, HTTP open |
| **Secrets** | Gitignored files, GitHub Actions secrets, Ansible assertions |
| **CI/CD** | Least-privilege permissions, manual production approval |

### Not Implemented (Out of Scope)
MFA, Password Reset, Email Verification, Audit Logging, Rate Limiting, HTTPS/TLS, CSRF Protection, CSP, Enterprise Secret Management, Kubernetes, Database Encryption, Automated Vulnerability Scanning.

See `docs/security/security.md` for complete details.

---

## Deployment Status

| Component | Status | Evidence |
|-----------|--------|----------|
| Flask App (SQLite) | **VALIDATED** | Tests pass, runs locally |
| Flask App (PostgreSQL) | **VALIDATED** | CI PostgreSQL tests pass |
| Admin + Hospital hierarchy | **VALIDATED** | Tests cover all admin routes |
| RECEIVED lifecycle | **VALIDATED** | Tests cover receive, notifications, protections |
| Docker Compose | **VALIDATED** | `docker compose up --build` healthy |
| Dockerfile | **VALIDATED** | CI build + healthcheck pass |
| Terraform config | **VALIDATED** | CI `fmt/validate` pass |
| Ansible playbook | **VALIDATED** | CI syntax check pass |
| CI Pipeline | **VALIDATED** | Runs on push/PR, all jobs pass |
| CD Pipeline | **CONFIGURED** | Manual dispatch, approval gated |
| **AWS Live Deployment** | **NOT EXECUTED** | Terraform apply + Ansible not run in current verification |

> ⚠️ The CD pipeline is fully configured and validated in CI, but has **not been executed** against a live AWS account in the current verification cycle. No live EC2 IP or deployment URL should be documented as current.

---

## Documentation

| Document | Description |
|----------|-------------|
| `docs/architecture/architecture.md` | System architecture, components, deployment flow, security boundaries |
| `docs/architecture/database.md` | ER diagram, table definitions, relationships, migrations |
| `docs/deployment/deployment-guide.md` | Local, Docker, Terraform, Ansible, CI/CD procedures |
| `docs/deployment/ci-cd.md` | CI/CD workflow details, jobs, secrets, verification commands |
| `docs/security/security.md` | Implemented controls, not-implemented features, threat model |
| `docs/testing/testing-report.md` | Test categories, coverage, CI execution, fixtures, results |
| `docs/submission/final-report.md` | Comprehensive college project report |
| `docs/submission/demo-guide.md` | 15-step demonstration flow |
| `docs/submission/known-limitations.md` | Honest limitation documentation |
| `docs/submission/submission-checklist.md` | Final submission verification |

---

## Known Limitations

See `docs/submission/known-limitations.md` for complete list.

**Key distinctions:**
- **Project Scope Exclusions** = Features not required (MFA, HTTPS, rate limiting, etc.)
- **Deployment Environment Limitations** = Current verification state (no live AWS deploy)

---

## License

Academic project — DevOps FA1 College Submission