"""Regression test for the PostgreSQL/SQLite schema migration defect.

Root cause: doctor_id/hospital_id were added to the prescriptions CREATE TABLE
definition, but existing tables cause create_table() to return early without
reconciliation, and no ALTER TABLE migration existed. A persistent database
created by older code therefore retained the old schema and lacked these two
columns, while the application code expected them.

This test reproduces CASE 2 (existing database) by building a prescriptions
table WITHOUT doctor_id/hospital_id, inserting a row, then letting create_app()
run init_db(), which must migrate the table in place via ALTER TABLE. The test
verifies the columns are added and existing rows are preserved.
"""

import sqlite3

from src import create_app


def _build_legacy_db(db_path: str) -> None:
    """Create a legacy-schema database: prescriptions lacks doctor_id/hospital_id.

    Mirrors the schema an older deployment created before the columns were added
    to the CREATE TABLE definition. Existing prescription rows are inserted so we
    can later assert they survive the migration untouched.
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE hospitals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                address TEXT,
                phone TEXT,
                email TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        # Legacy prescriptions table: deliberately MISSING doctor_id/hospital_id.
        conn.execute(
            """
            CREATE TABLE prescriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                verification_id TEXT NOT NULL UNIQUE,
                patient_name TEXT NOT NULL,
                patient_reference TEXT NOT NULL,
                doctor_name TEXT NOT NULL,
                clinic_name TEXT NOT NULL,
                medicine_name TEXT NOT NULL,
                dosage TEXT NOT NULL,
                instructions TEXT NOT NULL,
                issue_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                received_at TEXT,
                received_by_user_id INTEGER
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                prescription_id INTEGER
            )
            """
        )
        # Insert an existing prescription row that must survive the migration.
        conn.execute(
            """
            INSERT INTO prescriptions (
                verification_id, patient_name, patient_reference, doctor_name,
                clinic_name, medicine_name, dosage, instructions, issue_date,
                status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "RX-LEGACY0001",
                "Legacy Patient",
                "UHID-OLD1",
                "Dr. Legacy",
                "Old Clinic",
                "Paracetamol",
                "500 mg",
                "As needed",
                "2026-01-01",
                "active",
                "2026-01-01T00:00:00",
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _prescription_columns(db_path: str) -> list[str]:
    conn = sqlite3.connect(db_path)
    try:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(prescriptions)")]
        return cols
    finally:
        conn.close()


def test_existing_prescriptions_table_migrated_in_place(tmp_path):
    """An existing prescriptions table missing doctor_id/hospital_id receives them.

    This exercises the init_db() ALTER TABLE migration rather than the CREATE TABLE
    definition: the table already exists (legacy schema, no doctor_id/hospital_id),
    so create_table() returns early and the columns must be added by the migration.
    """
    db_path = tmp_path / "legacy.db"
    _build_legacy_db(str(db_path))

    # Sanity: the legacy table really lacks the columns before migration.
    columns_before = _prescription_columns(str(db_path))
    assert "doctor_id" not in columns_before
    assert "hospital_id" not in columns_before

    # create_app() runs init_db() in its app context, triggering the migration.
    app = create_app({
        "TESTING": True,
        "DATABASE_URL": f"sqlite:///{db_path}",
        "SECRET_KEY": "test",
    })
    # app_context __exit__ is managed by the fixture-less app; re-open to verify.
    with app.app_context():
        columns_after = _prescription_columns(str(db_path))

    assert "doctor_id" in columns_after
    assert "hospital_id" in columns_after

    # Existing row must be preserved (no data loss).
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT verification_id, patient_name FROM prescriptions WHERE verification_id = 'RX-LEGACY0001'"
        ).fetchone()
    assert row is not None
    assert row[0] == "RX-LEGACY0001"
    assert row[1] == "Legacy Patient"


def test_migration_is_idempotent(tmp_path):
    """Running init_db() twice must not error or duplicate the columns.

    A second create_app() against the same database path re-runs init_db(),
    which re-executes the ALTER TABLE migration. It must complete without error
    and leave exactly one doctor_id and one hospital_id column.
    """
    db_path = tmp_path / "legacy_idem.db"
    _build_legacy_db(str(db_path))

    # First run: migrates the legacy table in place.
    app1 = create_app({
        "TESTING": True,
        "DATABASE_URL": f"sqlite:///{db_path}",
        "SECRET_KEY": "test",
    })
    with app1.app_context():
        cols_after_first = _prescription_columns(str(db_path))
    assert "doctor_id" in cols_after_first
    assert "hospital_id" in cols_after_first

    # Second run against the SAME database: must be a safe no-op.
    app2 = create_app({
        "TESTING": True,
        "DATABASE_URL": f"sqlite:///{db_path}",
        "SECRET_KEY": "test",
    })
    with app2.app_context():
        cols_after_second = _prescription_columns(str(db_path))

    # No duplicate columns introduced by the repeated migration.
    assert cols_after_second.count("doctor_id") == 1
    assert cols_after_second.count("hospital_id") == 1

    # Existing row still preserved across both runs.
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT verification_id FROM prescriptions WHERE verification_id = 'RX-LEGACY0001'"
        ).fetchone()
    assert row is not None
