# RxVerify Demonstration Guide
## 10-15 Minute College Demonstration

---

### Overview

This guide provides a structured demonstration flow for presenting RxVerify to faculty/evaluators. Total time: ~12 minutes.

**Prerequisites:**
- Local Docker Compose stack running (`docker compose up --build -d`)
- GitHub repository open in browser
- Terminal ready for commands

---

### Demo Flow

#### 1. Problem Statement (1 min)
- Open `docs/submission/final-report.md` → Section 3 (Problem Statement)
- Highlight: Paper prescriptions → forgery, no verification, no audit trail, no notifications
- State: "RxVerify replaces paper with secure digital workflow"

#### 2. Application Landing Page (1 min)
```bash
# Verify Docker is running
docker compose ps
curl http://localhost:5001/health
```
- Open browser: `http://localhost:5001`
- Show: Clean landing page with role selection
- Point out: "Three portals — Doctor, Pharmacist, Admin"

#### 3. Doctor Login & Create Prescription (2 min)
- Click **"Doctor Login"**
- Use **DEMO credentials**:
  ```
  Email: doctor@rxverify.local
  Password: doctor123
  ```
- Show: Redirect to "Issue Prescription" page
- Fill form with sample data:
  ```
  Patient Name: John Doe
  Patient Reference: UHID-12345
  Doctor Name: Dr. Meera Patel
  Clinic Name: City General Hospital
  Medicine Name: Amoxicillin
  Dosage: 500mg
  Instructions: Take 3 times daily for 7 days
  Issue Date: [today's date]
  ```
- Click **"Create Prescription"**
- Show: Redirects to verification result page with `RX-<10HEX>` ID
- **Key point**: "Unique non-sequential verification ID generated"

#### 4. Verification (1 min)
- Stay on result page — show prescription details
- Point out: "ACTIVE status, all fields intact"
- Copy the `verification_id` (e.g., `RX-A1B2C3D4E5`)

#### 5. Pharmacist Login (1 min)
- Open new browser tab/incognito window
- Go to `http://localhost:5001`
- Click **"Pharmacist Login"**
- Use **DEMO credentials**:
  ```
  Email: pharmacist@rxverify.local
  Password: pharmacist123
  ```
- Show: Redirect to "Verify Prescription" page
- Paste the `verification_id` → Click **"Verify"**
- Show: Same prescription details, ACTIVE status

#### 6. Receive Medicine (2 min)
- On verification result page (pharmacist view):
  - Show: **"Mark Medicine Received" button** (only on ACTIVE)
  - Click it
- Show: Success flash → "Medicine marked as received. Doctor and admins have been notified."
- Page now shows: **RECEIVED status**, `received_at` timestamp, pharmacist name
- **Key point**: "Terminal state — cannot be received again or revoked"

#### 7. Notification System (1 min)
- Go back to Doctor tab (or login as doctor again)
- Show: **Red notification badge** in navigation bar
- Click **"Notifications"** in nav
- Show: Notification — "Medicine for prescription RX-... has been received by pharmacist Rohan Sharma"
- Click **"Mark as read"** → badge clears
- **Key point**: "Automatic doctor + admin notifications on handoff"

#### 8. Admin Dashboard (1.5 min)
- Open new tab → `http://localhost:5001`
- Click **"Admin Login"**
- Use **DEMO credentials**:
  ```
  Email: admin@rxverify.local
  Password: admin123
  ```
- Show: Dashboard with statistics cards:
  - Hospitals: 2
  - Doctors: 1
  - Pharmacists: 1
  - Prescriptions: [count]
  - Active / Received / Revoked breakdown
- Click **"Hospitals"** in nav
- Show: Hospital list with doctor/pharmacist counts
- Click **"City General Hospital"**
- Show: Doctor (Dr. Meera Patel) with prescription count, Pharmacist (Rohan Sharma) with verification count
- Click the doctor → Show doctor's prescriptions with date filter

#### 9. Hospital Management (1 min)
- From hospital detail, note: "Admins see all hospitals; doctors/pharmacists see own only"
- Show: Two hospitals seeded (City General, Metro Medical Center)
- Explain: `users.hospital_id` FK enables hospital isolation

#### 10. Docker & PostgreSQL (1 min)
```bash
# In terminal
docker compose ps
docker compose logs rxverify | tail -10
```
- Show: Two containers running (rxverify-app, rxverify-postgres)
- Show: Health checks passing
- Explain: "PostgreSQL 16 in production parity with local SQLite"

#### 11. GitHub Actions CI/CD (1 min)
- Open GitHub repository → **Actions** tab
- Show: Latest workflow run (green checkmarks)
- Expand `postgresql-tests` job → show "98 passed"
- Expand `docker-validation` job → show health check passing
- Explain: "5 parallel CI jobs validate every push/PR"
- Show: **CD requires manual workflow_dispatch + approval gate**

#### 12. Terraform Infrastructure (1 min)
```bash
cd terraform
terraform fmt -check && echo "Format OK"
terraform validate && echo "Validate OK"
```
- Show: `main.tf` — VPC, subnet, IGW, security group, EC2
- Show: `variables.tf` — `allowed_ssh_cidr` default `0.0.0.0/0` (must override)
- Explain: "Infrastructure as Code — reproducible AWS provisioning"

#### 13. Ansible Deployment (1 min)
```bash
cd ansible
ansible-playbook --syntax-check deploy.yml && echo "Syntax OK"
```
- Show: `deploy.yml` — assertions, Docker install, file copy, build, deploy, health check
- Show: `generate_inventory.py` — Terraform output → Ansible inventory
- Show: `secrets.yml.example` — secure secrets template
- Explain: "Configuration management — idempotent, assertion-gated"

#### 14. Architecture Diagram (0.5 min)
- Open `docs/architecture/architecture.md`
- Scroll to **Mermaid architecture diagram** (Section 2)
- Briefly explain: Factory → Blueprints → DB Abstraction → Docker → Terraform → Ansible → CI/CD

#### 15. Database ER Diagram (0.5 min)
- Open `docs/architecture/database.md`
- Scroll to **Mermaid ER diagram** (Section 2)
- Highlight: 4 tables, hospital→users, users→notifications, prescriptions→notifications, dual doctor/pharmacist linking

---

### Demo Credentials Summary

| Role | Email | Password | Purpose |
|------|-------|----------|---------|
| **Doctor** | `doctor@rxverify.local` | `doctor123` | Create/revoke prescriptions, view notifications |
| **Pharmacist** | `pharmacist@rxverify.local` | `pharmacist123` | Verify, mark received |
| **Admin** | `admin@rxverify.local` | `admin123` | Dashboard, hospital management |

> ⚠️ **These are DEVELOPMENT/DEMO credentials only.** Never use in production. Production requires explicit admin creation via environment variables or manual database insertion.

---

### Talking Points for Q&A

| Topic | Key Message |
|-------|-------------|
| **Why Flask?** | Lightweight, explicit, great for learning; factory pattern enables testing |
| **Why dual database?** | SQLite for zero-config dev; PostgreSQL for production parity; abstraction layer ensures identical behavior |
| **Why not FK for doctor_name?** | Audit integrity — prescription records must be immutable; doctor renames shouldn't alter issued prescriptions |
| **How is RBAC enforced?** | Server-side decorators on every route; not just UI hiding |
| **What prevents double-receive?** | Status check in `receive_medicine()`: blocks if `status != 'active'` |
| **How are notifications deduplicated?** | `_create_notification_if_not_exists()` checks user+prescription+message pattern |
| **Why manual CD approval?** | Safety gate — production changes require human review |
| **What's the `allowed_ssh_cidr`?** | Restricts SSH to your IP; default 0.0.0.0/0 is for CI validation only |
| **How do secrets work?** | `.env`/`secrets.yml` gitignored; GitHub Secrets for CI/CD; Ansible assertions fail on defaults |

---

### Troubleshooting During Demo

| Issue | Fix |
|-------|-----|
| Port 5001 in use | `docker compose down && docker compose up --build -d` |
| Health check fails | Wait 10s, check `docker compose logs rxverify` |
| Database locked | `docker compose down -v && docker compose up --build -d` |
| Tests fail locally | Ensure PostgreSQL not required for default test run (uses SQLite) |

---

### Post-Demo Cleanup

```bash
# Stop containers (keep data)
docker compose down

# Full reset (remove volumes)
docker compose down -v
```

---

### Files to Reference During Demo

| File | Section |
|------|---------|
| `docs/submission/final-report.md` | Problem statement, objectives, results |
| `docs/architecture/architecture.md` | Architecture diagram, component status |
| `docs/architecture/database.md` | ER diagram, table definitions |
| `docs/security/security.md` | Implemented controls, not-implemented table |
| `docs/deployment/ci-cd.md` | Pipeline diagram, job details |
| `docs/testing/testing-report.md` | Test categories, 98 passed |
| `.github/workflows/ci-cd.yml` | Actual workflow YAML |
| `terraform/main.tf` | AWS resources |
| `ansible/deploy.yml` | Deployment playbook |

---

*Demo Guide v1.0 — 2026-08-21*