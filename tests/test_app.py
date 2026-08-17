from pathlib import Path

import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path: Path):
    app = create_app({"TESTING": True, "DATABASE": tmp_path / "test.db", "SECRET_KEY": "test"})
    return app.test_client()


def prescription_form():
    return {
        "patient_name": "Aarav Shah",
        "patient_reference": "UHID-1024",
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


def test_doctor_name_can_be_changed(client):
    login(client, "doctor")
    form = prescription_form()
    form["doctor_name"] = "Dr. Ananya Rao"
    result = client.get(client.post("/prescriptions/new", data=form).headers["Location"])
    assert b"Dr. Ananya Rao" in result.data


def test_unknown_id_is_not_verified(client):
    login(client, "pharmacist")
    response = client.get("/verify/RX-NOTREAL")
    assert b"could not verify" in response.data


def test_role_protection_redirects_to_correct_login(client):
    doctor_page = client.get("/prescriptions/new")
    pharmacist_page = client.get("/verify")
    assert "/login/doctor" in doctor_page.headers["Location"]
    assert "/login/pharmacist" in pharmacist_page.headers["Location"]
