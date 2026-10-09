from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import date, datetime, timezone
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Gauge
from werkzeug.security import check_password_hash, generate_password_hash


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "local-development-only-change-me"),
        DATABASE=Path(app.instance_path) / "prescriptions.db",
        USERS={
            "doctor@rxverify.local": {
                "name": "Dr. Meera Patel", "role": "doctor",
                "password_hash": generate_password_hash("doctor123"),
            },
            "pharmacist@rxverify.local": {
                "name": "Rohan Sharma", "role": "pharmacist",
                "password_hash": generate_password_hash("pharmacist123"),
            },
        },
    )

    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    def get_db() -> sqlite3.Connection:
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_error: BaseException | None = None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db() -> None:
        db = get_db()
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS prescriptions (
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
                created_at TEXT NOT NULL
            )
            """
        )
        db.commit()

    with app.app_context():
        init_db()

    def require_role(role: str):
        def decorator(view):
            @wraps(view)
            def wrapped(*args, **kwargs):
                if session.get("role") != role:
                    flash(f"Please sign in as a {role} to continue.", "error")
                    return redirect(url_for("login", role=role))
                return view(*args, **kwargs)
            return wrapped
        return decorator

    def require_any_role(*roles: str):
        def decorator(view):
            @wraps(view)
            def wrapped(*args, **kwargs):
                if session.get("role") not in roles:
                    flash("Please sign in as a doctor or pharmacist to continue.", "error")
                    return redirect(url_for("home"))
                return view(*args, **kwargs)
            return wrapped
        return decorator

    @app.context_processor
    def inject_current_user():
        return {"current_user": {"name": session.get("name"), "role": session.get("role")}}

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/health")
    def health():
        """Lightweight endpoint used to confirm that the container is running."""
        return {"status": "ok"}

    @app.route("/login/<role>", methods=["GET", "POST"])
    def login(role: str):
        if role not in {"doctor", "pharmacist"}:
            abort(404)
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            account = app.config["USERS"].get(email)
            if account and account["role"] == role and check_password_hash(account["password_hash"], password):
                session.clear()
                session.update(name=account["name"], role=account["role"])
                flash(f"Welcome, {account['name']}.", "success")
                return redirect(url_for("issue_prescription" if role == "doctor" else "verify_form"))
            flash("Incorrect credentials or account role.", "error")
        return render_template("login.html", role=role)

    @app.post("/logout")
    def logout():
        session.clear()
        flash("You have signed out.", "success")
        return redirect(url_for("home"))

    @app.route("/prescriptions/new", methods=["GET", "POST"])
    @require_role("doctor")
    def issue_prescription():
        if request.method == "POST":
            fields = {
                "patient_name": request.form.get("patient_name", "").strip(),
                "patient_reference": request.form.get("patient_reference", "").strip(),
                "doctor_name": request.form.get("doctor_name", "").strip(),
                "clinic_name": request.form.get("clinic_name", "").strip(),
                "medicine_name": request.form.get("medicine_name", "").strip(),
                "dosage": request.form.get("dosage", "").strip(),
                "instructions": request.form.get("instructions", "").strip(),
                "issue_date": request.form.get("issue_date", "").strip(),
            }
            missing = [name.replace("_", " ") for name, value in fields.items() if not value]
            if missing:
                flash(f"Please complete: {', '.join(missing)}.", "error")
                return render_template("issue.html", form=fields), 400

            try:
                date.fromisoformat(fields["issue_date"])
            except ValueError:
                flash("Issue date must be a valid date.", "error")
                return render_template("issue.html", form=fields), 400

            verification_id = f"RX-{uuid.uuid4().hex[:10].upper()}"
            get_db().execute(
                """
                INSERT INTO prescriptions
                (verification_id, patient_name, patient_reference, doctor_name, clinic_name,
                 medicine_name, dosage, instructions, issue_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    verification_id,
                    fields["patient_name"], fields["patient_reference"], fields["doctor_name"],
                    fields["clinic_name"], fields["medicine_name"], fields["dosage"],
                    fields["instructions"], fields["issue_date"],
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            get_db().commit()
            return redirect(url_for("verification_result", verification_id=verification_id))

        return render_template("issue.html", form={"issue_date": date.today().isoformat()})

    @app.get("/verify")
    @require_role("pharmacist")
    def verify_form():
        return render_template("verify.html")

    @app.post("/verify")
    @require_role("pharmacist")
    def verify_submit():
        verification_id = request.form.get("verification_id", "").strip().upper()
        if not verification_id:
            flash("Enter a prescription ID to verify it.", "error")
            return redirect(url_for("verify_form"))
        return redirect(url_for("verification_result", verification_id=verification_id))

    @app.get("/verify/<verification_id>")
    @require_any_role("doctor", "pharmacist")
    def verification_result(verification_id: str):
        prescription = get_db().execute(
            "SELECT * FROM prescriptions WHERE verification_id = ?", (verification_id.upper(),)
        ).fetchone()
        return render_template("result.html", prescription=prescription, verification_id=verification_id)

    @app.get("/prescriptions")
    @require_role("doctor")
    def prescriptions():
        records = get_db().execute(
            "SELECT * FROM prescriptions ORDER BY id DESC"
        ).fetchall()
        return render_template("prescriptions.html", prescriptions=records)

    @app.post("/prescriptions/<int:prescription_id>/revoke")
    @require_role("doctor")
    def revoke_prescription(prescription_id: int):
        cursor = get_db().execute(
            "UPDATE prescriptions SET status = 'revoked' WHERE id = ?", (prescription_id,)
        )
        if cursor.rowcount == 0:
            abort(404)
        get_db().commit()
        flash("Prescription revoked. Future checks will show it as invalid.", "success")
        return redirect(url_for("prescriptions"))

    # Prometheus metrics
    metrics = PrometheusMetrics(app)
    # Custom application info metric - only register once per process
    try:
        rxverify_info = Gauge('rxverify_info', 'RxVerify application info', ['version'])
        rxverify_info.labels(version='1.0.0').set(1)
    except ValueError:
        # Metric already registered (e.g., in test environment with multiple create_app calls)
        pass

    return app


app = create_app()
