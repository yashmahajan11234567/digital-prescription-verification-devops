# RxVerify Deployment Guide

## 1. Local Development

### 1.1 Prerequisites

- Python 3.12+
- Git
- Optional: Docker Desktop (for containerized workflow)

### 1.2 Virtual Environment Setup

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
```

### 1.3 Environment Configuration

```bash
# Copy example and edit
cp .env.example .env
# Edit .env with your values (FLASK_ENV=development, SECRET_KEY, etc.)
```

For SQLite (default), no further config needed. Database file created at `instance/prescriptions.db`.

### 1.4 Run Flask Development Server

```bash
flask --app app run --debug
# Or:
python -m flask --app app run --debug
```

Open `http://127.0.0.1:5000`

### 1.5 Demo Credentials (Development Only)

| Role | Email | Password |
|------|-------|----------|
| Doctor | `doctor@rxverify.local` | `doctor123` |
| Pharmacist | `pharmacist@rxverify.local` | `pharmacist123` |
| Admin | `admin@rxverify.local` | `admin123` |

> ⚠️ These are **development/demo credentials only**. Never use in production. Production must use `seeds.py` environment-variable seeding or explicit admin creation.

### 1.6 Run Tests

```bash
# All tests (98 tests)
python -m pytest tests/ -q

# With coverage
python -m pytest tests/ --cov=src --cov-report=term-missing
```

---

## 2. Docker Deployment (Local)

### 2.1 Prerequisites

- Docker Engine 24+
- Docker Compose v2+

### 2.2 Configuration

```bash
cp .env.example .env
# Edit .env — at minimum change:
# POSTGRES_PASSWORD=your-secure-password
# SECRET_KEY=your-long-random-secret
```

### 2.3 Start Stack

```bash
# Validate config
docker compose config

# Build and start in background
docker compose up --build -d

# Check status
docker compose ps

# View logs
docker compose logs -f

# Verify health
curl http://localhost:5001/health
# Expected: {"status": "ok"}
```

### 2.4 Service Details

| Service | Host Port | Container Port | Notes |
|---------|-----------|----------------|-------|
| rxverify (Flask/Gunicorn) | 5001 | 5000 | Port 5001 avoids macOS Control Center conflict |
| postgres | 5433 | 5432 | Exposed for debugging; internal network uses 5432 |

### 2.5 Data Persistence

- `prescription_data` volume → `/app/instance` (Flask instance folder)
- `postgres_data` volume → `/var/lib/postgresql/data`

To reset completely:
```bash
docker compose down -v
```

### 2.6 Stop Stack

```bash
docker compose down        # Keeps volumes
docker compose down -v     # Removes volumes (data loss)
```

---

## 3. Terraform Infrastructure (AWS)

### 3.1 Prerequisites

- AWS CLI configured with profile (default: `fa1`)
- Terraform 1.5+
- Valid EC2 key pair in target region

### 3.2 Configure Variables

```bash
cd terraform

# Find your public IP
curl -4 ifconfig.me
# Example output: 203.0.113.10

# Create tfvars from example
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars:
# allowed_ssh_cidr = "203.0.113.10/32"  # YOUR IP/32
```

### 3.3 Provision Infrastructure

```bash
# Format check
terraform fmt -check -recursive

# Initialize (downloads providers)
terraform init

# Validate syntax
terraform validate

# Preview changes
terraform plan

# Apply (creates EC2, VPC, SG, etc.)
terraform apply
```

### 3.4 Outputs

After `apply`, record:
```bash
terraform output instance_public_ip
terraform output website_url
```

### 3.5 Cleanup

```bash
terraform destroy
```

---

## 4. Ansible Deployment (To EC2)

### 4.1 Prerequisites

- Terraform apply completed (EC2 running)
- SSH private key for EC2 key pair
- Ansible 2.14+ (`pip install ansible-core`)
- Community Docker collection (`ansible-galaxy collection install -r requirements.yml`)

### 4.2 Prepare Local-Only Files

```bash
cd ansible

# Inventory (auto-generated from Terraform)
python generate_inventory.py --tf-output-dir ../terraform --key-file ~/.ssh/your-key.pem > inventory.ini

# Secrets
cp secrets.yml.example secrets.yml
# Edit secrets.yml:
# app_secret_key: "YOUR_32+_CHAR_HEX_STRING"  # openssl rand -hex 32
# postgres_password: "YOUR_16+_CHAR_STRING"   # openssl rand -hex 16
```

### 4.3 Deploy

```bash
# Test connectivity
ansible all -m ping

# Deploy
ansible-playbook -i inventory.ini deploy.yml
```

### 4.4 Verify Deployment

After playbook completes, open the `website_url` from Terraform output:
- Health: `http://<EC2_IP>/health`
- Application: `http://<EC2_IP>/`

---

## 5. CI/CD Pipeline (GitHub Actions)

### 5.1 Automatic CI (Push/PR to main)

Runs on every push/PR to `main`:

| Job | Purpose |
|-----|---------|
| `validation` | Python imports, basic sanity |
| `postgresql-tests` | Full pytest suite against live PostgreSQL 16 |
| `docker-validation` | `docker compose config`, build, up, health, smoke |
| `terraform-validation` | `fmt -check`, `init -backend=false`, `validate` |
| `ansible-validation` | Syntax check, config dump |

**Trigger:** Automatic on push/PR to `main`.

### 5.2 Manual CD (Workflow Dispatch)

Production deployment requires **manual trigger** with approval:

1. Go to GitHub Actions → "CI/CD Pipeline" → "Run workflow"
2. Select environment: `production`
3. **Terraform Plan** runs → uploads plan artifact
4. **Manual Approval Gate** (GitHub Environment: `production`)
5. **Terraform Apply** runs (requires AWS credentials secrets)
6. **Ansible Deploy** runs (requires SSH private key secret)
7. **Post-Deploy Health & Smoke Checks**

### 5.3 Required GitHub Secrets

| Secret | Used By | Description |
|--------|---------|-------------|
| `AWS_ACCESS_KEY_ID` | Terraform Apply, Ansible Deploy | AWS IAM user with EC2/VPC permissions |
| `AWS_SECRET_ACCESS_KEY` | Terraform Apply, Ansible Deploy | Corresponding secret key |
| `SSH_PRIVATE_KEY` | Ansible Deploy | EC2 key pair private key (PEM) |

### 5.4 Required GitHub Variables

| Variable | Used By | Description |
|----------|---------|-------------|
| `AWS_REGION` | Terraform Apply, Ansible Deploy | e.g., `ap-south-1` |

### 5.5 CI/CD Diagram

```mermaid
flowchart TD
    subgraph CI [Continuous Integration - Automatic]
        A1[Validation] --> A2[PostgreSQL Tests]
        A1 --> A3[Docker Validation]
        A1 --> A4[Terraform Validation]
        A1 --> A5[Ansible Validation]
    end
    
    subgraph CD [Continuous Deployment - Manual Dispatch]
        B1[Terraform Plan] --> B2[Approval Gate<br/>environment: production]
        B2 --> B3[Terraform Apply]
        B3 --> B4[Ansible Deploy]
        B4 --> B5[Health + Smoke Checks]
    end
    
    CI -.->|All pass enables| CD
```

---

## 6. Architecture-Specific Notes

### 6.1 Local vs Production Differences

| Aspect | Local (Docker Compose) | Production (Ansible on EC2) |
|--------|------------------------|----------------------------|
| **Database** | PostgreSQL in container | PostgreSQL in container (on EC2) |
| **App Port** | 5001 (host) | 80 (host) → 5000 (container) |
| **Network** | `rxverify-network` bridge | `rxverify-network` bridge |
| **Secrets** | `.env` file | `ansible/secrets.yml` (gitignored) |
| **Gunicorn Workers** | 2 | 2 |
| **Healthcheck** | HTTP localhost:5000/health | HTTP localhost:5000/health |

### 6.2 Database Connection Strings

| Environment | DATABASE_URL |
|-------------|--------------|
| Local SQLite | `sqlite:///instance/prescriptions.db` |
| Docker Compose | `postgresql://postgres:password@postgres:5432/rxverify` |
| Production (Ansible) | `postgresql://postgres:{{postgres_password}}@postgres:5432/rxverify` |

---

*Last updated: 2026-08-21 — Validated against actual Dockerfile, docker-compose.yml, Terraform, Ansible, and CI/CD workflow*