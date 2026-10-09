"""User model and data access layer."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from werkzeug.security import check_password_hash, generate_password_hash


VALID_ROLES = {"doctor", "pharmacist", "admin"}


@dataclass
class User:
    """User model."""
    id: int
    email: str
    name: str
    password_hash: str
    role: str
    is_active: bool
    created_at: str
    updated_at: str
    hospital_id: Optional[int] = None
    pharmacist_identifier: Optional[str] = None

    def __getitem__(self, key):
        """Allow dict-like access to user attributes."""
        return getattr(self, key)

    def __contains__(self, key):
        """Check if user has an attribute."""
        return hasattr(self, key)

    @classmethod
    def from_row(cls, row: Any) -> "User":
        """Create User from database row."""
        return cls(
            id=row["id"],
            email=row["email"],
            name=row["name"],
            password_hash=row["password_hash"],
            role=row["role"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            hospital_id=row["hospital_id"] if "hospital_id" in row.keys() else None,
            pharmacist_identifier=row["pharmacist_identifier"] if "pharmacist_identifier" in row.keys() else None,
        )

    def verify_password(self, password: str) -> bool:
        """Verify a plaintext password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def hash_password(password: str) -> str:
        """Generate a password hash."""
        return generate_password_hash(password)

    def to_dict(self) -> dict:
        """Convert to dictionary (excluding password hash)."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "hospital_id": self.hospital_id,
            "pharmacist_identifier": self.pharmacist_identifier,
        }


def get_current_timestamp() -> str:
    """Get current UTC timestamp as ISO format string."""
    return datetime.now(timezone.utc).isoformat()


def create_user(
    db: Any,
    email: str,
    name: str,
    password: str,
    role: str,
    is_active: bool = True,
    hospital_id: Optional[int] = None,
    pharmacist_identifier: Optional[str] = None,
) -> User:
    """Create a new user in the database."""
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}. Must be one of {VALID_ROLES}")

    email = email.strip().lower()
    password_hash = User.hash_password(password)
    now = get_current_timestamp()

    cursor = db.cursor()
    if _is_postgres_db(db):
        # psycopg2 does NOT populate cursor.lastrowid (it stays 0), so read the
        # new primary key back via INSERT ... RETURNING id. The PSQL cursor
        # wrapper converts ? placeholders to %s, so RETURNING id is preserved.
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, role, is_active, hospital_id, pharmacist_identifier, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id
            """,
            (email, name, password_hash, role, int(is_active), hospital_id, pharmacist_identifier, now, now),
        )
        row = cursor.fetchone()
        db.commit()
        if not row:
            user_id = 0
        else:
            # RealDictCursor (app path) yields dict-like rows; a plain psycopg2
            # cursor yields tuples. Support both.
            user_id = row["id"] if isinstance(row, dict) else row[0]
            user_id = int(user_id)
    else:
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, role, is_active, hospital_id, pharmacist_identifier, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (email, name, password_hash, role, int(is_active), hospital_id, pharmacist_identifier, now, now),
        )
        db.commit()
        user_id = cursor.lastrowid

    return User(
        id=user_id,
        email=email,
        name=name,
        password_hash=password_hash,
        role=role,
        is_active=is_active,
        created_at=now,
        updated_at=now,
        hospital_id=hospital_id,
        pharmacist_identifier=pharmacist_identifier,
    )


def generate_pharmacist_identifier(db: Any) -> str:
    """Generate the next sequential PHARM-XXX identifier, server-side.

    The identifier is unique, sequential (PHARM-001, PHARM-002, ...), assigned
    only to pharmacists, and safe against gaps/duplicates already present in the
    table (e.g. PHARM-001, PHARM-002, PHARM-005 must not collide).

    Uses the existing SQLite/PostgreSQL abstraction (db.cursor() + ? params).
    """
    cursor = db.cursor()
    cursor.execute(
        "SELECT pharmacist_identifier FROM users "
        "WHERE role = 'pharmacist' AND pharmacist_identifier IS NOT NULL "
        "ORDER BY pharmacist_identifier"
    )
    existing = {row["pharmacist_identifier"] for row in cursor.fetchall()}

    next_num = 1
    while True:
        identifier = f"PHARM-{next_num:03d}"
        if identifier not in existing:
            return identifier
        next_num += 1


def create_hospital(
    db: Any,
    name: str,
    address: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
) -> int:
    """Create a new hospital and return its id.

    The hospitals.name column carries a UNIQUE constraint (enforced in init_db),
    so a duplicate name raises an IntegrityError that callers may catch and
    surface as a friendly error. Follows the existing DB abstraction/transaction
    conventions (db.cursor(), db.commit()).

    Returns the actual inserted primary key. psycopg2 does NOT populate
    ``cursor.lastrowid`` (it stays 0), so on PostgreSQL we read the new id via
    ``INSERT ... RETURNING id``. On SQLite, ``cursor.lastrowid`` is reliable,
    so we keep using it there. The DB backend is detected from the connection,
    falling back to ``lastrowid`` when RETURNING is unavailable.
    """
    now = get_current_timestamp()
    cursor = db.cursor()

    if _is_postgres_db(db):
        # psycopg2 does NOT populate cursor.lastrowid (it stays 0), so we read
        # the new primary key back via INSERT ... RETURNING id. The PSQL cursor
        # wrapper converts ? placeholders to %s, so RETURNING id is preserved.
        cursor.execute(
            """
            INSERT INTO hospitals (name, address, phone, email, created_at)
            VALUES (?, ?, ?, ?, ?) RETURNING id
            """,
            (name, address, phone, email, now),
        )
        row = cursor.fetchone()
        db.commit()
        if not row:
            return 0
        # RealDictCursor (app path) yields dict-like rows; a plain psycopg2
        # cursor yields tuples. Support both.
        new_id = row["id"] if isinstance(row, dict) else row[0]
        return int(new_id)

    # SQLite: cursor.lastrowid is reliable and is the project's established
    # mechanism for retrieving the inserted row id (see create_user).
    cursor.execute(
        """
        INSERT INTO hospitals (name, address, phone, email, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, address, phone, email, now),
    )
    db.commit()
    return cursor.lastrowid


def _is_postgres_db(db: Any) -> bool:
    """Detect whether db is backed by PostgreSQL (psycopg2)."""
    conn = getattr(db, "_conn", None)
    if conn is None:
        return False
    module = type(conn).__module__
    return module.startswith("psycopg2")


def get_hospital_by_id(db: Any, hospital_id: int) -> Optional[dict]:
    """Fetch a hospital row by id (or None)."""
    cursor = db.cursor()
    cursor.execute("SELECT * FROM hospitals WHERE id = ?", (hospital_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_user_by_email(db: Any, email: str) -> Optional[User]:
    """Get user by email address."""
    email = email.strip().lower()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    if row:
        return User.from_row(row)
    return None


def get_user_by_id(db: Any, user_id: int) -> Optional[User]:
    """Get user by ID."""
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        return User.from_row(row)
    return None


def update_user(
    db: Any,
    user_id: int,
    name: Optional[str] = None,
    password: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    hospital_id: Optional[int] = None,
    pharmacist_identifier: Optional[str] = None,
) -> Optional[User]:
    """Update user fields."""
    user = get_user_by_id(db, user_id)
    if not user:
        return None

    updates = []
    params = []

    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if password is not None:
        updates.append("password_hash = ?")
        params.append(User.hash_password(password))
    if role is not None:
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role: {role}. Must be one of {VALID_ROLES}")
        updates.append("role = ?")
        params.append(role)
    if is_active is not None:
        updates.append("is_active = ?")
        params.append(int(is_active))
    if hospital_id is not None:
        updates.append("hospital_id = ?")
        params.append(hospital_id)
    if pharmacist_identifier is not None:
        updates.append("pharmacist_identifier = ?")
        params.append(pharmacist_identifier)

    if not updates:
        return user

    updates.append("updated_at = ?")
    params.append(get_current_timestamp())
    params.append(user_id)

    cursor = db.cursor()
    cursor.execute(
        f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
        tuple(params),
    )
    db.commit()

    return get_user_by_id(db, user_id)


def set_user_active(db: Any, user_id: int, is_active: bool) -> Optional[User]:
    """Set user active/inactive status."""
    return update_user(db, user_id, is_active=is_active)


def delete_user(db: Any, user_id: int) -> bool:
    """Delete a user by ID."""
    cursor = db.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    return cursor.rowcount > 0


def list_users(db: Any, role: Optional[str] = None) -> list[User]:
    """List all users, optionally filtered by role."""
    cursor = db.cursor()
    if role:
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role: {role}. Must be one of {VALID_ROLES}")
        cursor.execute("SELECT * FROM users WHERE role = ? ORDER BY created_at", (role,))
    else:
        cursor.execute("SELECT * FROM users ORDER BY created_at")
    return [User.from_row(row) for row in cursor.fetchall()]