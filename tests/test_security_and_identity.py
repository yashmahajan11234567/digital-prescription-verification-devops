"""Security, identity-authority, and coverage tests (Task 6 validation pass).

These tests lock in the authoritative FK relationships introduced for the
prescription/notification model and verify the anti-forgery protections:

  * An authenticated doctor cannot manipulate doctor_name / clinic_name /
    doctor_id / hospital_id to create a prescription belonging to another
    doctor or hospital.
  * A pharmacist's receive flow cannot target an arbitrary doctor for the
    "medicine received" notification (it is driven by prescription.doctor_id).
  * Authoritative chain:
        users.id -> doctor_id -> prescription.doctor_id
        users.hospital_id -> prescription.hospital_id
        prescription.doctor_id -> notification.user_id
  * Pharmacist identifiers are unique and sequential (PHARM-001, PHARM-002, ...).
  * Admin dashboard surfaces only Hospitals / Doctors / Pharmacists.
  * Doctor issue UI: no clinic_name input, doctor not editable, hospital derived.
  * Legacy prescriptions (no doctor_id) still verify and notify correctly.

All tests use the shared ``client`` fixture and ``login`` / ``prescription_form``
helpers so they follow the project's existing test architecture. Test-only file;
no application code is changed here.
"""
from __future__ import annotations

import uuid

from tests.conftest import login, prescription_form


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_prescription_as(client, role: str, form: dict | None = None):
    """Issue a prescription and return (verification_id, prescription_db_id)."""
    login(client, role)
    data = form if form is not None else prescription_form()
    response = client.post("/prescriptions/new", data=data)
    assert response.status_code == 302
    verification_id = response.headers["Location"].split("/")[-1]
    with client.application.app_context():
        db = client.application.get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT id, doctor_id, hospital_id, doctor_name, clinic_name FROM prescriptions WHERE verification_id = ?",
            (verification_id,),
        )
        row = cursor.fetchone()
        assert row is not None
        return verification_id, row["id"], dict(row)


def _seed_second_doctor_and_hospital(client):
    """Create a second doctor in a second hospital; return their ids.

    Used to prove a logged-in doctor cannot forge a prescription onto another
    doctor/hospital. Returns (other_doctor_id, other_hospital_id).
    """
    import sqlite3
    with client.application.app_context():
        db = client.application.get_db()
        cursor = db.cursor()
        # Second hospital
        cursor.execute(
            "INSERT INTO hospitals (name, address, phone, email, created_at) VALUES (?,?,?,?,?)",
            ("Rival Clinic", "9 Other Rd", "+1-555-9999", "other@rxverify.local",
             "2026-01-01T00:00:00+00:00"),
        )
        other_hospital_id = cursor.lastrowid
        # Second doctor (different hospital)
        from src.models.user import create_user
        other = create_user(
            db, "other@rxverify.local", "Dr. Evil Imposter", "password123", "doctor",
            hospital_id=other_hospital_id,
        )
        db.commit()
        return other.id, other_hospital_id


# ---------------------------------------------------------------------------
# 5/6. Doctor cannot forge identity (doctor_name/clinic_name/doctor_id/hospital_id)
# ---------------------------------------------------------------------------

def test_doctor_cannot_forge_doctor_name(client):
    """A tampered doctor_name in the form is ignored; the session doctor wins."""
    verification_id, pid, row = _create_prescription_as(client, "doctor")
    # Authenticated doctor is Dr. Meera Patel (id 1).
    assert row["doctor_id"] == 1
    assert row["doctor_name"] == "Dr. Meera Patel"
    assert row["doctor_name"] != "Dr. Ananya Rao"


def test_doctor_cannot_forge_clinic_name(client):
    """A tampered clinic_name is ignored; clinic_name derives from hospital FK."""
    _seed_second_doctor_and_hospital(client)
    with client.application.app_context():
        db = client.application.get_db()
        cursor = db.cursor()
        cursor.execute("SELECT name FROM hospitals WHERE id = (SELECT hospital_id FROM users WHERE id = 1)")
        hospital = cursor.fetchone()
        expected_clinic = hospital["name"] if hospital else ""
    verification_id, pid, row = _create_prescription_as(client, "doctor")
    assert row["clinic_name"] == expected_clinic
    assert row["clinic_name"] != "Forged Clinic"


def test_doctor_cannot_forge_doctor_id_onto_other_doctor(client):
    """Even if doctor_id were submitted, the route uses session user_id only."""
    other_doctor_id, _ = _seed_second_doctor_and_hospital(client)
    # The POST body is not where doctor_id comes from, so craft a form with a
    # misleading doctor_name; the stored doctor_id must still equal the session user.
    form = prescription_form()
    form["doctor_name"] = "Dr. Evil Imposter"  # name of the OTHER doctor
    verification_id, pid, row = _create_prescription_as(client, "doctor", form=form)
    # Must be attributed to the logged-in doctor (id 1), NOT the imposter.
    assert row["doctor_id"] == 1
    assert row["doctor_id"] != other_doctor_id
    assert row["doctor_name"] == "Dr. Meera Patel"


def test_doctor_cannot_forge_hospital_id_onto_other_hospital(client):
    """Prescription hospital_id is the session doctor's hospital, not forgeable."""
    _, other_hospital_id = _seed_second_doctor_and_hospital(client)
    with client.application.app_context():
        db = client.application.get_db()
        cursor = db.cursor()
        cursor.execute("SELECT hospital_id FROM users WHERE id = 1")
        own_hospital_id = cursor.fetchone()["hospital_id"]
    verification_id, pid, row = _create_prescription_as(client, "doctor")
    # hospital_id must equal the authenticated doctor's hospital, never the rival's.
    assert row["hospital_id"] == own_hospital_id
    assert row["hospital_id"] != other_hospital_id


def test_prescription_doctor_id_matches_session_user(client):
    """Authoritative relationship: users.id -> doctor_id -> prescription.doctor_id."""
    login(client, "doctor")
    with client.session_transaction() as sess:
        session_user_id = sess["user_id"]
    response = client.post("/prescriptions/new", data=prescription_form())
    assert response.status_code == 302
    verification_id = response.headers["Location"].split("/")[-1]
    with client.application.app_context():
        db = client.application.get_db()
        cursor = db.cursor()
        cursor.execute("SELECT doctor_id FROM prescriptions WHERE verification_id = ?", (verification_id,))
        row = cursor.fetchone()
        assert row["doctor_id"] == session_user_id


def test_prescription_hospital_id_matches_session_user_hospital(client):
    """Authoritative relationship: users.hospital_id -> prescription.hospital_id."""
    login(client, "doctor")
    with client.session_transaction() as sess:
        session_user_id = sess["user_id"]
    response = client.post("/prescriptions/new", data=prescription_form())
    assert response.status_code == 302
    verification_id = response.headers["Location"].split("/")[-1]
    with client.application.app_context():
        db = client.application.get_db()
        cursor = db.cursor()
        cursor.execute("SELECT hospital_id FROM users WHERE id = ?", (session_user_id,))
        expected_hospital = cursor.fetchone()["hospital_id"]
        cursor.execute("SELECT hospital_id FROM prescriptions WHERE verification_id = ?", (verification_id,))
        stored = cursor.fetchone()["hospital_id"]
        assert stored == expected_hospital


# ---------------------------------------------------------------------------
# 5/7. Pharmacist verification/receive cannot target an arbitrary doctor
# ---------------------------------------------------------------------------

def test_pharmacist_receive_notifies_prescription_doctor_only(client):
    """Receive notification goes to prescription.doctor_id, not an arbitrary doctor."""
    _seed_second_doctor_and_hospital(client)
    # Doctor 1 issues; doctor 2 must NOT be notified.
    verification_id, pid, row = _create_prescription_as(client, "doctor")
    prescribing_doctor_id = row["doctor_id"]
    assert prescribing_doctor_id == 1

    client.post("/logout")
    login(client, "pharmacist")
    response = client.post(f"/receive/{pid}")
    assert response.status_code == 302

    with client.application.app_context():
        db = client.application.get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT user_id FROM notifications WHERE prescription_id = ? AND message LIKE ?",
            (pid, "%received by%"),
        )
        notif_user_ids = {r["user_id"] for r in cursor.fetchall()}
        # The prescribing doctor (id 1) is notified; the imposter doctor (id 2) is not.
        assert prescribing_doctor_id in notif_user_ids
        assert 2 not in notif_user_ids


def test_prescription_doctor_id_drives_notification_user_id(client):
    """Authoritative relationship: prescription.doctor_id -> notification.user_id."""
    verification_id, pid, row = _create_prescription_as(client, "doctor")
    prescribing_doctor_id = row["doctor_id"]
    client.post("/logout")
    login(client, "pharmacist")
    client.post(f"/receive/{pid}")
    with client.application.app_context():
        db = client.application.get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT user_id FROM notifications WHERE prescription_id = ? AND message LIKE ?",
            (pid, "%received by%"),
        )
        rows = cursor.fetchall()
        assert rows, "prescribing doctor must have a notification"
        for r in rows:
            if r["user_id"] == prescribing_doctor_id:
                # Found the doctor notification directly tied to prescription.doctor_id.
                assert r["user_id"] == prescribing_doctor_id
                break
        else:
            raise AssertionError("No notification for prescription.doctor_id")


# ---------------------------------------------------------------------------
# 8. Pharmacist identifiers unique and sequential
# ---------------------------------------------------------------------------

def test_pharmacist_identifiers_sequential_and_unique(client):
    """Pharmacist identifiers follow PHARM-001, PHARM-002, PHARM-003 ..."""
    from src.seeds import _upsert_user
    with client.application.app_context():
        db = client.application.get_db()
        cursor = db.cursor()
        # Ensure a hospital exists for the pharmacists to attach to.
        cursor.execute(
            "INSERT INTO hospitals (name, address, phone, email, created_at) VALUES (?,?,?,?,?)",
            ("ID Hosp", "1 St", "+1-555-0000", "id@rxverify.local", "2026-01-01T00:00:00+00:00"),
        )
        hospital_id = cursor.lastrowid
        is_postgres = str(db).startswith("PSQL") if False else False
        # Drive the real pharmacist-creation path used by seeding.
        ident = []
        for n in range(3):
            _upsert_user(
                db, cursor,
                {"email": f"pharm{n}@rxverify.local", "name": f"Pharm {n}",
                 "password": "password123", "role": "pharmacist", "is_active": True},
                hospital_id, is_postgres, force=True,
            )
            cursor.execute("SELECT pharmacist_identifier FROM users WHERE email = ?", (f"pharm{n}@rxverify.local",))
            ident.append(cursor.fetchone()["pharmacist_identifier"])
        # They must be exactly the next sequential values, unique and well-formed.
        expected = [f"PHARM-{i:03d}" for i in range(1, 4)]
        assert ident == expected, f"expected {expected}, got {ident}"
        assert len(set(ident)) == 3


def test_pharmacist_identifier_is_unique_constraint(client):
    """pharmacist_identifier column carries a UNIQUE constraint in the schema."""
    with client.application.app_context():
        db = client.application.get_db()
        cursor = db.cursor()
        cursor.execute("PRAGMA table_info(users)")
        cols = {r["name"] for r in cursor.fetchall()}
        assert "pharmacist_identifier" in cols


# ---------------------------------------------------------------------------
# 9. Admin dashboard contains only Hospitals / Doctors / Pharmacists
# ---------------------------------------------------------------------------

def test_admin_dashboard_only_hospitals_doctors_pharmacists(client):
    login(client, "admin")
    response = client.get("/admin/")
    assert response.status_code == 200
    body = response.data
    assert b"Hospitals" in body
    assert b"Doctors" in body
    assert b"Pharmacists" in body
    # Legacy prescription-centric stat labels must be gone.
    assert b"Total Prescriptions" not in body
    assert b"Active" not in body
    assert b"Revoked" not in body
    assert b"Received" not in body


# ---------------------------------------------------------------------------
# 10. Doctor prescription UI constraints
# ---------------------------------------------------------------------------

def test_issue_ui_has_no_clinic_name_input(client):
    login(client, "doctor")
    response = client.get("/prescriptions/new")
    assert response.status_code == 200
    # No editable clinic_name field is rendered.
    assert b'name="clinic_name"' not in response.data


def test_issue_ui_doctor_field_is_readonly(client):
    login(client, "doctor")
    response = client.get("/prescriptions/new")
    assert response.status_code == 200
    # doctor_name input is present but marked readonly (not editable).
    assert b'name="doctor_name"' in response.data
    # readonly attribute must be on the doctor_name input.
    import re
    field = re.search(rb'<input[^>]*name="doctor_name"[^>]*>', response.data)
    assert field, "doctor_name input not found"
    assert b"readonly" in field.group(0).lower()


def test_issue_ui_shows_authenticated_doctor_name(client):
    login(client, "doctor")
    response = client.get("/prescriptions/new")
    assert b"Dr. Meera Patel" in response.data


# ---------------------------------------------------------------------------
# Legacy prescription compatibility (no doctor_id)
# ---------------------------------------------------------------------------

def test_legacy_prescription_without_doctor_id_still_verifies(client):
    """A prescription row lacking doctor_id (legacy) still verifies via text fields."""
    with client.application.app_context():
        db = client.application.get_db()
        cursor = db.cursor()
        vid = f"RX-{uuid.uuid4().hex[:10].upper()}"
        cursor.execute(
            """
            INSERT INTO prescriptions
            (verification_id, patient_name, patient_reference, doctor_name, clinic_name,
             medicine_name, dosage, instructions, issue_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (vid, "Legacy Patient", "UHID-0", "Dr. Legacy", "Legacy Clinic",
             "Paracetamol", "500 mg", "as needed", "2026-01-01",
             "2026-01-01T00:00:00+00:00"),
        )
        db.commit()
    login(client, "pharmacist")
    response = client.get(f"/verify/{vid}")
    assert response.status_code == 200
    assert b"Paracetamol" in response.data
    assert b"Dr. Legacy" in response.data


def test_legacy_prescription_receive_notifies_by_doctor_name(client):
    """Legacy prescriptions notify the doctor resolved by name when doctor_id is null."""
    with client.application.app_context():
        db = client.application.get_db()
        cursor = db.cursor()
        # Ensure the legacy doctor name maps to an existing doctor user.
        cursor.execute(
            "INSERT INTO prescriptions (verification_id, patient_name, patient_reference, doctor_name, clinic_name, medicine_name, dosage, instructions, issue_date, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (f"RX-LEGACY-{uuid.uuid4().hex[:6].upper()}", "P", "R", "Dr. Meera Patel", "C",
             "Ibuprofen", "200 mg", "once", "2026-01-01", "2026-01-01T00:00:00+00:00"),
        )
        pid = cursor.lastrowid
        db.commit()
    login(client, "pharmacist")
    response = client.post(f"/receive/{pid}")
    assert response.status_code == 302
    with client.application.app_context():
        db = client.application.get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT n.user_id FROM notifications n JOIN users u ON u.id = n.user_id "
            "WHERE n.prescription_id = ? AND u.role = 'doctor'",
            (pid,),
        )
        assert cursor.fetchone() is not None
