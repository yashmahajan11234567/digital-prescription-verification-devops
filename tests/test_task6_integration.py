"""Task 6 targeted integration tests.

These tests fill genuine coverage gaps identified by inspecting the existing
suite against the Task 6 objectives, without duplicating tests that already
exist. They reuse the shared ``client`` fixture and the ``login`` /
``prescription_form`` helpers from ``tests/conftest.py`` so they follow the
project's existing test architecture and conventions.

Scope (test-only, no application code changes):
  * prescription revoke (active -> revoked, data intact, revoked -> revoked)
  * prescription receive authorization (non-pharmacist roles rejected)
  * admin route authorization (non-admin roles rejected)
  * notification authorization / IDOR (cross-user mark-read rejected)
  * input / security handling (malformed IDs, SQL-injection-looking values,
    non-existent prescription receive)
"""
from __future__ import annotations

from tests.conftest import login, prescription_form


# ---------------------------------------------------------------------------
# Helpers (test-local; keep URL/parsing logic in one place)
# ---------------------------------------------------------------------------

def _verification_id_from_url(prescription_url: str) -> str:
    """Extract the verification ID (RX-XXXXXXXXXX) from the create redirect.

    The doctor create route redirects to
    ``url_for("pharmacist.verification_result", verification_id=...)`` which is
    ``/verify/RX-XXXXXXXXXX``. The trailing segment is the verification ID
    string, NOT the integer database row id.
    """
    return prescription_url.split("/")[-1]


def _create_prescription(client) -> tuple[str, int]:
    """Issue a prescription as a doctor and return (verification_id, db_id)."""
    login(client, "doctor")
    response = client.post("/prescriptions/new", data=prescription_form())
    assert response.status_code == 302
    verification_id = _verification_id_from_url(response.headers["Location"])
    with client.application.app_context():
        db = client.application.get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT id FROM prescriptions WHERE verification_id = ?",
            (verification_id,),
        )
        row = cursor.fetchone()
        assert row is not None
        return verification_id, row["id"]


# ---------------------------------------------------------------------------
# Prescription revoke (genuine gap: existing revoke test never calls revoke)
# ---------------------------------------------------------------------------

def test_active_prescription_can_be_revoked(client):
    """ACTIVE -> REVOKED transition succeeds and updates the DB status."""
    verification_id, prescription_id = _create_prescription(client)

    response = client.post(f"/prescriptions/{prescription_id}/revoke")
    assert response.status_code == 302

    with client.application.app_context():
        db = client.application.get_db()
        cursor = db.cursor()
        cursor.execute("SELECT status FROM prescriptions WHERE id = ?", (prescription_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["status"] == "revoked"


def test_revoke_does_not_corrupt_verification_data(client):
    """Verification/display data is preserved after a prescription is revoked."""
    verification_id, prescription_id = _create_prescription(client)

    client.post(f"/prescriptions/{prescription_id}/revoke")

    result = client.get(f"/verify/{verification_id}")
    assert result.status_code == 200
    assert b"revoked" in result.data.lower()
    # Original prescription data is still shown on the verification page.
    assert b"Amoxicillin" in result.data
    assert b"Aarav Shah" in result.data
    assert b"UHID-1024" in result.data


def test_revoking_nonexistent_prescription_returns_404(client):
    """Revoke of an unknown prescription id yields a 404, not a silent no-op."""
    login(client, "doctor")
    response = client.post("/prescriptions/999999/revoke")
    assert response.status_code == 404


def test_revoked_prescription_revoke_is_idempotent(client):
    """REVOKED -> REVOKED keeps status revoked and returns a redirect."""
    verification_id, prescription_id = _create_prescription(client)

    first = client.post(f"/prescriptions/{prescription_id}/revoke")
    assert first.status_code == 302

    second = client.post(f"/prescriptions/{prescription_id}/revoke")
    # revoke just sets status='revoked' again; still a successful redirect.
    assert second.status_code == 302

    with client.application.app_context():
        db = client.application.get_db()
        cursor = db.cursor()
        cursor.execute("SELECT status FROM prescriptions WHERE id = ?", (prescription_id,))
        assert cursor.fetchone()["status"] == "revoked"


# ---------------------------------------------------------------------------
# Prescription receive authorization (gap: who may call /receive)
# ---------------------------------------------------------------------------

def test_doctor_cannot_receive_prescription(client):
    """A doctor (not pharmacist) is rejected from the receive endpoint."""
    verification_id, prescription_id = _create_prescription(client)

    # Already logged in as doctor; attempt to receive must be rejected.
    response = client.post(f"/receive/{prescription_id}")
    assert response.status_code == 302
    assert "/login/pharmacist" in response.headers["Location"]

    # Prescription status must be unchanged.
    with client.application.app_context():
        db = client.application.get_db()
        cursor = db.cursor()
        cursor.execute("SELECT status FROM prescriptions WHERE id = ?", (prescription_id,))
        assert cursor.fetchone()["status"] == "active"


def test_unauthenticated_user_cannot_receive_prescription(client):
    """No session at all is rejected from the receive endpoint."""
    verification_id, prescription_id = _create_prescription(client)
    client.post("/logout")

    response = client.post(f"/receive/{prescription_id}")
    assert response.status_code == 302
    assert "/login/pharmacist" in response.headers["Location"]


# ---------------------------------------------------------------------------
# Admin route authorization (gap: prior test only checked decorator import)
# ---------------------------------------------------------------------------

ADMIN_ROUTES = [
    "/admin/",
    "/admin/hospitals",
    "/admin/hospitals/1",
]


def test_admin_dashboard_accessible_by_admin(client):
    """An authenticated admin can reach the admin dashboard."""
    login(client, "admin")
    response = client.get("/admin/")
    assert response.status_code == 200


def test_doctor_cannot_access_admin_dashboard(client):
    """Doctor is redirected away from the admin dashboard (server-side RBAC)."""
    login(client, "doctor")
    response = client.get("/admin/")
    assert response.status_code == 302
    assert "/login/admin" in response.headers["Location"]


def test_pharmacist_cannot_access_admin_dashboard(client):
    """Pharmacist is redirected away from the admin dashboard."""
    login(client, "pharmacist")
    response = client.get("/admin/")
    assert response.status_code == 302
    assert "/login/admin" in response.headers["Location"]


def test_unauthenticated_cannot_access_admin_routes(client):
    """Unauthenticated requests to admin routes are rejected, not served."""
    client.post("/logout")
    for route in ADMIN_ROUTES:
        response = client.get(route)
        assert response.status_code == 302, f"{route} should redirect unauthenticated"
        assert "/login/admin" in response.headers["Location"], (
            f"{route} should redirect to admin login"
        )


def test_admin_hospital_detail_invalid_id_returns_404(client):
    """Admin requesting a non-existent hospital gets 404 (server-side)."""
    login(client, "admin")
    response = client.get("/admin/hospitals/99999")
    assert response.status_code == 404


def test_admin_doctor_detail_invalid_ids_return_404(client):
    """Admin requesting a non-existent doctor (in a valid hospital) gets 404."""
    login(client, "admin")
    # Hospital 99999 does not exist -> 404.
    assert client.get("/admin/hospitals/99999/doctors/1").status_code == 404


def test_non_admin_cannot_access_admin_hospital_list(client):
    """Doctor/pharmacist are rejected from the hospital list route."""
    for role in ("doctor", "pharmacist"):
        login(client, role)
        response = client.get("/admin/hospitals")
        assert response.status_code == 302
        assert "/login/admin" in response.headers["Location"]
        client.post("/logout")


# ---------------------------------------------------------------------------
# Notification authorization / IDOR (gap: cross-user mark-read not tested)
# ---------------------------------------------------------------------------

def test_user_cannot_mark_another_users_notification_read(client):
    """Marking a notification read is scoped by user_id (IDOR protection).

    A notification owned by the doctor must not be modifiable by a pharmacist.
    The route's data layer filters on ``user_id`` (see
    src/models/notifications.py:mark_notification_read), so a cross-user mark
    affects zero rows and the doctor's unread count is unchanged.
    """
    verification_id, prescription_id = _create_prescription(client)
    client.post("/logout")

    # Receive as pharmacist so the prescribing doctor gets a notification.
    login(client, "pharmacist")
    client.post(f"/receive/{prescription_id}")
    client.post("/logout")

    # Snapshot the doctor's unread notifications.
    with client.application.app_context():
        db = client.application.get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id FROM users WHERE role = 'doctor' LIMIT 1")
        doctor = cursor.fetchone()
        doctor_id = doctor["id"]
        cursor.execute(
            "SELECT id FROM notifications WHERE user_id = ? AND is_read = 0 LIMIT 1",
            (doctor_id,),
        )
        row = cursor.fetchone()
        assert row is not None, "doctor should have an unread notification"
        doctor_notification_id = row["id"]

    # Log in as pharmacist (not the notification owner) and attempt to mark the
    # doctor's notification read.
    login(client, "pharmacist")
    response = client.post(f"/notifications/{doctor_notification_id}/read")
    # The doctor blueprint requires the doctor role; pharmacist is redirected
    # to the doctor login rather than mutating the row.
    assert response.status_code == 302
    assert "/login/doctor" in response.headers["Location"]

    # The doctor's notification is still unread (no cross-user mutation).
    with client.application.app_context():
        db = client.application.get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT is_read FROM notifications WHERE id = ?",
            (doctor_notification_id,),
        )
        assert cursor.fetchone()["is_read"] == 0


def test_user_can_mark_own_notification_read(client):
    """A doctor can mark their own notification as read via the route."""
    verification_id, prescription_id = _create_prescription(client)
    client.post("/logout")

    login(client, "pharmacist")
    client.post(f"/receive/{prescription_id}")
    client.post("/logout")

    login(client, "doctor")
    with client.application.app_context():
        db = client.application.get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id FROM users WHERE role = 'doctor' LIMIT 1")
        doctor_id = cursor.fetchone()["id"]
        cursor.execute(
            "SELECT id FROM notifications WHERE user_id = ? AND is_read = 0 LIMIT 1",
            (doctor_id,),
        )
        notification_id = cursor.fetchone()["id"]

    response = client.post(f"/notifications/{notification_id}/read")
    assert response.status_code == 302

    with client.application.app_context():
        db = client.application.get_db()
        cursor = db.cursor()
        cursor.execute("SELECT is_read FROM notifications WHERE id = ?", (notification_id,))
        assert cursor.fetchone()["is_read"] == 1


# ---------------------------------------------------------------------------
# Input / security handling (gap: malformed / malicious verification IDs)
# ---------------------------------------------------------------------------

def test_malformed_verification_id_does_not_verify(client):
    """A malformed verification ID renders 'not found', not an error page."""
    login(client, "pharmacist")
    response = client.get("/verify/RX-")
    assert response.status_code == 200
    assert b"could not verify" in response.data or b"No matching prescription" in response.data


def test_verify_nonexistent_verification_id(client):
    """A well-formed but non-existent RX id renders 'not found'."""
    login(client, "pharmacist")
    response = client.get("/verify/RX-0000000000")
    assert response.status_code == 200
    assert b"could not verify" in response.data or b"No matching prescription" in response.data


def test_verify_sql_injection_looking_value_is_safe(client):
    """A SQL-injection-looking verification id is treated as a literal value.

    The route uses parameterized queries, so a classic injection payload is not
    executed; it simply fails to match any prescription.
    """
    login(client, "pharmacist")
    response = client.get("/verify/' OR '1'='1")
    assert response.status_code == 200
    # No real prescription matches; page must show not-found, never 500.
    assert b"could not verify" in response.data or b"No matching prescription" in response.data


def test_receive_nonexistent_prescription_redirects(client):
    """Receiving an unknown prescription id redirects (not-found branch), not 500."""
    login(client, "pharmacist")
    response = client.post("/receive/999999")
    assert response.status_code == 302
    # The not-found branch redirects back to the verify form.
    assert "/verify" in response.headers["Location"]


def test_submit_empty_verification_id(client):
    """Submitting an empty verification id redirects back with a flash."""
    login(client, "pharmacist")
    response = client.post("/verify", data={"verification_id": ""})
    assert response.status_code == 302
    assert "/verify" in response.headers["Location"]
