"""Regression tests for the PostgreSQL lastrowid class of bug.

Background
----------
psycopg2 does NOT populate ``cursor.lastrowid`` (it stays 0). Several DAL
insert helpers historically relied on ``cursor.lastrowid`` to report the
newly-created primary key. On PostgreSQL this returned 0 instead of the real
id. ``create_hospital()`` was already fixed; this file locks in the same fix
for ``create_user()`` and ``create_notification()``.

These tests are backend-agnostic: they run against whatever database the test
session is configured with (SQLite by default, PostgreSQL if ``DATABASE_URL``
points at one). They assert that the id returned by the helper matches the id
of the row actually persisted, which is the property that broke on PostgreSQL.

This guards against a regression of the root cause (RETURNING id vs lastrowid)
on both backends without introducing a second DB abstraction.
"""
from __future__ import annotations

import pytest

from src.models.user import (
    create_user,
    generate_pharmacist_identifier,
    get_user_by_id,
)
from src.models.notifications import create_notification, get_notifications_by_user


def _backend_name(db) -> str:
    conn = getattr(db, "_conn", None)
    if conn is None:
        return "sqlite"
    module = type(conn).__module__
    return "postgres" if module.startswith("psycopg2") else "sqlite"


class TestCreateUserReturnsRealId:
    def test_create_user_returns_persisted_id(self, client):
        with client.application.app_context():
            db = client.application.get_db()
            created = create_user(db, "audit_u_1@rx.local", "Audit U", "pass123", "doctor")
            # The returned id must be the real primary key of the persisted row.
            persisted = get_user_by_id(db, created.id)
            assert persisted is not None, "create_user returned an id with no matching row"
            assert persisted.id == created.id
            assert persisted.email == "audit_u_1@rx.local"

    def test_create_user_id_not_zero_on_postgres(self, client):
        with client.application.app_context():
            db = client.application.get_db()
            backend = _backend_name(db)
            created = create_user(db, "audit_u_2@rx.local", "Audit U2", "pass123", "doctor")
            if backend == "postgres":
                # This was the previously-broken behaviour: psycopg2 lastrowid == 0.
                assert created.id != 0, "PostgreSQL must return the real inserted id, not 0"
            # On SQLite lastrowid is reliable; just assert round-trips.
            persisted = get_user_by_id(db, created.id)
            assert persisted.id == created.id

    def test_create_user_doctor_carries_hospital_id(self, client):
        with client.application.app_context():
            db = client.application.get_db()
            # Find a real hospital to satisfy the FK.
            cur = db.cursor()
            cur.execute("SELECT id FROM hospitals ORDER BY id LIMIT 1")
            first = cur.fetchone()
            hospital_id = first["id"] if first else None
            created = create_user(
                db, "audit_u_3@rx.local", "Audit U3", "pass123", "doctor", hospital_id=hospital_id
            )
            persisted = get_user_by_id(db, created.id)
            assert persisted.hospital_id == hospital_id

    def test_create_user_pharmacist_carries_identifier(self, client):
        with client.application.app_context():
            db = client.application.get_db()
            identifier = generate_pharmacist_identifier(db)
            created = create_user(
                db, "audit_u_4@rx.local", "Audit U4", "pass123", "pharmacist",
                pharmacist_identifier=identifier,
            )
            persisted = get_user_by_id(db, created.id)
            assert persisted.pharmacist_identifier == identifier


class TestCreateNotificationReturnsRealId:
    def test_create_notification_returns_persisted_id(self, client):
        with client.application.app_context():
            db = client.application.get_db()
            created = create_user(db, "audit_n_user@rx.local", "Audit N", "pass123", "doctor")
            note = create_notification(db, created.id, "audit notification")
            # The returned id must match the persisted notification row.
            notes = get_notifications_by_user(db, created.id)
            assert notes
            assert any(n.id == note.id for n in notes)
            assert note.user_id == created.id

    def test_create_notification_id_not_zero_on_postgres(self, client):
        with client.application.app_context():
            db = client.application.get_db()
            backend = _backend_name(db)
            created = create_user(db, "audit_n_user2@rx.local", "Audit N2", "pass123", "doctor")
            note = create_notification(db, created.id, "audit notification 2")
            if backend == "postgres":
                assert note.id != 0, "PostgreSQL must return the real inserted id, not 0"
            notes = get_notifications_by_user(db, created.id)
            assert any(n.id == note.id for n in notes)
            assert note.user_id == created.id


def test_no_existing_data_modified(client):
    """Guard: the fix does not mutate pre-existing rows."""
    with client.application.app_context():
        db = client.application.get_db()
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM users")
        before = cur.fetchone()["c"]
        # Exercise both helpers.
        created = create_user(db, "audit_guard@rx.local", "Guard", "pass123", "doctor")
        create_notification(db, created.id, "guard note")
        cur.execute("SELECT COUNT(*) AS c FROM users")
        after = cur.fetchone()["c"]
        # Only the one user we created is added.
        assert after == before + 1
