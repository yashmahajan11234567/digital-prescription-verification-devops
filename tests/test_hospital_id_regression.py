"""Regression tests for the Add Hospital redirect-ID bug.

Root cause: ``create_hospital()`` returned ``cursor.lastrowid``. psycopg2 does
NOT populate ``lastrowid`` (it stays 0), so on PostgreSQL the admin POST
``/admin/hospitals/add`` redirected to ``/admin/hospitals/0`` -> 404. On SQLite
``lastrowid`` is reliable, which is why the all-SQLite suite never caught it.

These tests lock in the contract:
  * create_hospital() returns the actual inserted primary key (non-zero)
  * get_hospital_by_id(returned_id) round-trips to the created row
  * the admin POST redirects to /admin/hospitals/<real_id> and the detail page
    returns 200 (not 404 for id 0)
  * duplicate-name handling still works
  * a PostgreSQL path (when a live DB is reachable) returns the real id too.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Make project importable when run from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.user import create_hospital, get_hospital_by_id

from tests.conftest import login


# ---------------------------------------------------------------------------
# SQLite behaviour (the project's default test backend)
# ---------------------------------------------------------------------------

class TestCreateHospitalReturnsRealIdSQLite:
    def test_create_hospital_returns_nonzero_id(self, client):
        with client.application.app_context():
            db = client.application.get_db()
            hid = create_hospital(db, "Regression Hospital", "1 R St", "+1", "ops@reg.rx")
        assert isinstance(hid, int)
        assert hid != 0

    def test_create_hospital_id_round_trips(self, client):
        with client.application.app_context():
            db = client.application.get_db()
            hid = create_hospital(db, "Roundtrip Hospital", "2 R St", "+1", "ops@rt.rx")
            row = get_hospital_by_id(db, hid)
        assert row is not None
        assert row["id"] == hid
        assert row["name"] == "Roundtrip Hospital"
        assert row["address"] == "2 R St"
        assert row["email"] == "ops@rt.rx"

    def test_successive_hospitals_get_distinct_ids(self, client):
        with client.application.app_context():
            db = client.application.get_db()
            a = create_hospital(db, "First Hospital")
            b = create_hospital(db, "Second Hospital")
        assert a != b
        assert a != 0 and b != 0
        # Newer insert must have a strictly greater id under the identity column.
        assert b > a


class TestAddHospitalRedirectsToRealId:
    def test_post_redirects_to_actual_id(self, client):
        login(client, "admin")
        r = client.post("/admin/hospitals/add", data={
            "name": "Redirect Hospital", "address": "3 R St", "email": "ops@red.rx"
        }, follow_redirects=False)
        assert r.status_code == 302
        location = r.headers["Location"]
        assert location.startswith("/admin/hospitals/")
        # The trailing segment must be a real, non-zero id, not "0".
        suffix = location.rstrip("/").split("/")[-1]
        assert suffix != "0"
        assert suffix.isdigit()

    def test_detail_page_returns_200_not_404(self, client):
        login(client, "admin")
        r = client.post("/admin/hospitals/add", data={
            "name": "Detail Hospital", "address": "4 D St", "email": "ops@det.rx"
        }, follow_redirects=False)
        assert r.status_code == 302
        detail = client.get(r.headers["Location"])
        assert detail.status_code == 200
        assert b"Detail Hospital" in detail.data

    def test_redirect_target_is_real_hospital(self, client):
        login(client, "admin")
        r = client.post("/admin/hospitals/add", data={
            "name": "Verify Hospital", "address": "5 V St"
        }, follow_redirects=False)
        hid = int(r.headers["Location"].rstrip("/").split("/")[-1])
        assert hid != 0
        with client.application.app_context():
            db = client.application.get_db()
            row = get_hospital_by_id(db, hid)
        assert row is not None
        assert row["name"] == "Verify Hospital"


class TestAddHospitalDuplicateHandling:
    def test_duplicate_name_still_rejected(self, client):
        login(client, "admin")
        good = {"name": "Dup Regression Hospital"}
        assert client.post("/admin/hospitals/add", data=good).status_code == 302
        r = client.post("/admin/hospitals/add", data=good)
        assert r.status_code == 400
        assert b"already exists" in r.data

    def test_no_orphan_created_on_duplicate(self, client):
        login(client, "admin")
        name = "Dup Count Hospital"
        client.post("/admin/hospitals/add", data={"name": name})
        client.post("/admin/hospitals/add", data={"name": name})  # rejected
        with client.application.app_context():
            db = client.application.get_db()
            cur = db.cursor()
            cur.execute("SELECT COUNT(*) AS c FROM hospitals WHERE name = ?", (name,))
            assert cur.fetchone()["c"] == 1


# ---------------------------------------------------------------------------
# PostgreSQL behaviour (only runs when a live DB is reachable)
# ---------------------------------------------------------------------------

def _pg_available() -> bool:
    """Return True if a live PostgreSQL DATABASE_URL is configured & reachable."""
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql://") and not url.startswith("postgres://"):
        return False
    from src import create_app
    app = create_app({"TESTING": True, "DATABASE_URL": url, "SECRET_KEY": "test"})
    try:
        with app.app_context():
            db = app.get_db()
            ok = getattr(db, "_conn", None) is not None and type(db._conn).__module__.startswith("psycopg2")
    except Exception:
        return False
    return ok


@pytest.mark.skipif(not _pg_available(), reason="No live PostgreSQL DATABASE_URL configured")
class TestCreateHospitalReturnsRealIdPostgres:
    def test_returns_real_nonzero_id_on_postgres(self):
        url = os.environ["DATABASE_URL"]
        from src import create_app
        app = create_app({"TESTING": True, "DATABASE_URL": url, "SECRET_KEY": "test"})
        with app.app_context():
            db = app.get_db()
            hid = create_hospital(db, "PG Regression Hospital", "pg", "+1", "pg@reg.rx")
            try:
                assert isinstance(hid, int)
                assert hid != 0, "psycopg2 lastrowid bug: returned 0 instead of real id"
                row = get_hospital_by_id(db, hid)
                assert row is not None
                assert row["id"] == hid
            finally:
                cur = db.cursor()
                cur.execute("DELETE FROM hospitals WHERE name = %s", ("PG Regression Hospital",))
                db.commit()

    def test_post_redirects_to_actual_id_on_postgres(self):
        url = os.environ["DATABASE_URL"]
        from src import create_app
        app = create_app({"TESTING": True, "DATABASE_URL": url, "SECRET_KEY": "test"})
        with app.app_context():
            from src.seeds import seed_development_users
            seed_development_users(app)
            c = app.test_client()
            # Log in as admin (seeded dev user) and exercise the POST.
            c.post("/login/admin", data={"email": "admin@rxverify.local", "password": "admin123"})
            r = c.post("/admin/hospitals/add", data={
                "name": "PG Redirect Hospital", "address": "pg", "email": "pgred@reg.rx"
            }, follow_redirects=False)
            try:
                assert r.status_code == 302
                assert r.headers["Location"].rstrip("/").split("/")[-1] != "0"
            finally:
                d = app.get_db()
                cur = d.cursor()
                cur.execute("DELETE FROM hospitals WHERE name = %s", ("PG Redirect Hospital",))
                d.commit()
