"""Shared test configuration and fixtures."""
from __future__ import annotations

from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from src import create_app
from src.models.user import create_user


@pytest.fixture()
def client(tmp_path: Path):
    """Create test client with SQLite file database."""
    db_path = tmp_path / "test.db"
    app = create_app({
        "TESTING": True,
        "DATABASE_URL": f"sqlite:///{db_path}",
        "SECRET_KEY": "test",
    })
    # Seed test users directly
    with app.app_context():
        db = app.get_db()
        create_user(db, "doctor@rxverify.local", "Dr. Meera Patel", "doctor123", "doctor")
        create_user(db, "pharmacist@rxverify.local", "Rohan Sharma", "pharmacist123", "pharmacist")
        create_user(db, "admin@rxverify.local", "System Administrator", "admin123", "admin")
        # Create inactive user for testing
        create_user(db, "inactive@rxverify.local", "Inactive User", "password123", "doctor", is_active=False)
    return app.test_client()


def prescription_form():
    """Return valid prescription form data."""
    return {
        "patient_name": "Aarav Shah",
        "patient_reference": "UHID-1024",
        "doctor_name": "Dr. Meera Patel",
        "clinic_name": "City Care Clinic",
        "medicine_name": "Amoxicillin",
        "dosage": "500 mg twice daily",
        "instructions": "Take after meals for five days.",
        "issue_date": "2026-08-16",
    }


def login(client, role: str):
    """Helper to log in as a specific role."""
    credentials = {
        "doctor": {"email": "doctor@rxverify.local", "password": "doctor123"},
        "pharmacist": {"email": "pharmacist@rxverify.local", "password": "pharmacist123"},
        "admin": {"email": "admin@rxverify.local", "password": "admin123"},
    }
    return client.post(f"/login/{role}", data=credentials[role])