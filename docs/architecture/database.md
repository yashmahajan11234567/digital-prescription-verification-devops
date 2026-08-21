# RxVerify Database Schema

## 1. Overview

RxVerify uses a relational schema with four tables supporting dual-database compatibility:
- **SQLite** — Local development, testing (`sqlite:///instance/prescriptions.db`, `:memory:`)
- **PostgreSQL** — Production, Docker, CI (`postgresql://...`)

All migrations are **idempotent** and work identically on both backends via the abstraction layer in `src/__init__.py`.

---

## 2. Entity Relationship Diagram

```mermaid
erDiagram
    HOSPITALS ||--o{ USERS : "has"
    USERS ||--o{ NOTIFICATIONS : "receives"
    PRESCRIPTIONS ||--o{ NOTIFICATIONS : "references"
    USERS ||--o{ PRESCRIPTIONS : "issued_by (doctor_name)"
    USERS ||--o{ PRESCRIPTIONS : "received_by (FK)"

    HOSPITALS {
        integer id PK
        string name UK
        string address
        string phone
        string email
        string created_at
    }

    USERS {
        integer id PK
        string email UK
        string name
        string password_hash
        string role CHECK
        boolean is_active
        string created_at
        string updated_at
        integer hospital_id FK
    }

    PRESCRIPTIONS {
        integer id PK
        string verification_id UK
        string patient_name
        string patient_reference
        string doctor_name
        string clinic_name
        string medicine_name
        string dosage
        string instructions
        string issue_date
        string status CHECK
        string created_at
        string received_at
        integer received_by_user_id FK
    }

    NOTIFICATIONS {
        integer id PK
        integer user_id FK
        string message
        boolean is_read
        string created_at
        integer prescription_id FK
    }
```

---

## 3. Table Definitions

### 3.1 `hospitals`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK, AUTOINCREMENT/IDENTITY | Primary key |
| `name` | TEXT | NOT NULL, UNIQUE | Hospital name (enforced at DB level) |
| `address` | TEXT | NULLABLE | Street address |
| `phone` | TEXT | NULLABLE | Contact phone |
| `email` | TEXT | NULLABLE | Contact email |
| `created_at` | TEXT | NOT NULL | ISO8601 timestamp |

**Relationships:**
1 hospital → N users (via `users.hospital_id` FK)

---

### 3.2 `users`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK, AUTOINCREMENT/IDENTITY | Primary key |
| `email` | TEXT | NOT NULL, UNIQUE | Login email (lowercased) |
| `name` | TEXT | NOT NULL | Display name |
| `password_hash` | TEXT | NOT NULL | Werkzeug PBKDF2 hash |
| `role` | TEXT | NOT NULL, CHECK IN ('doctor','pharmacist','admin') | RBAC role |
| `is_active` | INTEGER | NOT NULL, DEFAULT 1 | Soft disable (0=inactive) |
| `created_at` | TEXT | NOT NULL | ISO8601 timestamp |
| `updated_at` | TEXT | NOT NULL | ISO8601 timestamp |
| `hospital_id` | INTEGER | NULLABLE, FK → `hospitals.id` | Hospital affiliation (NULL for admins) |

**Relationships:**
- N users → 1 hospital (many-to-one, `hospital_id` FK)
- 1 user → N notifications (via `notifications.user_id`)
- Doctor user → N prescriptions (via `prescriptions.doctor_name` = `users.name` where role='doctor')
- Pharmacist user → N prescriptions (via `prescriptions.received_by_user_id` FK)

---

### 3.3 `prescriptions`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK, AUTOINCREMENT/IDENTITY | Primary key |
| `verification_id` | TEXT | NOT NULL, UNIQUE | Public verification ID (format: `RX-<10 hex>`) |
| `patient_name` | TEXT | NOT NULL | Patient full name |
| `patient_reference` | TEXT | NOT NULL | Hospital reference (UHID) |
| `doctor_name` | TEXT | NOT NULL | **Stores doctor's display name** (not FK) |
| `clinic_name` | TEXT | NOT NULL | Clinic/hospital name string |
| `medicine_name` | TEXT | NOT NULL | Medicine name |
| `dosage` | TEXT | NOT NULL | Dosage string |
| `instructions` | TEXT | NOT NULL | Usage instructions |
| `issue_date` | TEXT | NOT NULL | YYYY-MM-DD format |
| `status` | TEXT | NOT NULL, DEFAULT 'active', CHECK IN ('active','revoked','received') | Lifecycle state |
| `created_at` | TEXT | NOT NULL | ISO8601 timestamp |
| `received_at` | TEXT | NULLABLE | ISO8601 timestamp when marked received |
| `received_by_user_id` | INTEGER | NULLABLE, FK → `users.id` | Pharmacist who marked received |

**Relationships:**
- 1 prescription → 0/1 notification (via `notifications.prescription_id`)
- **Doctor linkage**: `doctor_name` (TEXT) matches `users.name` WHERE `role='doctor'` — **not a database FK** (denormalized for audit trail)
- **Pharmacist linkage**: `received_by_user_id` FK → `users.id` (proper FK)

---

### 3.4 `notifications`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK, AUTOINCREMENT/IDENTITY | Primary key |
| `user_id` | INTEGER | NOT NULL, FK → `users.id` | Recipient user |
| `message` | TEXT | NOT NULL | Notification text |
| `is_read` | INTEGER | NOT NULL, DEFAULT 0 | 0=unread, 1=read |
| `created_at` | TEXT | NOT NULL | ISO8601 timestamp |
| `prescription_id` | INTEGER | NULLABLE, FK → `prescriptions.id` | Related prescription (optional) |

**Relationships:**
- N notifications → 1 user (many-to-one)
- 0/1 prescription → N notifications (optional FK)

---

## 4. Relationship Details

### 4.1 hospitals → users (1:N)

```
hospitals.id  ←  users.hospital_id
```

- Each hospital can have many doctors and pharmacists
- Admins have `hospital_id = NULL`
- Enforced: FK constraint + index (auto-created by PostgreSQL, explicit in SQLite migration)

### 4.2 users → notifications (1:N)

```
users.id  ←  notifications.user_id
```

- Each user receives their own notifications
- Doctors receive: "Medicine received" notifications
- Admins receive: All "Medicine received" notifications
- Pharmacists: no notification generation (configurable)

### 4.3 prescriptions → notifications (1:N optional)

```
prescriptions.id  ←  notifications.prescription_id
```

- One prescription can generate multiple notifications (one per doctor + all admins)
- Nullable: system notifications may not reference a prescription

### 4.4 users ↔ prescriptions (denormalized + FK hybrid)

| Link Type | Column | Target | Notes |
|-----------|--------|--------|-------|
| **Doctor (author)** | `prescriptions.doctor_name` → `users.name` | Text match + role filter | **Not a FK** — stores name at creation time for audit integrity; doctor renames don't affect prescription record |
| **Pharmacist (receiver)** | `prescriptions.received_by_user_id` → `users.id` | Proper FK | Added in Task 4 migration; NULL until received |

**Why `doctor_name` is TEXT not FK:**
- Prescription records must be immutable after creation
- Doctor name changes shouldn't retroactively alter issued prescriptions
- Query pattern: `WHERE doctor_name = ? AND role = 'doctor'` (see `src/pharmacist/routes.py:124`)

---

## 5. SQLite ↔ PostgreSQL Compatibility

### 5.1 Auto-Increment vs Identity

| Backend | Column Definition |
|---------|-------------------|
| SQLite | `id INTEGER PRIMARY KEY AUTOINCREMENT` |
| PostgreSQL | `id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY` |

Handled in `init_db()` via conditional `id_column` variable.

### 5.2 Placeholder Style

| Backend | Placeholder | Abstraction |
|---------|-------------|-------------|
| SQLite | `?` | `SQLiteConnection.execute()` passes through |
| PostgreSQL | `%s` | `PSQLConnection.cursor()` auto-converts `?` → `%s` |

### 5.3 UNIQUE Constraint on `hospitals.name`

Migration logic in `ensure_hospitals_name_unique()`:
- **PostgreSQL**: Checks `pg_constraint` + `pg_indexes`, adds `ALTER TABLE ... ADD CONSTRAINT hospitals_name_unique UNIQUE (name)`
- **SQLite**: Checks `sqlite_master` + `PRAGMA index_list`, creates `CREATE UNIQUE INDEX idx_hospitals_name_unique ON hospitals(name)`

Both check for duplicate data before adding constraint.

### 5.4 Boolean Storage

- SQLite: `INTEGER` (0/1)
- PostgreSQL: `INTEGER` (0/1) — not native `BOOLEAN` for consistency
- Application layer: Python `bool` ↔ `int(0/1)`

### 5.5 Timestamp Format

All timestamps: ISO8601 UTC strings (`datetime.now(timezone.utc).isoformat()`)
- Stored as TEXT in both backends
- No timezone conversion needed

---

## 6. Schema Initialization & Migration Behavior

### 6.1 `init_db()` Flow

```python
def init_db():
    1. Detect backend from DATABASE_URL
    2. Define id_column (AUTOINCREMENT vs IDENTITY)
    3. For each table (users, hospitals, prescriptions, notifications):
         - Check if exists (backend-specific query)
         - CREATE TABLE IF NOT EXISTS with schema
    4. Ensure UNIQUE constraint on hospitals.name (migration)
    5. Add hospital_id to users (idempotent ALTER TABLE)
    6. Add received_at, received_by_user_id to prescriptions (idempotent)
    7. Create notifications table (idempotent - second pass)
    8. Commit
```

### 6.2 Idempotency Guarantees

- `table_exists()` checks before CREATE → safe on repeated calls
- `ALTER TABLE ... IF NOT EXISTS` (PostgreSQL) / `PRAGMA table_info` (SQLite) for columns
- `ON CONFLICT DO NOTHING` for hospital/user seeding
- Duplicate constraint checks before adding UNIQUE

### 6.3 Development Seeding

`src/seeds.py` seeds only in non-production:
- 2 hospitals: "City General Hospital", "Metro Medical Center"
- 3 users: doctor, pharmacist (both at City General), admin (no hospital)
- Uses atomic UPSERT with `ON CONFLICT` (PostgreSQL) / `INSERT OR IGNORE` (SQLite)

---

## 7. Verification Queries

```sql
-- All prescriptions with doctor hospital info
SELECT p.*, u.hospital_id, h.name as hospital_name
FROM prescriptions p
JOIN users u ON u.name = p.doctor_name AND u.role = 'doctor'
LEFT JOIN hospitals h ON h.id = u.hospital_id;

-- Received prescriptions with pharmacist details
SELECT p.*, u.name as pharmacist_name
FROM prescriptions p
JOIN users u ON u.id = p.received_by_user_id
WHERE p.status = 'received';

-- Doctor's notifications
SELECT n.* FROM notifications n
JOIN users u ON u.id = n.user_id
WHERE u.role = 'doctor' AND n.is_read = 0;
```

---

*Last updated: 2026-08-21 — Reflects Tasks 1–9 schema (hospitals, notifications, received lifecycle)*
