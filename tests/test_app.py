from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from src import create_app
from src.models.user import create_user


@pytest.fixture()
def client(tmp_path: Path):
    app = create_app({
        "TESTING": True,
        "DATABASE_URL": f"sqlite:///{tmp_path}/test.db",
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
    return {
        "patient_name": "Aarav Shah",
        "patient_reference": "UHID-1024",
        "medicine_name": "Amoxicillin",
        "dosage": "500 mg twice daily",
        "instructions": "Take after meals for five days.",
        "issue_date": "2026-08-16",
    }


def login(client, role):
    credentials = {
        "doctor": {"email": "doctor@rxverify.local", "password": "doctor123"},
        "pharmacist": {"email": "pharmacist@rxverify.local", "password": "pharmacist123"},
        "admin": {"email": "admin@rxverify.local", "password": "admin123"},
    }
    return client.post(f"/login/{role}", data=credentials[role])


def test_issue_and_verify_prescription(client):
    login(client, "doctor")
    response = client.post("/prescriptions/new", data=prescription_form())
    assert response.status_code == 302
    doctor_result = client.get(response.headers["Location"])
    assert b"Prescription issued successfully" in doctor_result.data
    client.post("/logout")
    login(client, "pharmacist")
    result = client.get(response.headers["Location"])
    assert b"Prescription verified" in result.data
    assert b"Amoxicillin" in result.data


def test_doctor_name_cannot_be_changed(client):
    login(client, "doctor")
    form = prescription_form()
    # Try to change doctor name - should be ignored
    form["doctor_name"] = "Dr. Ananya Rao"
    result = client.get(client.post("/prescriptions/new", data=form).headers["Location"])
    # Should show the original doctor name from session, not the form input
    assert b"Dr. Meera Patel" in result.data
    assert b"Dr. Ananya Rao" not in result.data


def test_unknown_id_is_not_verified(client):
    login(client, "pharmacist")
    response = client.get("/verify/RX-NOTREAL")
    assert b"could not verify" in response.data


def test_role_protection_redirects_to_correct_login(client):
    doctor_page = client.get("/prescriptions/new")
    pharmacist_page = client.get("/verify")
    assert "/login/doctor" in doctor_page.headers["Location"]
    assert "/login/pharmacist" in pharmacist_page.headers["Location"]
