"""RxVerify Flask application package."""
from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

from config import get_config
from src.decorators import require_role, require_any_role


class SQLiteConnection:
    """Wrapper for SQLite connection to provide PostgreSQL-compatible interface."""

    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return self._conn.cursor()

    def execute(self, query: str, params: tuple = ()):
        """Execute query with ? placeholders (SQLite style)."""
        return self._conn.execute(query, params)

    def fetchone(self):
        return self._conn.fetchone()

    def fetchall(self):
        return self._conn.fetchall()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    @property
    def rowcount(self):
        return self._conn.rowcount


class _PSQLCursor:
    """Wrapper for psycopg2 cursor to convert ? placeholders to %s."""

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query: str, params: tuple = ()):
        # Convert ? placeholders to %s for PostgreSQL
        if "?" in query:
            query = query.replace("?", "%s")
        return self._cursor.execute(query, params)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class PSQLConnection:
    """Wrapper for PostgreSQL connection to provide SQLite-compatible interface."""

    def __init__(self, **kwargs):
        self._conn = psycopg2.connect(**kwargs)

    def cursor(self):
        return _PSQLCursor(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def create_app(test_config: dict | None = None) -> Flask:
    """Create and configure the Flask application."""
    config_class = get_config()
    # Templates and static files are at the project root
    app = Flask(__name__, instance_relative_config=True, template_folder="../templates", static_folder="../static")

    if test_config:
        # Testing config overrides everything
        app.config.from_mapping(test_config)
    else:
        app.config.from_object(config_class)

    # Load environment variables from .env file if present
    from dotenv import load_dotenv
    load_dotenv()

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    # No hardcoded USERS - authentication uses database-backed users table

    # Database abstraction layer
    def _parse_db_url(url: str) -> dict:
        """Parse DATABASE_URL into connection parameters."""
        if url.startswith("sqlite:///"):
            return {"type": "sqlite", "path": url[10:]}
        elif url.startswith("postgresql://") or url.startswith("postgres://"):
            # postgresql://user:pass@host:port/dbname
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            return {
                "type": "postgresql",
                "host": parsed.hostname,
                "port": parsed.port or 5432,
                "database": parsed.path.lstrip("/"),
                "user": parsed.username,
                "password": parsed.password,
            }
        else:
            # Default to SQLite
            return {"type": "sqlite", "path": url}

    def get_db():
        """Get database connection for current request."""
        db_url = app.config.get("DATABASE_URL", "sqlite:///instance/prescriptions.db")
        db_info = _parse_db_url(db_url)

        if "db" not in g:
            if db_info["type"] == "postgresql":
                if not HAS_POSTGRES:
                    raise RuntimeError("psycopg2 is required for PostgreSQL but not installed")
                from psycopg2.extras import RealDictCursor
                g.db = PSQLConnection(
                    host=db_info["host"],
                    port=db_info["port"],
                    dbname=db_info["database"],
                    user=db_info["user"],
                    password=db_info["password"],
                    cursor_factory=RealDictCursor,
                )
            else:
                import sqlite3
                g.db = sqlite3.connect(db_info["path"])
                g.db.row_factory = sqlite3.Row
                g.db = SQLiteConnection(g.db)
        return g.db

    @app.teardown_appcontext
    def close_db(_error: BaseException | None = None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    # Attach get_db to app for blueprints to use (must be before init_db/seed)
    app.get_db = get_db

    def init_db() -> None:
        """Initialize database schema."""
        db = get_db()
        cursor = db.cursor()
        db_url = app.config.get("DATABASE_URL", "sqlite:///instance/prescriptions.db")
        is_postgres = db_url.startswith("postgresql://") or db_url.startswith("postgres://")

        if is_postgres:
            id_column = "id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY"
        else:
            id_column = "id INTEGER PRIMARY KEY AUTOINCREMENT"

        def table_exists(cursor, table_name: str) -> bool:
            """Check if table exists."""
            if is_postgres:
                cursor.execute(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)",
                    (table_name,),
                )
                return cursor.fetchone()["exists"]
            else:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                return cursor.fetchone() is not None

        def create_table(table_name: str, columns: list[str]):
            """Create a table if it doesn't exist."""
            if table_exists(cursor, table_name):
                return
            columns_sql = ",\n                    ".join(columns)
            try:
                cursor.execute(
                    f"""
                    CREATE TABLE {table_name} (
                        {id_column},
                        {columns_sql}
                    )
                    """
                )
                db.commit()
            except Exception as e:
                db.rollback()
                # If table was created concurrently, that's fine
                if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
                    raise

        # Create users table
        create_table("users", [
            "email TEXT NOT NULL UNIQUE",
            "name TEXT NOT NULL",
            "password_hash TEXT NOT NULL",
            "role TEXT NOT NULL CHECK (role IN ('doctor', 'pharmacist', 'admin'))",
            "is_active INTEGER NOT NULL DEFAULT 1",
            "created_at TEXT NOT NULL",
            "updated_at TEXT NOT NULL"
        ])

        # Create hospitals table
        create_table("hospitals", [
            "name TEXT NOT NULL UNIQUE",
            "address TEXT",
            "phone TEXT",
            "email TEXT",
            "created_at TEXT NOT NULL"
        ])

        # Ensure UNIQUE constraint on hospitals.name exists (migration for existing databases)
        def ensure_hospitals_name_unique():
            """Ensure hospitals.name has a UNIQUE constraint/index."""
            if is_postgres:
                # Check if UNIQUE constraint already exists on hospitals.name
                cursor.execute("""
                    SELECT 1 FROM pg_constraint c
                    JOIN pg_class t ON c.conrelid = t.oid
                    JOIN pg_namespace n ON t.relnamespace = n.oid
                    WHERE n.nspname = 'public'
                      AND t.relname = 'hospitals'
                      AND c.contype = 'u'
                      AND c.conname LIKE 'hospitals_name%%'
                """)
                if cursor.fetchone() is None:
                    # Also check for unique index (in case constraint was added as index)
                    cursor.execute("""
                        SELECT 1 FROM pg_indexes
                        WHERE schemaname = 'public'
                          AND tablename = 'hospitals'
                          AND indexdef LIKE '%%UNIQUE%%name%%'
                    """)
                    if cursor.fetchone() is None:
                        # No UNIQUE constraint or index found - add it
                        # First check for duplicates that would prevent constraint creation
                        cursor.execute("""
                            SELECT name, COUNT(*) as cnt
                            FROM hospitals
                            GROUP BY name
                            HAVING COUNT(*) > 1
                        """)
                        duplicates = cursor.fetchall()
                        if duplicates:
                            db.rollback()
                            dup_names = [d["name"] for d in duplicates]
                            raise RuntimeError(
                                f"Cannot add UNIQUE constraint on hospitals.name: "
                                f"duplicate hospital names exist: {dup_names}. "
                                f"Resolve duplicate data before continuing."
                            )
                        # Add UNIQUE constraint using valid PostgreSQL syntax
                        cursor.execute("ALTER TABLE hospitals ADD CONSTRAINT hospitals_name_unique UNIQUE (name)")
                        db.commit()
            else:
                # SQLite: check if UNIQUE index/constraint exists on name
                cursor.execute("""
                    SELECT 1 FROM sqlite_master
                    WHERE type = 'index'
                      AND tbl_name = 'hospitals'
                      AND sql LIKE '%name%UNIQUE%'
                """)
                if cursor.fetchone() is None:
                    # Also check if table was created with UNIQUE column constraint
                    cursor.execute("PRAGMA index_list(hospitals)")
                    indexes = cursor.fetchall()
                    has_unique = False
                    for idx in indexes:
                        if idx["name"] == "sqlite_autoindex_hospitals_1":
                            # Check if this is on the name column
                            cursor.execute(f'PRAGMA index_info("{idx["name"]}")')
                            cols = cursor.fetchall()
                            if cols and cols[0]["name"] == "name":
                                has_unique = True
                                break
                    if not has_unique:
                        # Check for duplicates first
                        cursor.execute("""
                            SELECT name, COUNT(*) as cnt
                            FROM hospitals
                            GROUP BY name
                            HAVING COUNT(*) > 1
                        """)
                        duplicates = cursor.fetchall()
                        if duplicates:
                            db.rollback()
                            dup_names = [d["name"] for d in duplicates]
                            raise RuntimeError(
                                f"Cannot add UNIQUE constraint on hospitals.name: "
                                f"duplicate hospital names exist: {dup_names}. "
                                f"Resolve duplicate data before continuing."
                            )
                        # Create UNIQUE index in SQLite
                        cursor.execute("CREATE UNIQUE INDEX idx_hospitals_name_unique ON hospitals(name)")
                        db.commit()

        ensure_hospitals_name_unique()

        # Create prescriptions table
        create_table("prescriptions", [
            "verification_id TEXT NOT NULL UNIQUE",
            "patient_name TEXT NOT NULL",
            "patient_reference TEXT NOT NULL",
            "doctor_name TEXT NOT NULL",
            "clinic_name TEXT NOT NULL",
            "medicine_name TEXT NOT NULL",
            "dosage TEXT NOT NULL",
            "instructions TEXT NOT NULL",
            "issue_date TEXT NOT NULL",
            "status TEXT NOT NULL DEFAULT 'active'",
            "created_at TEXT NOT NULL",
            "received_at TEXT",
            "received_by_user_id INTEGER"
        ])

        # Create notifications table
        create_table("notifications", [
            "user_id INTEGER NOT NULL REFERENCES users(id)",
            "message TEXT NOT NULL",
            "is_read INTEGER NOT NULL DEFAULT 0",
            "created_at TEXT NOT NULL",
            "prescription_id INTEGER REFERENCES prescriptions(id)"
        ])

        # Add hospital_id column to users table if not exists (idempotent migration)
        try:
            if is_postgres:
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS hospital_id INTEGER REFERENCES hospitals(id)")
            else:
                # Check if column exists in SQLite
                cursor.execute("PRAGMA table_info(users)")
                columns = [row["name"] for row in cursor.fetchall()]
                if "hospital_id" not in columns:
                    cursor.execute("ALTER TABLE users ADD COLUMN hospital_id INTEGER REFERENCES hospitals(id)")
            db.commit()
        except Exception as e:
            if "duplicate column" not in str(e).lower() and "already exists" not in str(e).lower():
                pass
            db.rollback()

        # Add received_at and received_by_user_id columns to prescriptions if not exists (idempotent migration)
        try:
            if is_postgres:
                cursor.execute("ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS received_at TEXT")
                cursor.execute("ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS received_by_user_id INTEGER REFERENCES users(id)")
            else:
                cursor.execute("PRAGMA table_info(prescriptions)")
                columns = [row["name"] for row in cursor.fetchall()]
                if "received_at" not in columns:
                    cursor.execute("ALTER TABLE prescriptions ADD COLUMN received_at TEXT")
                cursor.execute("PRAGMA table_info(prescriptions)")
                columns = [row["name"] for row in cursor.fetchall()]
                if "received_by_user_id" not in columns:
                    cursor.execute("ALTER TABLE prescriptions ADD COLUMN received_by_user_id INTEGER REFERENCES users(id)")
            db.commit()
        except Exception as e:
            if "duplicate column" not in str(e).lower() and "already exists" not in str(e).lower():
                pass
            db.rollback()

        # Create notifications table
        try:
            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS notifications (
                    {id_column},
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    message TEXT NOT NULL,
                    is_read INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    prescription_id INTEGER REFERENCES prescriptions(id)
                )
                """
            )
        except Exception as e:
            if "duplicate key" not in str(e).lower() and "already exists" not in str(e).lower():
                raise

        db.commit()

        db.commit()

    with app.app_context():
        init_db()
        # Seed development users in non-production environments
        if not test_config and app.config.get("FLASK_ENV") != "production":
            from src.seeds import seed_development_users
            seed_development_users(app)

    @app.context_processor
    def inject_current_user():
        user_data = {"name": session.get("name"), "role": session.get("role")}
        # Add unread notification count for doctors and admins
        unread_count = 0
        if session.get("role") in {"doctor", "admin"} and session.get("user_id"):
            try:
                from src.models import get_unread_count
                db = get_db()
                unread_count = get_unread_count(db, session["user_id"])
            except Exception:
                pass
        return {"current_user": user_data, "unread_count": unread_count}

    # Register blueprints
    from src.auth import bp as auth_bp
    from src.doctor import bp as doctor_bp
    from src.pharmacist import bp as pharmacist_bp
    from src.admin import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(pharmacist_bp)
    app.register_blueprint(admin_bp)

    @app.get("/", endpoint="home")
    def home():
        # Redirect authenticated admin to admin dashboard
        if session.get("role") == "admin":
            return redirect(url_for("admin.dashboard"))
        return render_template("index.html")

    @app.get("/health")
    def health():
        """Lightweight endpoint used to confirm that the container is running."""
        return {"status": "ok"}

    return app