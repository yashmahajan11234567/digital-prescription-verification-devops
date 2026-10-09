"""Admin routes for hospital hierarchy and dashboard."""
from __future__ import annotations

import re
from datetime import date

from flask import current_app, render_template, request, session, flash, redirect, url_for, abort

from src.decorators import require_admin
from src.admin import bp
from src.models.user import (
    create_user,
    generate_pharmacist_identifier,
    create_hospital,
    get_hospital_by_id,
    get_user_by_email,
)


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _valid_email(value: str) -> bool:
    return bool(_EMAIL_RE.match(value or ""))


@bp.get("/", endpoint="dashboard")
@require_admin()
def dashboard():
    """Admin dashboard with statistics (Hospitals / Doctors / Pharmacists only)."""
    db = current_app.get_db()
    cursor = db.cursor()

    # Get counts
    cursor.execute("SELECT COUNT(*) as count FROM hospitals")
    hospital_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'doctor'")
    doctor_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'pharmacist'")
    pharmacist_count = cursor.fetchone()["count"]

    stats = {
        "hospitals": hospital_count,
        "doctors": doctor_count,
        "pharmacists": pharmacist_count,
    }

    return render_template("admin/dashboard.html", stats=stats)


@bp.get("/hospitals/add", endpoint="add_hospital")
@require_admin()
def add_hospital_form():
    """Render the Add Hospital form."""
    return render_template("admin/add_hospital.html", form={})


@bp.post("/hospitals/add", endpoint="add_hospital_post")
@require_admin()
def add_hospital_submit():
    """Create a new hospital from admin input."""
    name = (request.form.get("name") or "").strip()
    address = (request.form.get("address") or "").strip() or None
    phone = (request.form.get("phone") or "").strip() or None
    email = (request.form.get("email") or "").strip().lower() or None

    if not name:
        flash("Hospital name is required.", "error")
        return render_template("admin/add_hospital.html",
                               form={"name": name, "address": address, "phone": phone, "email": email}), 400

    if email and not _valid_email(email):
        flash("Enter a valid hospital email address.", "error")
        return render_template("admin/add_hospital.html",
                               form={"name": name, "address": address, "phone": phone, "email": email}), 400

    db = current_app.get_db()
    try:
        hospital_id = create_hospital(db, name, address, phone, email)
    except Exception as exc:  # UNIQUE name constraint violation, etc.
        if "UNIQUE" in str(exc).upper() or "duplicate" in str(exc).lower():
            flash(f"A hospital named '{name}' already exists.", "error")
        else:
            flash("Could not create hospital. Please try again.", "error")
            current_app.logger.error(f"Hospital creation failed: {exc}")
        return render_template("admin/add_hospital.html",
                               form={"name": name, "address": address, "phone": phone, "email": email}), 400

    flash(f"Hospital '{name}' created.", "success")
    return redirect(url_for("admin.hospital_detail", hospital_id=hospital_id))


@bp.get("/hospitals/<int:hospital_id>/doctors/add", endpoint="add_doctor")
@require_admin()
def add_doctor_form(hospital_id: int):
    """Render the Register Doctor form for a specific hospital."""
    db = current_app.get_db()
    hospital = get_hospital_by_id(db, hospital_id)
    if not hospital:
        abort(404)
    return render_template("admin/add_doctor.html", hospital=hospital, form={})


@bp.post("/hospitals/<int:hospital_id>/doctors/add", endpoint="add_doctor_post")
@require_admin()
def add_doctor_submit(hospital_id: int):
    """Register a doctor tied to a specific hospital (hospital_id is server-controlled)."""
    db = current_app.get_db()

    # Validate hospital exists server-side; never trust a client hospital_id.
    hospital = get_hospital_by_id(db, hospital_id)
    if not hospital:
        abort(404)

    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    if not name:
        flash("Doctor name is required.", "error")
        return render_template("admin/add_doctor.html", hospital=hospital,
                               form={"name": name, "email": email}), 400

    if not email or not _valid_email(email):
        flash("Enter a valid doctor email address.", "error")
        return render_template("admin/add_doctor.html", hospital=hospital,
                               form={"name": name, "email": email}), 400

    if len(password) < 6:
        flash("Password must be at least 6 characters.", "error")
        return render_template("admin/add_doctor.html", hospital=hospital,
                               form={"name": name, "email": email}), 400

    if get_user_by_email(db, email):
        flash("A user with this email already exists.", "error")
        return render_template("admin/add_doctor.html", hospital=hospital,
                               form={"name": name, "email": email}), 400

    # Reuse the existing create_user mechanism -> role=doctor, hospital_id server-set,
    # password securely hashed. Never stored or logged in plaintext.
    create_user(
        db,
        email=email,
        name=name,
        password=password,
        role="doctor",
        is_active=True,
        hospital_id=hospital_id,
    )

    flash(f"Doctor '{name}' registered to {hospital['name']}.", "success")
    return redirect(url_for("admin.hospital_detail", hospital_id=hospital_id))


@bp.get("/pharmacists", endpoint="pharmacists")
@require_admin()
def pharmacists_list():
    """List all registered pharmacists."""
    db = current_app.get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT u.*, COUNT(p.id) as verification_count
        FROM users u
        LEFT JOIN prescriptions p ON p.received_by_user_id = u.id
        WHERE u.role = 'pharmacist'
        GROUP BY u.id
        ORDER BY u.pharmacist_identifier, u.name
    """)
    pharmacists = [dict(row) for row in cursor.fetchall()]
    return render_template("admin/pharmacists.html", pharmacists=pharmacists)


@bp.get("/pharmacists/add", endpoint="add_pharmacist")
@require_admin()
def add_pharmacist_form():
    """Render the Add Pharmacist form."""
    return render_template("admin/add_pharmacist.html", form={})


@bp.post("/pharmacists/add", endpoint="add_pharmacist_post")
@require_admin()
def add_pharmacist_submit():
    """Create a pharmacist with a server-generated PHARM-XXX identifier."""
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    if not name:
        flash("Pharmacist name is required.", "error")
        return render_template("admin/add_pharmacist.html",
                               form={"name": name, "email": email}), 400

    if not email or not _valid_email(email):
        flash("Enter a valid pharmacist email address.", "error")
        return render_template("admin/add_pharmacist.html",
                               form={"name": name, "email": email}), 400

    if len(password) < 6:
        flash("Password must be at least 6 characters.", "error")
        return render_template("admin/add_pharmacist.html",
                               form={"name": name, "email": email}), 400

    db = current_app.get_db()
    if get_user_by_email(db, email):
        flash("A user with this email already exists.", "error")
        return render_template("admin/add_pharmacist.html",
                               form={"name": name, "email": email}), 400

    # Generate the next sequential, unique PHARM-XXX identifier server-side.
    pharmacist_identifier = generate_pharmacist_identifier(db)

    create_user(
        db,
        email=email,
        name=name,
        password=password,
        role="pharmacist",
        is_active=True,
        pharmacist_identifier=pharmacist_identifier,
    )

    flash(f"Pharmacist '{name}' created with ID {pharmacist_identifier}.", "success")
    return redirect(url_for("admin.pharmacists"))


@bp.get("/hospitals", endpoint="hospitals")
@require_admin()
def hospitals_list():
    """List all hospitals with doctor/pharmacist counts."""
    db = current_app.get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT h.*,
               COUNT(CASE WHEN u.role = 'doctor' THEN 1 END) as doctor_count,
               COUNT(CASE WHEN u.role = 'pharmacist' THEN 1 END) as pharmacist_count
        FROM hospitals h
        LEFT JOIN users u ON u.hospital_id = h.id
        GROUP BY h.id
        ORDER BY h.name
    """)
    hospitals = [dict(row) for row in cursor.fetchall()]

    return render_template("admin/hospitals.html", hospitals=hospitals)


@bp.get("/hospitals/<int:hospital_id>", endpoint="hospital_detail")
@require_admin()
def hospital_detail(hospital_id: int):
    """Show hospital details with doctors and pharmacists."""
    db = current_app.get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM hospitals WHERE id = ?", (hospital_id,))
    hospital = cursor.fetchone()
    if not hospital:
        from flask import abort
        abort(404)

    # Get doctors for this hospital
    cursor.execute("""
        SELECT u.*, COUNT(p.id) as prescription_count
        FROM users u
        LEFT JOIN prescriptions p ON p.doctor_name = u.name
        WHERE u.hospital_id = ? AND u.role = 'doctor'
        GROUP BY u.id
        ORDER BY u.name
    """, (hospital_id,))
    doctors = [dict(row) for row in cursor.fetchall()]

    # Get pharmacists for this hospital
    cursor.execute("""
        SELECT u.*, COUNT(p.id) as verification_count
        FROM users u
        LEFT JOIN prescriptions p ON p.received_by_user_id = u.id
        WHERE u.hospital_id = ? AND u.role = 'pharmacist'
        GROUP BY u.id
        ORDER BY u.name
    """, (hospital_id,))
    pharmacists = [dict(row) for row in cursor.fetchall()]

    return render_template("admin/hospital_detail.html",
                           hospital=dict(hospital),
                           doctors=doctors,
                           pharmacists=pharmacists)


@bp.get("/hospitals/<int:hospital_id>/doctors/<int:doctor_id>", endpoint="doctor_detail")
@require_admin()
def doctor_detail(hospital_id: int, doctor_id: int):
    """Show doctor details with their prescriptions."""
    db = current_app.get_db()
    cursor = db.cursor()

    # Verify hospital exists
    cursor.execute("SELECT * FROM hospitals WHERE id = ?", (hospital_id,))
    hospital = cursor.fetchone()
    if not hospital:
        from flask import abort
        abort(404)

    # Verify doctor exists and belongs to this hospital
    cursor.execute("SELECT * FROM users WHERE id = ? AND hospital_id = ? AND role = 'doctor'", (doctor_id, hospital_id))
    doctor = cursor.fetchone()
    if not doctor:
        from flask import abort
        abort(404)

    # Get doctor's prescriptions with optional date filter
    date_filter = request.args.get("date")
    if date_filter:
        cursor.execute("""
            SELECT * FROM prescriptions
            WHERE doctor_name = ? AND issue_date = ?
            ORDER BY created_at DESC
        """, (doctor["name"], date_filter))
    else:
        cursor.execute("""
            SELECT * FROM prescriptions
            WHERE doctor_name = ?
            ORDER BY created_at DESC
        """, (doctor["name"],))

    prescriptions = [dict(row) for row in cursor.fetchall()]

    return render_template("admin/doctor_detail.html",
                           hospital=dict(hospital),
                           doctor=dict(doctor),
                           prescriptions=prescriptions,
                           date_filter=date_filter)


@bp.get("/hospitals/<int:hospital_id>/doctors/<int:doctor_id>/prescriptions", endpoint="doctor_prescriptions")
@require_admin()
def doctor_prescriptions(hospital_id: int, doctor_id: int):
    """Show doctor's prescriptions with date filter (alias for doctor_detail with prescription focus)."""
    return doctor_detail(hospital_id, doctor_id)


@bp.get("/notifications", endpoint="notifications")
@require_admin()
def notifications():
    """View all notifications for the admin."""
    db = current_app.get_db()
    from src.models import get_notifications_by_user, get_unread_count
    notifications = get_notifications_by_user(db, session["user_id"])
    unread_count = get_unread_count(db, session["user_id"])
    return render_template("admin/notifications.html", notifications=notifications, unread_count=unread_count)


@bp.post("/notifications/<int:notification_id>/read", endpoint="mark_notification_read")
@require_admin()
def mark_notification_read(notification_id: int):
    """Mark a notification as read."""
    db = current_app.get_db()
    from src.models import mark_notification_read
    mark_notification_read(db, notification_id, session["user_id"])
    flash("Notification marked as read.", "success")
    return redirect(url_for("admin.notifications"))


@bp.post("/notifications/read-all", endpoint="mark_all_read")
@require_admin()
def mark_all_read():
    """Mark all notifications as read."""
    db = current_app.get_db()
    from src.models import mark_all_read
    count = mark_all_read(db, session["user_id"])
    flash(f"{count} notification(s) marked as read.", "success")
    return redirect(url_for("admin.notifications"))


@bp.get("/notifications/poll", endpoint="notifications_poll")
@require_admin()
def notifications_poll():
    """Poll endpoint for unread notification count for admin."""
    db = current_app.get_db()
    from src.models import get_unread_count
    unread_count = get_unread_count(db, session["user_id"])
    return {"unread_count": unread_count}