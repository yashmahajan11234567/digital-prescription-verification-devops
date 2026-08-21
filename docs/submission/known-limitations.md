# RxVerify Known Limitations

This document records genuine limitations of the current implementation, categorized by type.

---

## 1. Deployment Environment Limitations

These are limitations of the current verification environment, not the project design.

| Limitation | Impact | Resolution |
|------------|--------|------------|
| **No live AWS deployment verified** | Terraform apply + Ansible deploy not executed in current cycle | Run `terraform apply` + `ansible-playbook` with valid AWS credentials to verify end-to-end |
| **Ansible local syntax check only** | CI validates syntax but not full playbook execution against EC2 | Execute playbook against live instance for full validation |
| **SSH CIDR default = 0.0.0.0/0** | Security group allows SSH from anywhere (dev convenience) | Override `allowed_ssh_cidr` with your IP/32 in `terraform.tfvars` for production |
| **CI PostgreSQL password hardcoded** | `testpassword` used in CI only | Production uses Ansible `secrets.yml` with generated password (≥16 chars) |
| **No production HTTPS endpoint** | Application serves HTTP on port 80/5000/5001 | Deploy behind reverse proxy (nginx/Traefik) with TLS certificates |

---

## 2. Security Features Not Implemented (Project Scope Exclusions)

These features are **intentionally outside the current project scope** for academic deliverable. They are documented here to prevent false claims.

| Feature | Status | Reason |
|---------|--------|--------|
| **Multi-Factor Authentication (MFA)** | ❌ Not implemented | Username/password only; TOTP would require additional dependency and setup flow |
| **Password Reset / Forgot Password** | ❌ Not implemented | No email delivery infrastructure; would require SMTP service and token flow |
| **Email Verification** | ❌ Not implemented | No email infrastructure; registration is admin-seeded only |
| **Audit Logging** | ❌ Not implemented | No request/access log persistence; would need structured logging + storage |
| **Rate Limiting** | ❌ Not implemented | No throttling on login/verify endpoints; Flask-Limiter not integrated |
| **HTTPS / TLS Termination** | ❌ Not implemented | HTTP only; production requires reverse proxy + cert management (Let's Encrypt) |
| **CSRF Protection** | ❌ Not implemented | No CSRF tokens on forms; Flask-WTF not used |
| **Content Security Policy (CSP)** | ❌ Not implemented | No CSP headers; default Flask headers only |
| **Secure Headers (HSTS, X-Frame-Options, etc.)** | ❌ Not implemented | No security header middleware |
| **Enterprise Secret Management** | ❌ Not implemented | No Vault, AWS Secrets Manager, Azure Key Vault integration |
| **Kubernetes / Orchestration** | ❌ Not implemented | Single EC2 + Docker only; no K8s, ECS, or Swarm |
| **Database Encryption at Rest** | ❌ Not implemented | Relies on AWS EBS encryption / Docker volume defaults |
| **Database Encryption in Transit** | ❌ Not implemented | PostgreSQL in Docker network unencrypted; would need SSL mode |
| **Automated Vulnerability Scanning** | ❌ Not implemented | No SAST/DAST/SCA in CI pipeline |
| **Penetration Testing** | ❌ Not performed | Not in academic scope |

> **Note:** These are **project scope exclusions**, not bugs or oversights. The academic deliverable focuses on core DevOps pipeline and application functionality.

---

## 3. Application Functional Limitations

| Limitation | Impact | Notes |
|------------|--------|-------|
| **Doctor lookup by name only** | `prescriptions.doctor_name` matches `users.name` + role | Denormalized for audit integrity; not a FK. Name changes don't affect issued prescriptions. |
| **No patient portal** | Patients cannot view their own prescriptions | Out of scope; verification is pharmacist/doctor/admin only |
| **No prescription editing** | Only create/revoke/receive; no amendment | Intentional — prescriptions are immutable after creation |
| **No expiration/auto-revoke** | Prescriptions stay ACTIVE until manual action | Could add `expires_at` field + scheduled job |
| **Single hospital per user** | `hospital_id` is scalar FK | No multi-hospital affiliation for doctors |
| **No drug interaction checking** | Pure verification system | Clinical decision support out of scope |
| **In-app notifications only** | No email, SMS, push | Lightweight by design; no external dependencies |

---

## 4. Technical Debt / Code Quality Notes

| Area | Observation | Priority |
|------|-------------|----------|
| **Duplicate `notifications` table CREATE** | `init_db()` creates notifications table twice (lines 346-353 and 391-408) | Low — idempotent, harmless |
| **`doctor_name` denormalization** | Text match instead of FK | Intentional for audit trail; documented |
| **PostgreSQL sequence conflicts** | Handled in seeds with `ON CONFLICT` | Low — workaround for IDENTITY vs seed |
| **Hardcoded test passwords** | Dev seeds use `doctor123`, `pharmacist123`, `admin123` | Development only; production uses env vars |
| **No Alembic migrations** | Schema changes via idempotent `init_db()` | Acceptable for project scale; Alembic would add complexity |

---

## 5. Testing Gaps

| Gap | Current State | Future Enhancement |
|-----|---------------|-------------------|
| **E2E in CI** | Docker validation only (health + smoke) | Run full pytest suite in Docker Compose in CI |
| **Load testing** | None | Locust/k6 for concurrent user simulation |
| **Security scanning** | None | Bandit (SAST), Trivy (container), OWASP ZAP (DAST) |
| **Browser/UI tests** | None | Playwright/Cypress for frontend flows |
| **Chaos/resilience** | None | Network partition, DB failure simulation |

---

## 6. Documentation Gaps

| Gap | Status |
|-----|--------|
| **API spec (OpenAPI/Swagger)** | Not generated — no REST API, only server-rendered templates |
| **Runbook/operations guide** | Basic deployment guide exists; no incident response procedures |
| **Capacity planning** | Not documented — t3.micro baseline only |

---

## Summary Classification

| Category | Count | Severity |
|----------|-------|----------|
| Deployment Environment | 5 | Medium — blocks production readiness |
| Security (Scope Exclusions) | 15 | Low — documented as out of scope |
| Application Functional | 7 | Low — design decisions |
| Technical Debt | 5 | Low — non-blocking |
| Testing Gaps | 5 | Medium — would improve confidence |
| Documentation Gaps | 3 | Low — nice to have |

---

**Key Distinction:**
- **Project Scope Exclusions** = Features not required for academic deliverable (security hardening, enterprise integrations)
- **Deployment Environment Limitations** = Current verification state (not yet run against live AWS)

Both are honestly documented. Neither represents a defect in the implemented work.

---

*Last updated: 2026-08-21*