"""Authentication routes."""
from __future__ import annotations

from flask import abort, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from src.auth import bp
from src.models.user import get_user_by_email


@bp.route("/login/<role>", methods=["GET", "POST"], endpoint="login")
def login(role: str):
    if role not in {"doctor", "pharmacist", "admin"}:
        abort(404)
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_user_by_email(current_app.get_db(), email)

        # Verify: user exists, role matches, is active, password correct
        if user and user.role == role and user.is_active and user.verify_password(password):
            session.clear()
            session.update(name=user.name, role=user.role, user_id=user.id)
            flash(f"Welcome, {user.name}.", "success")
            if role == "doctor":
                return redirect(url_for("doctor.issue_prescription"))
            elif role == "pharmacist":
                return redirect(url_for("pharmacist.verify_form"))
            else:  # admin
                return redirect(url_for("admin.dashboard"))
        # Generic error - don't reveal whether email exists
        flash("Incorrect credentials or account role.", "error")
    return render_template("login.html", role=role)


@bp.post("/logout", endpoint="logout")
def logout():
    session.clear()
    flash("You have signed out.", "success")
    return redirect(url_for("home"))