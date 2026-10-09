from pathlib import Path

import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path: Path):
    app = create_app({"TESTING": True, "DATABASE": tmp_path / "test.db", "SECRET_KEY": "test"})
    # Manually seed the test database since test_config skips automatic seeding
    with app.app_context():
        from src.seeds import seed_development_users
        seed_development_users(app, force=True)
    return app.test_client()


def prescription_form():
    return {
        "patient_name": "Aarav Shah",
        "patient_reference": "UHID-1024",
        # doctor_name is now ignored - comes from authenticated user
        "clinic_name": "City Care Clinic",
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
    # Extract verification_id from redirect
    import re
    match = re.search(r"/verify/(RX-[A-F0-9]+)", response.headers["Location"].decode() if isinstance(response.headers["Location"], bytes) else response.headers["Location"])
    assert match, "Verification ID not found in redirect"
    verification_id = match.group(1)
    client.post("/logout")
    login(client, "pharmacist")
    result = client.get(f"/verify/{verification_id}")
    assert b"Prescription verified" in result.data
    assert b"Amoxicillin" in result.data


def test_doctor_name_from_authenticated_user(client):
    """Doctor name comes from authenticated user session, not form."""
    login(client, "doctor")
    form = prescription_form()
    # The form's doctor_name is now ignored
    result = client.get(client.post("/prescriptions/new", data=form).headers["Location"])
    # Should show the seeded doctor's name (Dr. Meera Patel)
    assert b"Dr. Meera Patel" in result.data


def test_unknown_id_is_not_verified(client):
    login(client, "pharmacist")
    response = client.get("/verify/RX-NOTREAL")
    assert b"could not verify" in response.data


def test_role_protection_redirects_to_correct_login(client):
    doctor_page = client.get("/prescriptions/new")
    pharmacist_page = client.get("/verify")
    # Check redirects point to login pages
    assert "/login/doctor" in doctor_page.headers["Location"]
    assert "/login/pharmacist" in pharmacist_page.headers["Location"]


def test_admin_login_and_dashboard(client):
    """Test admin login and dashboard access."""
    login(client, "admin")
    response = client.get("/")
    assert response.status_code == 302  # Redirect to admin dashboard
    dashboard = client.get(response.headers["Location"])
    assert b"ADMIN PORTAL" in dashboard.data
    assert b"Dashboard" in dashboard.data