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
) -> User:
    """Create a new user in the database."""
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}. Must be one of {VALID_ROLES}")

    email = email.strip().lower()
    password_hash = User.hash_password(password)
    now = get_current_timestamp()

    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO users (email, name, password_hash, role, is_active, hospital_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (email, name, password_hash, role, int(is_active), hospital_id, now, now),
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
    )


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