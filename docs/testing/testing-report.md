# RxVerify Testing Report

## 1. Executive Summary

| Metric | Value |
|--------|-------|
| **Test Framework** | pytest 8.x |
| **Total Tests (pytest suite)** | **98 passed** |
| **Coverage Areas** | Auth, RBAC, Prescriptions, Hospitals, Notifications, IDOR, Validation, PostgreSQL, Regression, Integration, Unit, Routes |
| **Standalone Scripts** | 1 E2E Docker workflow script (not counted as pytest tests) |

**Command:** `python -m pytest tests/ -q`
**Result:** `98 tests passed`

---

## 2. Test Suite Structure

```
tests/
├── conftest.py                 # Shared fixtures + helpers
├── test_app.py                 # 4 tests — app basics, health
├── test_auth.py                | 35 tests — authentication, users, RBAC
├── test_regression.py          # 25 tests — hospital seeding, notifications
├── test_task6_integration.py   # 20 tests — Task 6 coverage gaps
├── integration/
│   └── test_prescription_flow.py  # 4 tests — doctor→pharmacist flow
├── unit/
│   └── test_routes.py          # 10 tests — individual route behavior
└── e2e_docker_workflow.py      # Standalone script (not pytest)
```

**Total pytest test functions: 98**

---

## 3. Test Categories & Counts

| Category | File | Tests | Description |
|----------|------|-------|-------------|
| **App Core** | `test_app.py` | 4 | Home page, health endpoint, basic routing |
| **Authentication** | `test_auth.py` | 35 | Login/logout, password hashing, role validation, user CRUD, inactive users |
| **RBAC/Authorization** | `test_auth.py`, `test_task6_integration.py` | Covered in above | Decorator enforcement, cross-role redirects |
| **Prescription Lifecycle** | `test_task6_integration.py`, `integration/test_prescription_flow.py` | 24 | Issue, verify, revoke, receive, status transitions |
| **Hospital Hierarchy** | `test_regression.py` | 25 | Hospital seeding, admin dashboard, doctor/pharmacist counts |
| **Notifications** | `test_regression.py`, `test_task6_integration.py` | Covered | Creation, read/unread, deduplication, ownership |
| **IDOR Protection** | `test_task6_integration.py` | Covered | Notification mark-read ownership, cross-user access |
| **Input Validation** | `test_task6_integration.py` | Covered | Malformed IDs, SQL-like strings, non-existent resources |
| **PostgreSQL Compatibility** | `postgresql-tests` CI job | 98 | All tests run against live PostgreSQL 16 in CI |
| **Regression** | `test_regression.py` | 25 | Seeding idempotency, hospital UNIQUE constraint, notification handling |
| **Unit Routes** | `unit/test_routes.py` | 10 | Route-level behavior with test client |

---

## 4. Key Test Coverage Details

### 4.1 Authentication Tests (`test_auth.py` - 35 tests)

- Login success for all three roles
- Login failure: wrong password, wrong role, inactive user
- Logout clears session
- User model: create, read by email/id, update, delete, list
- Password hashing verification
- Role validation (valid/invalid roles)
- Active/inactive status toggle
- Generic error message prevents email enumeration

### 4.2 Prescription Flow Tests

**Integration (`integration/test_prescription_flow.py` - 4 tests):**
- Doctor → create prescription → redirect to result
- Pharmacist → verify prescription → data intact
- Full doctor→pharmacist handoff

**Task 6 Integration (`test_task6_integration.py` - 20 tests):**
- Revoke: ACTIVE → REVOKED, data intact, idempotent revoke
- Receive authorization: non-pharmacist roles rejected (403/redirect)
- Admin route authorization: non-admin rejected
- Notification IDOR: user cannot mark another's notification read
- Input security: malformed IDs, SQL-injection-like strings, non-existent prescriptions

### 4.3 Hospital & Admin Tests (`test_regression.py` - 25 tests)

- Hospital seeding idempotency (upsert behavior)
- UNIQUE constraint on hospitals.name (PostgreSQL + SQLite)
- Admin dashboard statistics accuracy
- Hospital list with doctor/pharmacist counts
- Hospital detail: doctors with prescription counts, pharmacists with verification counts
- Doctor detail with date filtering
- Notification creation on receive (doctor + admins)
- Notification read/unread state
- Duplicate receive rejection
- Revoked receive rejection

### 4.4 Regression Tests

- `seed_development_users` idempotency (no duplicates on re-run)
- Hospital UNIQUE constraint migration safety
- PostgreSQL sequence conflict handling
- Notification deduplication logic

### 4.5 Unit Route Tests (`unit/test_routes.py` - 10 tests)

- Home page loads
- Health endpoint returns `{"status": "ok"}`
- Login page renders per role
- Protected routes redirect unauthenticated
- Role-specific redirects

---

## 5. Standalone Verification Scripts (Not Pytest)

| Script | Purpose | Run Method |
|--------|---------|------------|
| `tests/e2e_docker_workflow.py` | Full E2E against live Docker Compose stack (health, login, create, verify, receive, notifications) | `python tests/e2e_docker_workflow.py` (requires `docker compose up`) |
| `test_fresh_table.py` | PostgreSQL seeding verification (requires DB on 5433) | Manual |
| `test_postgres_seeding.py` | PostgreSQL seeding verification | Manual |
| `test_truncate_table.py` | Table truncation behavior | Manual |
| `test_notifications.py` | Notification flow debug | Manual |
| `debug_*.py` / `replicate_test.py` / `test_bug.py` | Debug fixtures | Manual |

> **Note:** Only `tests/e2e_docker_workflow.py` is a structured E2E verification. The others are debug/artifact scripts from development.

---

## 6. CI Test Execution

### 6.1 GitHub Actions: `postgresql-tests` Job

```yaml
services:
  postgres:
    image: postgres:16-alpine
    env:
      POSTGRES_DB: rxverify
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: testpassword
steps:
  - pytest tests/ -q --tb=short -x
    env:
      DATABASE_URL: postgresql://postgres:testpassword@localhost:5432/rxverify
      FLASK_ENV: testing
      SECRET_KEY: test-secret-key
      TESTING: "1"
```

- Runs **all 98 pytest tests** against live PostgreSQL 16
- Validates SQLite/PostgreSQL parity
- Fails fast on first error (`-x`)

### 6.2 Docker Validation Job

```yaml
- docker compose up -d --build
- curl health endpoint
- (smoke test only, not full pytest suite)
```

---

## 7. Test Fixtures & Helpers

### 7.1 `conftest.py` Fixtures

```python
@pytest.fixture()
def client(tmp_path: Path):
    """Test client with isolated SQLite file database."""
    db_path = tmp_path / "test.db"
    app = create_app({
        "TESTING": True,
        "DATABASE_URL": f"sqlite:///{db_path}",
        "SECRET_KEY": "test",
    })
    # Seeds: doctor, pharmacist, admin, inactive_doctor
    with app.app_context():
        db = app.get_db()
        create_user(...)
    return app.test_client()
```

### 7.2 Helper Functions

```python
def prescription_form() -> dict:
    """Valid prescription data for tests."""
    return {...}

def login(client, role: str):
    """Log in test client as role."""
    credentials = {
        "doctor": {"email": "doctor@rxverify.local", "password": "doctor123"},
        "pharmacist": {"email": "pharmacist@rxverify.local", "password": "pharmacist123"},
        "admin": {"email": "admin@rxverify.local", "password": "admin123"},
    }
    return client.post(f"/login/{role}", data=credentials[role])
```

---

## 8. Test Execution Commands

```bash
# Run all pytest tests (authoritative)
python -m pytest tests/ -q

# Run with verbose output
python -m pytest tests/ -v

# Run specific category
python -m pytest tests/test_auth.py -q
python -m pytest tests/test_task6_integration.py -q

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Run E2E Docker workflow (requires docker compose up)
python tests/e2e_docker_workflow.py

# CI simulation (PostgreSQL)
docker run -d --name pg -e POSTGRES_PASSWORD=test -e POSTGRES_DB=rxverify -p 5432:5432 postgres:16-alpine
sleep 10
DATABASE_URL=postgresql://postgres:test@localhost:5432/rxverify FLASK_ENV=testing SECRET_KEY=test TESTING=1 python -m pytest tests/ -q
docker stop pg && docker rm pg
```

---

## 9. Verification Results (Current)

```
$ python -m pytest tests/ -q
........................................................................ [ 73%]
..........................                                               [100%]
98 passed in 141.51s
```

All tests pass. No flaky tests observed. PostgreSQL parity validated in CI.

---

## 10. Known Test Gaps (Future Scope)

| Area | Current Coverage | Gap |
|------|------------------|-----|
| **E2E in CI** | Docker validation only | Full pytest suite in Docker not run in CI |
| **Load Testing** | None | Not in scope |
| **Security Scanning** | None | No SAST/DAST |
| **Browser/UI Tests** | None | Not in scope |
| **Chaos/Resilience** | None | Not in scope |

---

*Last updated: 2026-08-21 — Based on `python -m pytest tests/ -q` execution*