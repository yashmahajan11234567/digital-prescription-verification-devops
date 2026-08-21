"""Unit tests for RxVerify routes."""
from __future__ import annotations

import pytest

from tests.conftest import prescription_form, login


def test_home_page(client):
    """Test home page loads."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"RxVerify" in response.data


def test_health_endpoint(client):
    """Test health endpoint returns OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_login_page_accessible(client):
    """Test login pages are accessible."""
    doctor_login = client.get("/login/doctor")
    pharmacist_login = client.get("/login/pharmacist")
    assert doctor_login.status_code == 200
    assert pharmacist_login.status_code == 200


def test_invalid_role_returns_404(client):
    """Test invalid role returns 404."""
    response = client.get("/login/invalidrole")
    assert response.status_code == 404


def test_admin_login_page_accessible(client):
    """Test admin login page is accessible."""
    response = client.get("/login/admin")
    assert response.status_code == 200
    assert b"Admin" in response.data or b"login" in response.data.lower()


def test_issue_prescription_get(client):
    """Test GET /prescriptions/new shows form."""
    login(client, "doctor")
    response = client.get("/prescriptions/new")
    assert response.status_code == 200
    assert b"Issue a prescription" in response.data


def test_verify_form_get(client):
    """Test GET /verify shows form."""
    login(client, "pharmacist")
    response = client.get("/verify")
    assert response.status_code == 200
    assert b"Verify a prescription" in response.data


def test_prescriptions_list_get(client):
    """Test GET /prescriptions shows list."""
    login(client, "doctor")
    response = client.get("/prescriptions")
    assert response.status_code == 200
    assert b"Prescription records" in response.data


def test_logout_works(client):
    """Test logout clears session."""
    login(client, "doctor")
    response = client.post("/logout")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_role_protection_redirects_to_correct_login(client):
    """Test role protection redirects to correct login."""
    doctor_page = client.get("/prescriptions/new")
    pharmacist_page = client.get("/verify")
    assert "/login/doctor" in doctor_page.headers["Location"]
    assert "/login/pharmacist" in pharmacist_page.headers["Location"]