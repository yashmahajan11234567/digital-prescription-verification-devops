"""Development/demo user seeding for RxVerify.

This module provides explicit development/demo user seeding.
Production must require explicit administrative user creation.
DO NOT automatically create insecure default users in production.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from src.models.user import VALID_ROLES, create_user, get_user_by_email, delete_user
from src import create_app


DEV_HOSPITALS = [
    {
        "name": "City General Hospital",
        "address": "123 Main Street, Metro City",
        "phone": "+1-555-0101",
        "email": "admin@citygeneral.rxverify.local",
    },
    {
        "name": "Metro Medical Center",
        "address": "456 Oak Avenue, Metro City",
        "phone": "+1-555-0102",
        "email": "admin@metromedical.rxverify.local",
    },
]


DEV_USERS = [
    {
        "email": "doctor@rxverify.local",
        "name": "Dr. Meera Patel",
        "password": "doctor123",
        "role": "doctor",
        "is_active": True,
        "hospital_name": "City General Hospital",
    },
    {
        "email": "pharmacist@rxverify.local",
        "name": "Rohan Sharma",
        "password": "pharmacist123",
        "role": "pharmacist",
        "is_active": True,
        "hospital_name": "City General Hospital",
    },
    {
        "email": "admin@rxverify.local",
        "name": "System Administrator",
        "password": "admin123",
        "role": "admin",
        "is_active": True,
        "hospital_name": None,  # Admin has no hospital
    },
]


def _upsert_hospital(db, cursor, hospital_data: dict, is_postgres: bool, force: bool = False) -> tuple[int, bool]:
    """Upsert a hospital atomically and return its ID and whether it was created.

    Uses atomic UPSERT operations with UNIQUE constraint on hospitals.name.
    This prevents duplicate hospitals when called concurrently by multiple workers.

    Returns:
        Tuple of (hospital_id, was_created) where was_created is True if a new
        hospital was inserted, False if an existing hospital was returned/updated.
    """
    name = hospital_data["name"]
    address = hospital_data["address"]
    phone = hospital_data["phone"]
    email = hospital_data["email"]
    now = datetime.now(timezone.utc).isoformat()

    if force:
        # Force mode: always update to the current seed data
        if is_postgres:
            cursor.execute(
                """
                INSERT INTO hospitals (name, address, phone, email, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (name) DO UPDATE SET
                    address = EXCLUDED.address,
                    phone = EXCLUDED.phone,
                    email = EXCLUDED.email,
                    created_at = EXCLUDED.created_at
                RETURNING id
                """,
                (name, address, phone, email, now),
            )
            result = cursor.fetchone()
            db.commit()
            return result["id"] if result else None, False
        else:
            # SQLite: INSERT OR REPLACE (name is UNIQUE)
            cursor.execute(
                """
                INSERT OR REPLACE INTO hospitals (name, address, phone, email, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, address, phone, email, now),
            )
            db.commit()
            cursor.execute("SELECT id FROM hospitals WHERE name = ?", (name,))
            result = cursor.fetchone()
            return result["id"] if result else None, False
    else:
        # Normal mode: insert if not exists, return existing if exists
        if is_postgres:
            cursor.execute(
                """
                INSERT INTO hospitals (name, address, phone, email, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (name) DO NOTHING
                RETURNING id
                """,
                (name, address, phone, email, now),
            )
            result = cursor.fetchone()
            if result:
                # New hospital was created
                db.commit()
                return result["id"], True
            else:
                # Hospital already existed, fetch its ID
                cursor.execute("SELECT id FROM hospitals WHERE name = ?", (name,))
                existing = cursor.fetchone()
                return existing["id"] if existing else None, False
        else:
            # SQLite: INSERT OR IGNORE (name is UNIQUE)
            cursor.execute(
                """
                INSERT OR IGNORE INTO hospitals (name, address, phone, email, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, address, phone, email, now),
            )
            db.commit()
            cursor.execute("SELECT id FROM hospitals WHERE name = ?", (name,))
            existing = cursor.fetchone()
            # Check if this was a new insert by checking if we got existing data
            # If existing is not None, the record already existed and INSERT was ignored
            was_created = existing is None
            return existing["id"] if existing else None, not was_created


def _upsert_user(db, cursor, user_data: dict, hospital_id: int | None, is_postgres: bool, force: bool = False) -> bool:
    """Upsert a user with optional hospital_id.

    Returns True if user was created/updated, False if skipped.
    """
    email = user_data["email"]
    name = user_data["name"]
    password = user_data["password"]
    role = user_data["role"]
    is_active = int(user_data["is_active"])
    now = datetime.now(timezone.utc).isoformat()
    password_hash = create_user.__globals__['User'].hash_password(password)

    existing = get_user_by_email(db, email)
    if existing and not force:
        return False  # Skipped

    if existing and force:
        delete_user(db, existing.id)

    if hospital_id is not None:
        if is_postgres:
            cursor.execute(
                """
                INSERT INTO users (email, name, password_hash, role, is_active, hospital_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (email) DO UPDATE SET
                    name = EXCLUDED.name,
                    password_hash = EXCLUDED.password_hash,
                    role = EXCLUDED.role,
                    is_active = EXCLUDED.is_active,
                    hospital_id = EXCLUDED.hospital_id,
                    updated_at = EXCLUDED.updated_at
                """,
                (email, name, password_hash, role, is_active, hospital_id, now, now),
            )
        else:
            cursor.execute(
                """
                INSERT INTO users (email, name, password_hash, role, is_active, hospital_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (email) DO UPDATE SET
                    name = EXCLUDED.name,
                    password_hash = EXCLUDED.password_hash,
                    role = EXCLUDED.role,
                    is_active = EXCLUDED.is_active,
                    hospital_id = EXCLUDED.hospital_id,
                    updated_at = EXCLUDED.updated_at
                """,
                (email, name, password_hash, role, is_active, hospital_id, now, now),
            )
    else:
        # Admin without hospital - use create_user for simplicity (handles password hashing)
        create_user(db, email, name, password, role, is_active=bool(is_active))

    return True


def seed_development_users(app, force: bool = False) -> dict:
    """Seed development/demo users into the database.

    Args:
        app: Flask application instance
        force: If True, recreate users even if they exist (for testing)

    Returns:
        Dictionary with seeding results
    """
    if app.config.get("FLASK_ENV") == "production" and not force:
        return {
            "seeded": 0,
            "skipped": 0,
            "message": "Production environment: skipping automated seeding. Use explicit admin creation.",
        }

    results = {"seeded": 0, "skipped": 0, "errors": []}

    with app.app_context():
        db = app.get_db()
        cursor = db.cursor()

        # Check if we're using PostgreSQL
        db_url = app.config.get("DATABASE_URL", "sqlite:///instance/prescriptions.db")
        is_postgres = db_url.startswith("postgresql://") or db_url.startswith("postgres://")

        # First, seed hospitals using idempotent UPSERT
        hospital_ids = {}
        for hospital_data in DEV_HOSPITALS:
            try:
                hospital_id, was_created = _upsert_hospital(db, cursor, hospital_data, is_postgres, force)
                if hospital_id:
                    hospital_ids[hospital_data["name"]] = hospital_id
                    if was_created:
                        results["seeded"] += 1
                else:
                    results["errors"].append(f"Failed to create/get hospital {hospital_data['name']}")
            except Exception as e:
                results["errors"].append(f"Failed to create hospital {hospital_data['name']}: {e}")
                db.rollback()
            else:
                print(f"[seed_development_users] Committing transaction for hospital {hospital_data['name']}")
                db.commit()

        # Then seed users with hospital associations
        for user_data in DEV_USERS:
            try:
                hospital_id = hospital_ids.get(user_data.get("hospital_name"))
                # Admin gets NULL hospital_id
                if user_data["role"] == "admin":
                    hospital_id = None

                print(f"[seed_development_users] Processing user {user_data['email']} with hospital_id={hospital_id}")
                was_created = _upsert_user(db, cursor, user_data, hospital_id, is_postgres, force)
                print(f"[seed_development_users] User {user_data['email']} was_created={was_created}")
                if was_created:
                    results["seeded"] += 1
                    print(f"[seed_development_users] Incremented seeded count to {results['seeded']}")
                else:
                    results["skipped"] += 1
                    print(f"[seed_development_users] Incremented skipped count to {results['skipped']}")
                db.commit()
                print(f"[seed_development_users] Committed transaction for user {user_data['email']}")
            except Exception as e:
                results["errors"].append(f"Failed to create {user_data['email']}: {e}")
                db.rollback()

    print(f"[seed_development_users] FINAL RESULTS: {results}")
    return results


def seed_users_from_env(app) -> dict:
    """Seed users from environment variables (for production use with explicit config).

    Expected environment variables:
    - ADMIN_EMAIL, ADMIN_NAME, ADMIN_PASSWORD, ADMIN_ROLE=admin
    - DOCTOR_EMAIL, DOCTOR_NAME, DOCTOR_PASSWORD, DOCTOR_ROLE=doctor
    - PHARMACIST_EMAIL, PHARMACIST_NAME, PHARMACIST_PASSWORD, PHARMACIST_ROLE=pharmacist

    Returns:
        Dictionary with seeding results
    """
    results = {"seeded": 0, "skipped": 0, "errors": []}

    # Define roles and their env prefixes
    roles_config = {
        "admin": "ADMIN",
        "doctor": "DOCTOR",
        "pharmacist": "PHARMACIST",
    }

    with app.app_context():
        db = app.get_db()
        for role, prefix in roles_config.items():
            email = os.environ.get(f"{prefix}_EMAIL")
            name = os.environ.get(f"{prefix}_NAME")
            password = os.environ.get(f"{prefix}_PASSWORD")

            if not all([email, name, password]):
                continue

            existing = get_user_by_email(db, email)
            if existing:
                results["skipped"] += 1
                continue

            try:
                create_user(db, email, name, password, role, is_active=True)
                results["seeded"] += 1
            except Exception as e:
                results["errors"].append(f"Failed to create {email}: {e}")

    return results


def ensure_development_users(app) -> None:
    """Ensure development users exist (called during app init in development).

    This is a convenience for local development only.
    """
    if app.config.get("FLASK_ENV") != "production":
        seed_development_users(app)


if __name__ == "__main__":
    # Allow running as script for manual seeding
    import sys

    app = create_app()
    force = "--force" in sys.argv
    results = seed_development_users(app, force=force)
    print(f"Seeded: {results['seeded']}, Skipped: {results['skipped']}")
    if results["errors"]:
        print(f"Errors: {results['errors']}")