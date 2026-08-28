"""Tests for admin provisioning: hospitals, doctors, pharmacists.

Covers the requirement-gap items A, B, E, G and the surrounding security
behaviour. Existing 132-test functionality must remain intact.
"""
from __future__ import annotations

import pytest

from src.models.user import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    generate_pharmacist_identifier,
    create_hospital,
)

from tests.conftest import login


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _doctor_login(client, email, password):
    return client.post("/login/doctor", data={"email": email, "password": password})


def _pharmacist_login(client, email, password):
    return client.post("/login/pharmacist", data={"email": email, "password": password})


# ---------------------------------------------------------------------------
# PHARM identifier helper (shared by seeds + admin)
# ---------------------------------------------------------------------------

class TestPharmacistIdentifierHelper:
    def test_first_identifier_is_pharm_001(self, client):
        with client.application.app_context():
            db = client.application.get_db()
            assert generate_pharmacist_identifier(db) == "PHARM-001"

    def test_subsequent_identifiers_sequential(self, client):
        with client.application.app_context():
            db = client.application.get_db()
            create_user(db, "ph1@rx.local", "P1", "password123", "pharmacist",
                        pharmacist_identifier="PHARM-001")
            assert generate_pharmacist_identifier(db) == "PHARM-002"

    def test_skips_existing_gaps(self, client):
        with client.application.app_context():
            db = client.application.get_db()
            # Manually plant PHARM-001, PHARM-002, PHARM-005
            cur = db.cursor()
            cur.execute(
                "INSERT INTO users (email, name, password_hash, role, is_active, pharmacist_identifier, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                ("ph1@rx.local", "P1", "x", "pharmacist", 1, "PHARM-001", "now", "now"),
            )
            cur.execute(
                "INSERT INTO users (email, name, password_hash, role, is_active, pharmacist_identifier, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                ("ph2@rx.local", "P2", "x", "pharmacist", 1, "PHARM-002", "now", "now"),
            )
            cur.execute(
                "INSERT INTO users (email, name, password_hash, role, is_active, pharmacist_identifier, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                ("ph5@rx.local", "P5", "x", "pharmacist", 1, "PHARM-005", "now", "now"),
            )
            db.commit()
            # Must not collide with existing PHARM-001/002/005 -> PHARM-003
            assert generate_pharmacist_identifier(db) == "PHARM-003"

    def test_seeds_and_admin_share_helper(self, client):
        """Admin creation must not duplicate IDs already seeded."""
        with client.application.app_context():
            db = client.application.get_db()
            # Seeded pharmacist via the shared helper pattern.
            ident = generate_pharmacist_identifier(db)
            assert ident == "PHARM-001"
            create_user(db, "ph1@rx.local", "P1", "password123", "pharmacist",
                        pharmacist_identifier=ident)
            assert generate_pharmacist_identifier(db) == "PHARM-002"


# ---------------------------------------------------------------------------
# ADMIN HOSPITAL
# ---------------------------------------------------------------------------

class TestAdminHospital:
    def test_get_add_hospital_page(self, client):
        login(client, "admin")
        r = client.get("/admin/hospitals/add")
        assert r.status_code == 200
        assert b"Add Hospital" in r.data

    def test_post_valid_hospital(self, client):
        login(client, "admin")
        r = client.post("/admin/hospitals/add", data={
            "name": "Northgate Hospital",
            "address": "1 North Rd",
            "phone": "+1-555-9999",
            "email": "ops@northgate.rx",
        }, follow_redirects=True)
        assert r.status_code == 200
        with client.application.app_context():
            db = client.application.get_db()
            cur = db.cursor()
            cur.execute("SELECT * FROM hospitals WHERE name = ?", ("Northgate Hospital",))
            row = cur.fetchone()
            assert row is not None
            assert row["address"] == "1 North Rd"
            assert row["email"] == "ops@northgate.rx"

    def test_hospital_appears_in_admin_list(self, client):
        login(client, "admin")
        client.post("/admin/hospitals/add", data={
            "name": "Westgate Hospital", "address": "2 West Rd", "email": "ops@westgate.rx"
        })
        r = client.get("/admin/hospitals")
        assert r.status_code == 200
        assert b"Westgate Hospital" in r.data

    def test_invalid_hospital_submission(self, client):
        login(client, "admin")
        r = client.post("/admin/hospitals/add", data={"name": ""})
        assert r.status_code == 400
        assert b"Hospital name is required" in r.data
        with client.application.app_context():
            db = client.application.get_db()
            cur = db.cursor()
            cur.execute("SELECT COUNT(*) AS c FROM hospitals WHERE name = ''")
            assert cur.fetchone()["c"] == 0

    def test_duplicate_hospital_rejected(self, client):
        login(client, "admin")
        client.post("/admin/hospitals/add", data={"name": "Dupe Hospital"})
        r = client.post("/admin/hospitals/add", data={"name": "Dupe Hospital"})
        assert r.status_code == 400
        assert b"already exists" in r.data

    def test_unauthorized_access_denied(self, client):
        # Not logged in
        assert client.get("/admin/hospitals/add").status_code == 302
        assert client.post("/admin/hospitals/add", data={"name": "X"}).status_code == 302
        # Doctor cannot
        login(client, "doctor")
        assert client.get("/admin/hospitals/add").status_code == 302
        assert client.post("/admin/hospitals/add", data={"name": "X"}).status_code == 302
        # Pharmacist cannot
        login(client, "pharmacist")
        assert client.get("/admin/hospitals/add").status_code == 302


# ---------------------------------------------------------------------------
# ADMIN DOCTOR
# ---------------------------------------------------------------------------

class TestAdminDoctor:
    def _make_hospital(self, client, name="Doc Hospital"):
        login(client, "admin")
        client.post("/admin/hospitals/add", data={"name": name})
        with client.application.app_context():
            db = client.application.get_db()
            cur = db.cursor()
            cur.execute("SELECT id FROM hospitals WHERE name = ?", (name,))
            return cur.fetchone()["id"]

    def test_register_doctor_under_hospital(self, client):
        hid = self._make_hospital(client, "Register Hospital")
        login(client, "admin")
        r = client.post(f"/admin/hospitals/{hid}/doctors/add", data={
            "name": "Dr. New Doc", "email": "newdoc@rx.local", "password": "secret123"
        }, follow_redirects=True)
        assert r.status_code == 200
        with client.application.app_context():
            db = client.application.get_db()
            user = get_user_by_email(db, "newdoc@rx.local")
            assert user is not None
            assert user.role == "doctor"
            assert user.hospital_id == hid
            assert user.is_active is True

    def test_password_is_hashed_not_plaintext(self, client):
        hid = self._make_hospital(client, "Hash Hospital")
        login(client, "admin")
        client.post(f"/admin/hospitals/{hid}/doctors/add", data={
            "name": "Dr. Hash", "email": "hashdoc@rx.local", "password": "secret123"
        })
        with client.application.app_context():
            db = client.application.get_db()
            user = get_user_by_email(db, "hashdoc@rx.local")
            assert user.password_hash != "secret123"
            assert user.verify_password("secret123")
            assert "secret123" not in user.password_hash

    def test_doctor_can_subsequently_login(self, client):
        hid = self._make_hospital(client, "Login Hospital")
        login(client, "admin")
        client.post(f"/admin/hospitals/{hid}/doctors/add", data={
            "name": "Dr. Login", "email": "logindoc@rx.local", "password": "secret123"
        })
        r = _doctor_login(client, "logindoc@rx.local", "secret123")
        assert r.status_code == 302
        assert "/prescriptions/new" in r.headers.get("Location", "")

    def test_doctor_role_only_cannot_be_admin(self, client):
        """A doctor provisioned by admin has role doctor, never admin."""
        hid = self._make_hospital(client, "Role Hospital")
        login(client, "admin")
        client.post(f"/admin/hospitals/{hid}/doctors/add", data={
            "name": "Dr. Role", "email": "roledoc@rx.local", "password": "secret123"
        })
        with client.application.app_context():
            db = client.application.get_db()
            user = get_user_by_email(db, "roledoc@rx.local")
            assert user.role == "doctor"

    def test_hospital_id_is_server_controlled(self, client):
        """Client cannot associate the doctor with a different hospital."""
        hid = self._make_hospital(client, "Real Hospital")
        other_name = "Other Hospital"
        login(client, "admin")
        client.post("/admin/hospitals/add", data={"name": other_name})
        with client.application.app_context():
            db = client.application.get_db()
            cur = db.cursor()
            cur.execute("SELECT id FROM hospitals WHERE name = ?", (other_name,))
            other_id = cur.fetchone()["id"]
        # Attempt to tamper with hospital_id via form field
        login(client, "admin")
        client.post(f"/admin/hospitals/{hid}/doctors/add", data={
            "name": "Dr. Tamper", "email": "tamper@rx.local", "password": "secret123",
            "hospital_id": other_id,
        })
        with client.application.app_context():
            db = client.application.get_db()
            user = get_user_by_email(db, "tamper@rx.local")
            assert user.hospital_id == hid  # server value wins, not hidden field

    def test_invalid_hospital_id_rejected(self, client):
        login(client, "admin")
        r = client.get("/admin/hospitals/999999/doctors/add")
        assert r.status_code == 404
        r = client.post("/admin/hospitals/999999/doctors/add", data={
            "name": "X", "email": "x@rx.local", "password": "secret123"
        })
        assert r.status_code == 404

    def test_duplicate_email_rejected(self, client):
        hid = self._make_hospital(client, "Dup Hospital")
        login(client, "admin")
        good = {"name": "Dr. Dup", "email": "dupdoc@rx.local", "password": "secret123"}
        assert client.post(f"/admin/hospitals/{hid}/doctors/add", data=good).status_code == 302
        r = client.post(f"/admin/hospitals/{hid}/doctors/add", data=good)
        assert r.status_code == 400
        assert b"already exists" in r.data

    def test_unauthorized_access_denied(self, client):
        hid = self._make_hospital(client, "Unauth Hospital")
        # Doctor cannot register a doctor
        login(client, "doctor")
        assert client.get(f"/admin/hospitals/{hid}/doctors/add").status_code == 302
        assert client.post(f"/admin/hospitals/{hid}/doctors/add",
                           data={"name": "X", "email": "x@rx.local", "password": "secret123"}).status_code == 302
        # Pharmacist cannot
        login(client, "pharmacist")
        assert client.get(f"/admin/hospitals/{hid}/doctors/add").status_code == 302

    def test_weak_password_rejected(self, client):
        hid = self._make_hospital(client, "Weak Hospital")
        login(client, "admin")
        r = client.post(f"/admin/hospitals/{hid}/doctors/add", data={
            "name": "Dr. Weak", "email": "weak@rx.local", "password": "123"
        })
        assert r.status_code == 400
        assert b"at least 6 characters" in r.data


# ---------------------------------------------------------------------------
# ADMIN PHARMACIST
# ---------------------------------------------------------------------------

class TestAdminPharmacist:
    def test_get_pharmacist_page(self, client):
        login(client, "admin")
        r = client.get("/admin/pharmacists")
        assert r.status_code == 200
        assert b"Pharmacists" in r.data

    def test_post_valid_pharmacist(self, client):
        login(client, "admin")
        r = client.post("/admin/pharmacists/add", data={
            "name": "Pharm One", "email": "pharmone@rx.local", "password": "secret123"
        }, follow_redirects=True)
        assert r.status_code == 200
        with client.application.app_context():
            db = client.application.get_db()
            user = get_user_by_email(db, "pharmone@rx.local")
            assert user is not None
            assert user.role == "pharmacist"
            assert user.pharmacist_identifier == "PHARM-001"

    def test_second_pharmacist_gets_pharm_002(self, client):
        login(client, "admin")
        client.post("/admin/pharmacists/add", data={
            "name": "Pharm One", "email": "pharmone@rx.local", "password": "secret123"
        })
        client.post("/admin/pharmacists/add", data={
            "name": "Pharm Two", "email": "pharmtwo@rx.local", "password": "secret123"
        })
        with client.application.app_context():
            db = client.application.get_db()
            u1 = get_user_by_email(db, "pharmone@rx.local")
            u2 = get_user_by_email(db, "pharmtwo@rx.local")
            assert u1.pharmacist_identifier == "PHARM-001"
            assert u2.pharmacist_identifier == "PHARM-002"

    def test_identifiers_remain_unique(self, client):
        login(client, "admin")
        for i in range(5):
            client.post("/admin/pharmacists/add", data={
                "name": f"Pharm {i}", "email": f"pharm{i}@rx.local", "password": "secret123"
            })
        with client.application.app_context():
            db = client.application.get_db()
            cur = db.cursor()
            cur.execute(
                "SELECT pharmacist_identifier, COUNT(*) AS c FROM users "
                "WHERE role='pharmacist' GROUP BY pharmacist_identifier HAVING c > 1"
            )
            assert cur.fetchone() is None

    def test_pharmacist_can_subsequently_login(self, client):
        login(client, "admin")
        client.post("/admin/pharmacists/add", data={
            "name": "Pharm Login", "email": "pharmlogin@rx.local", "password": "secret123"
        })
        r = _pharmacist_login(client, "pharmlogin@rx.local", "secret123")
        assert r.status_code == 302
        assert "/verify" in r.headers.get("Location", "")

    def test_password_hashed(self, client):
        login(client, "admin")
        client.post("/admin/pharmacists/add", data={
            "name": "Pharm Hash", "email": "pharmhash@rx.local", "password": "secret123"
        })
        with client.application.app_context():
            db = client.application.get_db()
            user = get_user_by_email(db, "pharmhash@rx.local")
            assert user.password_hash != "secret123"
            assert user.verify_password("secret123")

    def test_identifier_not_client_controllable(self, client):
        login(client, "admin")
        client.post("/admin/pharmacists/add", data={
            "name": "Pharm T", "email": "pharmt@rx.local", "password": "secret123",
            "pharmacist_identifier": "PHARM-999",  # must be ignored
        })
        with client.application.app_context():
            db = client.application.get_db()
            user = get_user_by_email(db, "pharmt@rx.local")
            assert user.pharmacist_identifier == "PHARM-001"

    def test_duplicate_email_rejected(self, client):
        login(client, "admin")
        good = {"name": "Pharm Dup", "email": "pharmdup@rx.local", "password": "secret123"}
        assert client.post("/admin/pharmacists/add", data=good).status_code == 302
        r = client.post("/admin/pharmacists/add", data=good)
        assert r.status_code == 400
        assert b"already exists" in r.data

    def test_unauthorized_access_denied(self, client):
        assert client.get("/admin/pharmacists/add").status_code == 302
        assert client.post("/admin/pharmacists/add",
                           data={"name": "X", "email": "x@rx.local", "password": "secret123"}).status_code == 302
        login(client, "doctor")
        assert client.get("/admin/pharmacists/add").status_code == 302
        assert client.post("/admin/pharmacists/add",
                           data={"name": "X", "email": "x@rx.local", "password": "secret123"}).status_code == 302
        login(client, "pharmacist")
        assert client.get("/admin/pharmacists/add").status_code == 302

    def test_weak_password_rejected(self, client):
        login(client, "admin")
        r = client.post("/admin/pharmacists/add", data={
            "name": "Pharm Weak", "email": "pharmweak@rx.local", "password": "123"
        })
        assert r.status_code == 400
        assert b"at least 6 characters" in r.data


# ---------------------------------------------------------------------------
# ADMIN DASHBOARD STATS
# ---------------------------------------------------------------------------

class TestAdminDashboardStats:
    def test_hospitals_doctors_pharmacists_present(self, client):
        login(client, "admin")
        r = client.get("/admin/")
        assert r.status_code == 200
        assert b"Hospitals" in r.data
        assert b"Doctors" in r.data
        assert b"Pharmacists" in r.data

    def test_prescription_stats_absent(self, client):
        login(client, "admin")
        r = client.get("/admin/")
        body = r.data
        assert b"Total Prescriptions" not in body
        assert b"Active" not in body
        assert b"Revoked" not in body
        assert b"Received" not in body

    def test_nav_reaches_pharmacists(self, client):
        login(client, "admin")
        r = client.get("/admin/")
        assert b"Add Hospital" in r.data
        assert b"Add Pharmacist" in r.data
        # Pharmacists nav link in header
        r2 = client.get("/admin/")
        assert b"href=\"/admin/pharmacists\"" in r2.data or b"/admin/pharmacists" in r2.data


# ---------------------------------------------------------------------------
# INTEGRATION: hospital -> doctor -> prescription
# ---------------------------------------------------------------------------

class TestHospitalDoctorPrescriptionIntegration:
    def test_full_flow(self, client):
        # Admin creates hospital
        login(client, "admin")
        client.post("/admin/hospitals/add", data={
            "name": "Integration Hospital", "address": "9 Int Rd", "email": "ops@int.rx"
        })
        with client.application.app_context():
            db = client.application.get_db()
            cur = db.cursor()
            cur.execute("SELECT id FROM hospitals WHERE name = ?", ("Integration Hospital",))
            hid = cur.fetchone()["id"]
        # Admin registers doctor
        client.post(f"/admin/hospitals/{hid}/doctors/add", data={
            "name": "Dr. Integ", "email": "integdoc@rx.local", "password": "secret123"
        })
        # Doctor logs in and creates prescription
        _doctor_login(client, "integdoc@rx.local", "secret123")
        r = client.post("/prescriptions/new", data={
            "patient_name": "Pat", "patient_reference": "UHID-1",
            "medicine_name": "Ibuprofen", "dosage": "200mg",
            "instructions": "as needed", "issue_date": "2026-08-16",
        }, follow_redirects=False)
        assert r.status_code == 302
        verification_id = r.headers["Location"].rstrip("/").split("/")[-1]
        with client.application.app_context():
            db = client.application.get_db()
            cur = db.cursor()
            cur.execute("SELECT * FROM prescriptions WHERE verification_id = ?", (verification_id,))
            p = cur.fetchone()
            doctor = get_user_by_email(db, "integdoc@rx.local")
            assert p["doctor_id"] == doctor.id
            assert p["hospital_id"] == hid


# ---------------------------------------------------------------------------
# INTEGRATION: pharmacist -> verify -> notify doctor
# ---------------------------------------------------------------------------

class TestPharmacistVerifyNotifyIntegration:
    def test_full_flow(self, client):
        # Set up: hospital + doctor + prescription
        with client.application.app_context():
            db = client.application.get_db()
            hid = create_hospital(db, "Notify Hospital", "1 N Rd", "+1-555", "op@n.rx")
            doc = create_user(db, "notifydoc@rx.local", "Dr. Notify", "secret123",
                              "doctor", hospital_id=hid)
            cur = db.cursor()
            cur.execute(
                "INSERT INTO prescriptions "
                "(verification_id, patient_name, patient_reference, doctor_name, clinic_name, "
                "doctor_id, hospital_id, medicine_name, dosage, instructions, issue_date, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                ("RX-NOTIFY1234", "Pat", "UHID-9", "Dr. Notify", "Notify Hospital",
                 doc.id, hid, "Paracetamol", "500mg", "as needed", "2026-08-16", "now"),
            )
            db.commit()
        # Admin creates pharmacist
        login(client, "admin")
        client.post("/admin/pharmacists/add", data={
            "name": "Pharm Notify", "email": "pharmnotify@rx.local", "password": "secret123"
        })
        # Pharmacist logs in and receives prescription
        _pharmacist_login(client, "pharmnotify@rx.local", "secret123")
        r = client.post("/receive/1", follow_redirects=False)
        assert r.status_code == 302
        with client.application.app_context():
            db = client.application.get_db()
            cur = db.cursor()
            cur.execute(
                "SELECT * FROM notifications WHERE user_id = ? AND prescription_id = 1",
                (doc.id,),
            )
            notif = cur.fetchone()
            assert notif is not None
            # Prescription marked received by this pharmacist
            cur.execute("SELECT received_by_user_id FROM prescriptions WHERE id = 1")
            assert cur.fetchone()["received_by_user_id"] is not None
