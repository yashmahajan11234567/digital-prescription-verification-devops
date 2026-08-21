# RxVerify Security Documentation

## 1. Implemented Security Controls

### 1.1 Authentication & Session Management

| Control | Implementation | Location |
|---------|----------------|----------|
| **Password Hashing** | Werkzeug `generate_password_hash` / `check_password_hash` (PBKDF2-SHA256) | `src/models/user.py:55-57`, `src/auth/routes.py:21` |
| **Session Authentication** | Flask signed session cookie (itsdangerous), stores `user_id`, `name`, `role` | `src/auth/routes.py:22-23` |
| **Session Invalidation** | `session.clear()` on logout | `src/auth/routes.py:38` |
| **Generic Error Messages** | "Incorrect credentials or account role" — no email enumeration | `src/auth/routes.py:32` |

### 1.2 Role-Based Access Control (RBAC)

| Control | Implementation | Location |
|---------|----------------|----------|
| **Role Validation** | `VALID_ROLES = {"doctor", "pharmacist", "admin"}` enforced at decorator definition | `src/decorators.py:9` |
| **Route-Level Enforcement** | Server-side decorators: `@require_role`, `@require_any_role`, `@require_admin` | `src/decorators.py`, all route files |
| **Cross-Role Prevention** | Doctor cannot access pharmacist routes, admin cannot receive medicine, etc. | Verified in `tests/test_task6_integration.py` |

### 1.3 Hospital Isolation

| Control | Implementation | Location |
|---------|----------------|----------|
| **Hospital Affiliation** | `users.hospital_id` FK → hospitals; admins have NULL | `src/__init__.py:223-231`, `src/seeds.py` |
| **Admin Oversight** | Admin sees all hospitals/users/prescriptions; doctors/pharmacists see own hospital | `src/admin/routes.py` queries |
| **Prescription Visibility** | Doctor prescriptions filtered by `doctor_name`; admin can filter by hospital | `src/doctor/routes.py`, `src/admin/routes.py` |

### 1.4 Insecure Direct Object Reference (IDOR) Protection

| Control | Implementation | Location |
|---------|----------------|----------|
| **Notification Ownership** | `mark_notification_read` verifies `notification.user_id == session.user_id` | `src/models/notifications.py:106-108` |
| **Prescription Access** | Verification view accepts any authenticated role; receive restricted to pharmacist | `src/pharmacist/routes.py:29`, `src/pharmacist/routes.py:75` |
| **Admin Routes** | All under `@require_admin()` — non-admins redirected | `src/admin/routes.py` |

### 1.5 SQL Injection Prevention

| Control | Implementation | Location |
|---------|----------------|----------|
| **Parameterized Queries** | All queries use `?` placeholders; PostgreSQL adapter converts to `%s` | `src/__init__.py:57-67`, all route files |
| **No String Interpolation** | Zero f-string/format SQL in codebase | Verified by code inspection |
| **Abstraction Layer** | `execute(query, params)` enforces separation | `src/__init__.py:33-35` |

### 1.6 Input Validation

| Control | Implementation | Location |
|---------|----------------|----------|
| **Prescription Required Fields** | All 7 fields validated server-side, flash error if missing | `src/doctor/routes.py:18-31` |
| **Date Validation** | `date.fromisoformat()` with try/except | `src/doctor/routes.py:34-37` |
| **Verification ID Format** | Uppercase, prefix check in routes | `src/pharmacist/routes.py:21`, `src/pharmacist/routes.py:33` |
| **Email Normalization** | `strip().lower()` on all email inputs | `src/auth/routes.py:16`, `src/models/user.py:91` |
| **Role Whitelist** | `role in VALID_ROLES` at decorator + model layer | `src/decorators.py:14-15`, `src/models/user.py:88-89` |

### 1.7 Prescription Lifecycle Integrity

| Control | Implementation | Location |
|---------|----------------|----------|
| **Status Transition Rules** | Only ACTIVE → RECEIVED; ACTIVE → REVOKED; RECEIVED/REVOKED terminal | `src/pharmacist/routes.py:90-103` |
| **Duplicate Receive Block** | Checks `status == 'received'` before update | `src/pharmacist/routes.py:91-93` |
| **Revoked Receive Block** | Checks `status == 'revoked'` before update | `src/pharmacist/routes.py:95-98` |
| **Data Preservation** | RECEIVED/REVOKED retains all original fields + adds metadata | `src/pharmacist/routes.py:110-114` |

### 1.8 Notification Security

| Control | Implementation | Location |
|---------|----------------|----------|
| **Ownership Enforcement** | `mark_notification_read` filters by `user_id` | `src/models/notifications.py:106` |
| **Deduplication** | `_create_notification_if_not_exists` prevents duplicate alerts | `src/pharmacist/routes.py:47-71` |
| **No External Delivery** | In-app only — no email/SMS attack surface | `src/pharmacist/routes.py:121-149` |

### 1.9 Container Security (Docker)

| Control | Implementation | Location |
|---------|----------------|----------|
| **Non-Root User** | `appuser` UID/GID created, `USER appuser` | `Dockerfile:23, 39` |
| **Healthcheck** | HTTP `/health` endpoint, 30s interval | `Dockerfile:43-44` |
| **No Secrets in Image** | Secrets via environment variables at runtime | `docker-compose.yml:27-38` |
| **Minimal Base** | `python:3.12-slim` — reduced attack surface | `Dockerfile:1, 15` |

### 1.10 Network Isolation

| Layer | Control |
|-------|---------|
| **Docker Compose** | `rxverify-network` bridge; PostgreSQL port 5432 not exposed to host (only 5433 for debugging) |
| **AWS Security Group** | Ingress: SSH (`allowed_ssh_cidr`), HTTP (0.0.0.0/0); Egress: 0.0.0.0/0 all |
| **PostgreSQL** | Runs in Docker network, not directly internet-accessible in production |

### 1.11 Secret Handling

| Control | Implementation |
|---------|----------------|
| **Development** | `.env.example` documents variables; `.env` gitignored |
| **Docker Compose** | Defaults in `docker-compose.yml` (marked `change-me`), overridden by `.env` |
| **Ansible** | `secrets.yml` (gitignored) with assertions for minimum length & non-defaults |
| **CI/CD** | GitHub Actions secrets for AWS credentials, SSH key; `POSTGRES_PASSWORD` hardcoded for CI only |
| **Production Config** | `ProductionConfig` requires `DATABASE_URL` and `SECRET_KEY` env vars (`config.py:38-41`) |

### 1.12 Production Configuration Validation

| Control | Implementation |
|---------|----------------|
| **Config Class** | `ProductionConfig.__init__` raises `ValueError` if `DATABASE_URL` or `SECRET_KEY` missing |
| **Ansible Assertions** | Fail-fast if `app_secret_key` < 32 chars or default; `postgres_password` < 16 chars or default |
| **Docker Healthcheck** | Validates app reaches `/health` before marking healthy |

### 1.13 AWS Security Group

```hcl
# terraform/main.tf:73-100
ingress {
  description = "SSH only from the project owner current public IP"
  from_port   = 22
  to_port     = 22
  protocol    = "tcp"
  cidr_blocks = [var.allowed_ssh_cidr]  # DEFAULT 0.0.0.0/0 — MUST OVERRIDE
}

ingress {
  description = "RxVerify website"
  from_port   = 80
  to_port     = 80
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0"]
}
```

---

## 2. Security Features NOT Implemented

> ⚠️ **The following are explicitly NOT implemented** in the current project scope. They are documented here to prevent false claims during evaluation.

| Feature | Status | Notes |
|---------|--------|-------|
| **Multi-Factor Authentication (MFA)** | ❌ Not implemented | Username/password only |
| **Password Reset / Forgot Password** | ❌ Not implemented | No email delivery system |
| **Email Verification** | ❌ Not implemented | No email infrastructure |
| **Audit Logging** | ❌ Not implemented | No request/access logs persisted |
| **Rate Limiting** | ❌ Not implemented | No throttling on login/verify endpoints |
| **HTTPS / TLS Termination** | ❌ Not implemented | HTTP only (port 80/5000/5001); no certificates managed |
| **CSRF Protection** | ❌ Not implemented | No CSRF tokens on forms (Flask-WTF not used) |
| **Content Security Policy (CSP)** | ❌ Not implemented | No CSP headers |
| **Secure Headers (HSTS, X-Frame-Options, etc.)** | ❌ Not implemented | Default Flask headers only |
| **Enterprise Secret Management** | ❌ Not implemented | No Vault, AWS Secrets Manager, etc. |
| **Kubernetes / Orchestration** | ❌ Not implemented | Single EC2 + Docker only |
| **Database Encryption at Rest** | ❌ Not implemented | Relies on AWS EBS / Docker volume defaults |
| **Database Encryption in Transit** | ❌ Not implemented | PostgreSQL in Docker network unencrypted |
| **Automated Vulnerability Scanning** | ❌ Not implemented | No SCA/DAST in CI |
| **Penetration Testing** | ❌ Not performed | Not in scope |

---

## 3. Threat Model Summary

| Asset | Threats Mitigated | Residual Risk |
|-------|-------------------|---------------|
| **Credentials** | Hashing, generic errors, session invalidation | Brute force (no rate limit) |
| **Prescription Data** | Parameterized queries, RBAC, lifecycle rules | No encryption at rest/transit |
| **Admin Functions** | `@require_admin`, hospital isolation | No MFA for admin |
| **Network** | Security group SSH restriction, Docker network isolation | HTTP plaintext |
| **Secrets** | Gitignore, CI secrets, Ansible assertions | No secret rotation |
| **Container** | Non-root, healthcheck, minimal base | No read-only rootfs, no seccomp |

---

## 4. Compliance Notes

- **Educational project** — Not production-hardened
- **No PHI/PII protection guarantees** — Uses fictional patient data only
- **HTTPS required** for any real deployment (reverse proxy: nginx/Traefik + cert-manager)
- **Rate limiting required** for any internet-exposed deployment
- **Audit logging required** for regulated environments

---

*Last updated: 2026-08-21 — Based on Tasks 1–9 code inspection*